"""Authentication & authorization primitives for the MASSIVE backend.

This module centralises API-key validation and rate-limiting so that the
router modules and ``main.py`` can share a single source of truth.

Design notes
------------
* **Fail-closed in production.** When ``MASSIVE_ENV=production`` and no
  ``MASSIVE_API_KEY`` is configured the API refuses all traffic (HTTP 503).
* **Dev fallback (two-factor).** When ``MASSIVE_ENV=development`` AND
  ``MASSIVE_DEV_FALLBACK`` is set, a fallback key ``dev-secret-key`` is
  accepted so local development is frictionless. Unset ``MASSIVE_ENV``
  resolves to fail-closed — never development.
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
    is_dev_fallback_allowed,
)

log = logging.getLogger(__name__)

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
    accepted = _configured_api_keys()
    if not accepted:
        if is_dev_fallback_allowed():
            accepted = [DEV_FALLBACK_API_KEY]
            log.warning(
                "MASSIVE_API_KEY not set — using dev fallback "
                "(development + MASSIVE_DEV_FALLBACK, dev only)"
            )
        else:
            raise HTTPException(
                status_code=503,
                detail="API key not configured — server is not ready",
            )
    # Compare against every accepted key, and never short-circuit: `any()` over
    # a generator would stop at the first match and leak, through timing, which
    # key matched and how many were checked. Accumulate instead, so the cost is
    # the same for every request regardless of the outcome.
    matched = False
    for candidate in accepted:
        matched |= api_key is not None and api_key_matches(api_key, candidate)
    if not matched:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key


def _configured_api_keys() -> list[str]:
    """Every API key the server accepts, in no particular order.

    Supports two variables, both documented in ``.env.example`` and the README:

    * ``MASSIVE_API_KEY``  — a single key.
    * ``MASSIVE_API_KEYS`` — comma-separated, for rotation: publish the new key
      alongside the old one, move clients over, then drop the old one.

    The plural form was documented and shipped in ``.env.example`` but **never
    read by any code**. An operator rotating credentials with it would have had
    their new keys silently ignored, and an operator who set *only* the plural
    would get a 503 with nothing in the logs pointing at the cause.
    """
    keys: list[str] = []
    single = os.getenv("MASSIVE_API_KEY", "").strip()
    if single:
        keys.append(single)
    for raw in os.getenv("MASSIVE_API_KEYS", "").split(","):
        candidate = raw.strip()
        if candidate and candidate not in keys:
            keys.append(candidate)
    return keys


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
