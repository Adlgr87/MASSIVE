"""Shared API-key authentication semantics for all MASSIVE HTTP backends.

Single source of truth for two rules that previously drifted between
``api.py`` (legacy) and ``backend/app/security.py`` (canonical):

1. **Environment detection** — ``MASSIVE_ENV`` accepts the documented value
   ``development`` (plus the legacy alias ``dev``); unset resolves to
   fail-closed (NOT development). Staging/production never resolve to development.
2. **Constant-time key comparison** — ``hmac.compare_digest`` on encoded
   values so timing does not leak the expected key.

Dev fallback gate:
3. The dev fallback key ``dev-secret-key`` is accepted ONLY when the
   environment is explicitly development AND the opt-in variable
   ``MASSIVE_DEV_FALLBACK`` is set. This two-factor check prevents an
   accidentally-unset ``MASSIVE_ENV`` from silently enabling a weak default
   key in production-like environments.

Both backends MUST consume these helpers so their behaviour cannot diverge
again (enforced by ``tests/test_api_security.py`` parity tests).
"""

from __future__ import annotations

import hmac
import os

#: Fallback key accepted ONLY when no ``MASSIVE_API_KEY`` is configured, the
#: environment resolves to development, AND ``MASSIVE_DEV_FALLBACK`` is set.
#: Never active in staging/production or when env is unset (fail-closed).
DEV_FALLBACK_API_KEY = "dev-secret-key"

#: Values of ``MASSIVE_ENV`` that resolve to a local development deployment.
_DEV_ENV_VALUES = frozenset({"development", "dev"})


def is_dev_env(env: str | None) -> bool:
    """Return True when ``env`` denotes an *explicit* development deployment.

    Args:
        env: Raw value of ``MASSIVE_ENV`` (may be ``None`` when unset).

    Returns:
        True for ``development`` and the legacy alias ``dev``
        (case-insensitive); **False** for ``None``, ``""``, staging,
        production, or anything else.  Unset is fail-closed.
    """
    if not env:
        return False
    return env.strip().lower() in _DEV_ENV_VALUES


def is_dev_fallback_allowed() -> bool:
    """Return True when the dev fallback API key is explicitly permitted.

    The dev fallback key (``dev-secret-key``) is only accepted when BOTH:
    1. ``MASSIVE_ENV`` is explicitly set to ``development`` or ``dev``.
    2. ``MASSIVE_DEV_FALLBACK`` is set to any non-empty value.

    This two-factor requirement prevents an unconfigured ``MASSIVE_ENV``
    (e.g., unset in production) from silently enabling the weak default key.
    """
    return is_dev_env(os.getenv("MASSIVE_ENV")) and bool(os.getenv("MASSIVE_DEV_FALLBACK"))


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
