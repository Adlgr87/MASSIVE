"""Authentication & authorization primitives for the MASSIVE backend.

This module centralises API-key validation and rate-limiting so that the
router modules and ``main.py`` can share a single source of truth.

Design notes
------------
* **Fail-closed in production.** When ``MASSIVE_ENV=production`` and no
  ``MASSIVE_API_KEY`` is configured the API refuses all traffic (HTTP 503).
* **Dev fallback.** When ``MASSIVE_ENV=development`` (or unset) a fallback
  key ``dev-secret-key`` is accepted so local development is frictionless.
* **Rate limiter.** Re-uses ``massive_core.config.build_rate_limiter``
  which supports both ``memory`` (single worker) and ``file`` (multi-worker)
  backends via the ``MASSIVE_RATE_LIMIT_BACKEND`` env var.
"""

from __future__ import annotations

import logging
import os

from fastapi import Header, HTTPException, Request
from fastapi.security import APIKeyHeader

from massive_core.config import (
    DEV_FALLBACK_API_KEY,
    api_key_matches,
    build_rate_limiter,
    is_dev_env,
)

log = logging.getLogger("massive.backend.security")

# --- Auth ----------------------------------------------------------------

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(
    api_key: str | None = Header(None, alias="X-API-Key"),
) -> str:
    """Validate the ``X-API-Key`` header.

    Args:
        api_key: Raw header value.

    Returns:
        The validated key string.

    Raises:
        HTTPException: 401 if the key is missing/invalid, 503 if the
            server is not yet configured (production only).
    """
    expected = os.getenv("MASSIVE_API_KEY")
    if not expected:
        if is_dev_env(os.getenv("MASSIVE_ENV")):
            expected = DEV_FALLBACK_API_KEY
            log.warning("MASSIVE_API_KEY not set — using dev fallback (development mode only)")
        else:
            raise HTTPException(
                status_code=503,
                detail="API key not configured — server is not ready",
            )
    if not api_key_matches(api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key


# --- Rate limiting -------------------------------------------------------

_RATE_LIMIT_PER_MIN = int(os.getenv("MASSIVE_RATE_LIMIT_PER_MIN", "60"))

_rate_limiter = build_rate_limiter(
    backend=os.getenv("MASSIVE_RATE_LIMIT_BACKEND", "memory"),
    path=os.getenv("MASSIVE_RATE_LIMIT_PATH"),
)


def rate_limit_dependency(request: Request) -> None:
    """FastAPI dependency that enforces per-IP rate limiting.

    Args:
        request: Incoming request (used for client IP).

    Raises:
        HTTPException: 429 if the client has exceeded the per-minute limit.
    """
    ip = request.client.host if request.client else "unknown"
    if not _rate_limiter.allow(ip, _RATE_LIMIT_PER_MIN):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
