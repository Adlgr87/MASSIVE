"""Pluggable rate limiters for the MASSIVE API.

Backends:
    memory — process-local dict (default, single worker)
    file   — JSON file with advisory lock for multi-worker / multi-process
"""

from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path
from typing import Optional


class RateLimiter(ABC):
    """Check whether a client key is allowed another request this minute."""

    @abstractmethod
    def allow(self, key: str, limit_per_min: int) -> bool:
        """Return True if the request is allowed; False if limited."""


class InMemoryRateLimiter(RateLimiter):
    """Single-process rate limiter (default)."""

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str, limit_per_min: int) -> bool:
        now = time.time()
        window = [t for t in self._hits[key] if now - t < 60.0]
        if len(window) >= limit_per_min:
            self._hits[key] = window
            return False
        window.append(now)
        self._hits[key] = window
        return True


class FileRateLimiter(RateLimiter):
    """Shared file-backed rate limiter for multi-worker deployments.

    Uses a simple JSON map of key → timestamps. Best-effort locking via
    ``fcntl`` on POSIX; without ``fcntl`` falls back to unlocked RMW
    (still better than pure memory for multi-process best-effort).
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def allow(self, key: str, limit_per_min: int) -> bool:
        now = time.time()
        try:
            import fcntl
        except ImportError:  # pragma: no cover - non-POSIX
            fcntl = None  # type: ignore[assignment]

        with self.path.open("r+", encoding="utf-8") as fh:
            if fcntl is not None:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                raw = fh.read().strip() or "{}"
                data = json.loads(raw)
                if not isinstance(data, dict):
                    data = {}
                window = [float(t) for t in data.get(key, []) if now - float(t) < 60.0]
                if len(window) >= limit_per_min:
                    data[key] = window
                    allowed = False
                else:
                    window.append(now)
                    data[key] = window
                    allowed = True
                # prune stale keys occasionally
                data = {
                    k: [float(t) for t in ts if now - float(t) < 60.0]
                    for k, ts in data.items()
                    if ts
                }
                fh.seek(0)
                fh.truncate()
                json.dump(data, fh)
                return allowed
            finally:
                if fcntl is not None:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def build_rate_limiter(
    backend: Optional[str] = None,
    path: Optional[str] = None,
) -> RateLimiter:
    """Factory for rate limiters from env / arguments.

    Args:
        backend: ``memory`` or ``file``. Defaults to ``MASSIVE_RATE_LIMIT_BACKEND``.
        path: File path when backend is ``file``. Defaults to
            ``MASSIVE_RATE_LIMIT_PATH`` or ``/tmp/massive_rate_limit.json``.
    """
    resolved = (backend or os.getenv("MASSIVE_RATE_LIMIT_BACKEND") or "memory").lower()
    if resolved == "file":
        file_path = Path(
            path
            or os.getenv("MASSIVE_RATE_LIMIT_PATH")
            or "/tmp/massive_rate_limit.json"
        )
        return FileRateLimiter(file_path)
    return InMemoryRateLimiter()
