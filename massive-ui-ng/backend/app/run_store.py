"""Run store for UI-NG — SQLite-backed persistence with in-memory fallback.

Production behavior: runs survive restarts in ``MASSIVE_DATA_DIR/runs.db``
(SQLite, WAL mode, busy timeout). Tests may pass ``db_path=None`` to get an
in-memory store. All JSON payloads are stored verbatim so any stored run can
be re-narrated by ``/api/explain`` or ``/api/runs/{id}``.
"""

from __future__ import annotations

import collections
import json
import logging
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

log = logging.getLogger("massive.ui_ng.run_store")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id          TEXT PRIMARY KEY,
    created         REAL NOT NULL,
    engine          TEXT NOT NULL,
    language        TEXT NOT NULL,
    mode            TEXT NOT NULL,
    headline        TEXT NOT NULL,
    summary_json    TEXT NOT NULL,
    scientific_json TEXT,
    series_json     TEXT NOT NULL,
    meta_json       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runs_created ON runs (created DESC);
"""


def _headline(engine: str, summary: dict[str, Any]) -> str:
    ini = summary.get("opinion_inicial", 0)
    fin = summary.get("opinion_final", 0)
    try:
        return f"{engine}: {float(ini):+.2f} → {float(fin):+.2f}"
    except (TypeError, ValueError):
        return f"{engine}: {ini} → {fin}"


class RunStore:
    """Thread-safe run store (SQLite when ``db_path`` is set)."""

    def __init__(self, db_path: Path | None = None, capacity: int = 500) -> None:
        self._db_path = db_path
        self._capacity = max(capacity, 1)
        self._lock = threading.Lock()
        self._memory: collections.OrderedDict[str, dict[str, Any]] = collections.OrderedDict()
        if db_path is not None:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_db()

    # ── storage backend helpers ───────────────────────────────────────────
    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    def _trim(self) -> None:
        while len(self._memory) > self._capacity:
            self._memory.popitem(last=False)
        if self._db_path is not None:
            with self._conn() as conn:
                conn.execute(
                    """
                    DELETE FROM runs WHERE run_id NOT IN (
                        SELECT run_id FROM runs ORDER BY created DESC LIMIT ?
                    )
                    """,
                    (self._capacity,),
                )

    # ── public API ────────────────────────────────────────────────────────
    def put(self, payload: dict[str, Any]) -> str:
        run_id = uuid.uuid4().hex[:12]
        created = time.time()
        with self._lock:
            self._memory[run_id] = payload
            self._memory.move_to_end(run_id)
            self._trim()
            if self._db_path is not None:
                with self._conn() as conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO runs "
                        "(run_id, created, engine, language, mode, headline, "
                        " summary_json, scientific_json, series_json, meta_json) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (
                            run_id,
                            created,
                            payload["engine"],
                            payload.get("language", "es"),
                            payload.get("mode", "heuristic"),
                            _headline(payload["engine"], payload.get("summary", {})),
                            json.dumps(payload.get("summary", {}), ensure_ascii=False),
                            (
                                json.dumps(payload.get("scientific_report"), ensure_ascii=False)
                                if payload.get("scientific_report") is not None
                                else None
                            ),
                            json.dumps(payload.get("series", {}), ensure_ascii=False),
                            json.dumps(payload.get("meta", {}), ensure_ascii=False),
                        ),
                    )
        return run_id

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            if self._db_path is None:
                return self._memory.get(run_id)
            # SQLite is the source of truth; the in-memory dict is only an
            # LRU cache, refreshed (or invalidated) on every read so that
            # deletions from other processes/instances are respected.
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT engine, language, mode, summary_json, scientific_json, "
                    "series_json, meta_json FROM runs WHERE run_id = ?",
                    (run_id,),
                ).fetchone()
            if row is None:
                self._memory.pop(run_id, None)
                return None
            payload = {
                "engine": row[0],
                "language": row[1],
                "mode": row[2],
                "summary": json.loads(row[3]),
                "scientific_report": json.loads(row[4]) if row[4] else None,
                "series": json.loads(row[5]),
                "meta": json.loads(row[6]),
            }
            self._memory[run_id] = payload
            self._memory.move_to_end(run_id)
            self._trim()
            return payload

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            if self._db_path is None:
                return [
                    {"run_id": rid, **payload}
                    for rid, payload in reversed(list(self._memory.items()))
                ][:limit]
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT run_id, created, engine, language, mode, headline "
                    "FROM runs ORDER BY created DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            entries = [
                {
                    "run_id": r[0],
                    "created": r[1],
                    "engine": r[2],
                    "language": r[3],
                    "mode": r[4],
                    "headline": r[5],
                }
                for r in rows
            ]
            # Enrich with in-memory payloads (most-recent runs live there too).
            for e in entries:
                payload = self._memory.get(e["run_id"])
                if payload:
                    e["summary"] = payload.get("summary", {})
                    e["meta"] = payload.get("meta", {})
            return entries

    def delete(self, run_id: str) -> bool:
        with self._lock:
            self._memory.pop(run_id, None)
            if self._db_path is not None:
                with self._conn() as conn:
                    cur = conn.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
                    return cur.rowcount > 0
            return True

    def count(self) -> int:
        if self._db_path is None:
            return len(self._memory)
        with self._conn() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0])


# Backwards-compatible module-level instance (dev default, replaced by the
# app factory when settings provide a data dir).
run_store = RunStore(db_path=None)
