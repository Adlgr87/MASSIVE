"""Shared API-key authentication semantics for all MASSIVE HTTP backends.

Single source of truth for two rules that previously drifted between
``api.py`` (legacy) and ``backend/app/security.py`` (canonical):

1. **Environment detection** — ``MASSIVE_ENV`` accepts the documented value
   ``development`` (plus the legacy alias ``dev``); unset defaults to
   development. Staging/production never resolve to development.
2. **Constant-time key comparison** — ``hmac.compare_digest`` on encoded
   values so timing does not leak the expected key.

Both backends MUST consume these helpers so their behaviour cannot diverge
again (enforced by ``tests/test_api_security.py`` parity tests).
"""

from __future__ import annotations

import hmac

#: Fallback key accepted ONLY when no ``MASSIVE_API_KEY`` is configured and
#: the environment resolves to development. Never active in staging/production.
DEV_FALLBACK_API_KEY = "dev-secret-key"

#: Values of ``MASSIVE_ENV`` that resolve to a local development deployment.
_DEV_ENV_VALUES = frozenset({"development", "dev"})


def is_dev_env(env: str | None) -> bool:
    """Return True when ``env`` denotes a development deployment.

    Args:
        env: Raw value of ``MASSIVE_ENV`` (may be ``None`` when unset).

    Returns:
        True for ``None``, ``""``, ``development`` and the legacy alias
        ``dev`` (case-insensitive); False for staging/production/anything else.
        Unset is development, matching the documented default in
        ``.env.example`` and ``backend/app/security.py``.
    """
    return (env or "development").strip().lower() in _DEV_ENV_VALUES


def api_key_matches(provided: str | None, expected: str) -> bool:
    """Constant-time comparison of a provided API key against the expected one.

    Args:
        provided: Raw ``X-API-Key`` header value (may be ``None``).
        expected: Configured expected key (non-empty).

    Returns:
        True iff both values are equal. ``None`` never matches.
    """
    if provided is None:
        return False
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))
