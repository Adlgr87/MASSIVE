"""
cache_manager.py — Gestor de caché para MASSIVE Architect
Arquitectura: Memoria RAM (ultra-rápido) + SQLite (persistente cross-session)
Compatible con: Streamlit, HF Spaces, Docker, serverless con volumen montado.
"""
import os
import json
import sqlite3
import hashlib
from typing import Optional


class LandscapeCache:
    """
    Caché clave-valor para paisajes sociales generados por el LLM.
    Prioriza velocidad (dict en memoria) y persistencia (SQLite).
    Thread-safe para Streamlit (check_same_thread=False).
    """

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or os.getenv("CACHE_DB_PATH", "landscapes_cache.db")
        self._memory: dict[str, dict] = {}
        self._init_db()

    def _init_db(self) -> None:
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS landscapes (
                    key TEXT PRIMARY KEY,
                    config TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Cache] ⚠️ No se pudo inicializar SQLite: {e}. Caché solo en memoria.")

    def _key(self, goal: str) -> str:
        return hashlib.md5(goal.lower().strip().encode()).hexdigest()[:12]

    def get(self, goal: str) -> Optional[dict]:
        k = self._key(goal)
        if k in self._memory:
            return self._memory[k]
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cur = conn.execute("SELECT config FROM landscapes WHERE key = ?", (k,))
            row = cur.fetchone()
            conn.close()
            if row:
                cfg = json.loads(row[0])
                self._memory[k] = cfg
                return cfg
        except Exception:
            pass
        return None

    def set(self, goal: str, config: dict) -> None:
        k = self._key(goal)
        self._memory[k] = config
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("""
                INSERT OR REPLACE INTO landscapes (key, config)
                VALUES (?, ?)
            """, (k, json.dumps(config, ensure_ascii=False)))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def clear(self) -> None:
        self._memory.clear()
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("DELETE FROM landscapes")
            conn.commit()
            conn.close()
        except Exception:
            pass
