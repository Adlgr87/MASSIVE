"""Sliding-window rate limiting for the UI-NG API.

Production note: this limiter keeps state **per process**. For a
multi-worker deployment (``uvicorn --workers N``) either run one worker per
pod behind a load balancer with session affinity, or move to a shared store
(Redis). The settings and middleware interface are designed so that swapping
the backend does not touch router code.

Client identity: the client IP, honoring ``X-Forwarded-For`` only when
``MASSIVE_TRUST_PROXY=1`` (otherwise an attacker could spoof it to bypass
limits).
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

log = logging.getLogger("massive.ui_ng.rate_limit")

_SIMULATE_PREFIXES = ("/api/simulate", "/api/explain")


def _client_ip(request: Request, trust_proxy: bool) -> str:
    if trust_proxy:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class SlidingWindowLimiter:
    """Thread-safe sliding-window limiter keyed by client."""

    def __init__(self, limit_per_minute: int) -> None:
        self.limit = limit_per_minute
        self.window = 60.0
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> tuple[bool, float]:
        """Check and record one request for ``key``.

        Returns:
            (allowed, retry_after_seconds)
        """
        now = time.monotonic()
        with self._lock:
            dq = self._hits[key]
            while dq and now - dq[0] > self.window:
                dq.popleft()
            if len(dq) >= self.limit:
                oldest = dq[0]
                return False, max(1.0, round(self.window - (now - oldest), 1))
            dq.append(now)
            return True, 0.0

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply per-minute limits; simulations use a stricter budget."""

    def __init__(self, app, *, enabled: bool, default_limit: int, simulate_limit: int,
                 trust_proxy: bool = False) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.trust_proxy = trust_proxy
        self._default = SlidingWindowLimiter(default_limit)
        self._simulate = SlidingWindowLimiter(simulate_limit)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self.enabled:
            return await call_next(request)
        path = request.url.path
        limiter = (
            self._simulate
            if path.startswith(_SIMULATE_PREFIXES)
            else self._default
        )
        key = _client_ip(request, self.trust_proxy)
        allowed, retry_after = limiter.allow(key)
        if not allowed:
            log.warning("Rate limit hit for %s on %s", key, path)
            from backend.app.metrics import registry

            registry.inc("rate_limit_hits_total", {"group": "simulate" if path.startswith(_SIMULATE_PREFIXES) else "general"})
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={"Retry-After": str(int(retry_after))},
            )
        return await call_next(request)
