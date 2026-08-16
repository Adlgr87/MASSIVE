"""API-key authentication for the UI-NG backend.

Supports one or more keys via ``MASSIVE_API_KEYS`` (comma-separated) or the
legacy ``MASSIVE_API_KEY``. Comparison is constant-time. When no keys are
configured the API runs in open development mode (logged once).
"""

from __future__ import annotations

import hmac
import logging
from typing import Optional

from fastapi import Header, HTTPException, Request

log = logging.getLogger("massive.ui_ng.security")

_warned = False


def _load_keys() -> list[str]:
    import os

    raw = os.getenv("MASSIVE_API_KEYS", "") or os.getenv("MASSIVE_API_KEY", "")
    return [k.strip() for k in raw.split(",") if k.strip()]


def api_key_is_valid(provided: str, valid_keys: list[str]) -> bool:
    for valid in valid_keys:
        if hmac.compare_digest(provided.encode(), valid.encode()):
            return True
    return False


def get_api_key(request: Request, api_key: Optional[str] = Header(None, alias="X-API-Key")) -> None:
    """Validate the X-API-Key header when keys are configured."""
    global _warned
    keys: list[str] = getattr(request.app.state, "api_keys", None) or _load_keys()
    if not keys:
        if not _warned:
            log.warning("No MASSIVE_API_KEYS configured — API running in open dev mode")
            _warned = True
        return
    if not api_key or not api_key_is_valid(api_key, keys):
        raise HTTPException(status_code=401, detail="Invalid API Key")
