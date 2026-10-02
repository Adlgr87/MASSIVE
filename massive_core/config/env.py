"""Dotenv loading for every MASSIVE entry-point.

Why this module exists
----------------------
``python-dotenv`` is declared as a **core** dependency, the README instructs
``cp .env.example .env``, and ``docker-compose.yml`` mounts ``./.env`` into the
container at ``/app/.env`` — but nothing ever called ``load_dotenv()``.  The
practical effect was that **every documented environment variable was dead
configuration**: in Docker only the variables listed under ``environment:``
reached ``os.environ``, so ``MASSIVE_API_KEY`` stayed unset and the whole
``/v1/*`` surface answered ``503 API key not configured``.

This module is the single place that loads ``.env`` and it is imported by both
HTTP entry-points (``backend.app.main`` and the legacy ``api``) plus the CLI,
*before* any module-level ``os.getenv`` call runs.

Semantics
---------
* Real environment variables always win (``override=False``).  A value exported
  by the operator, systemd, Kubernetes or ``docker run -e`` is never clobbered
  by a file checked out in the working tree.
* Loading is idempotent and best-effort: a missing ``.env`` or a missing
  ``python-dotenv`` install is not an error (the "optional means optional"
  invariant applies to configuration too).
* The resolved path can be forced with ``MASSIVE_ENV_FILE`` for tests and for
  deployments that keep secrets outside the project root.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

#: Set once the first successful/attempted load has happened.
_LOADED: bool = False

#: Repository root (…/massive_core/config/env.py → …/)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _candidate_paths(explicit: str | os.PathLike[str] | None) -> list[Path]:
    """Return the ordered list of ``.env`` locations to try."""
    if explicit:
        return [Path(explicit)]
    override = os.getenv("MASSIVE_ENV_FILE")
    if override:
        return [Path(override)]
    return [
        Path.cwd() / ".env",  # process working directory (local dev)
        _PROJECT_ROOT / ".env",  # repository root (/app/.env inside Docker)
    ]


def load_env_file(
    path: str | os.PathLike[str] | None = None,
    *,
    force: bool = False,
) -> Path | None:
    """Load ``.env`` into ``os.environ`` without overriding real env vars.

    Args:
        path: Explicit ``.env`` location. Defaults to ``MASSIVE_ENV_FILE``, then
            ``./.env``, then ``<repo root>/.env``.
        force: Re-run even if a previous call already loaded a file.

    Returns:
        The path that was loaded, or ``None`` when no file was found or
        ``python-dotenv`` is not installed.
    """
    global _LOADED
    if _LOADED and not force:
        return None

    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - python-dotenv is a core dep
        log.debug("python-dotenv not installed; skipping .env loading")
        _LOADED = True
        return None

    _LOADED = True
    for candidate in _candidate_paths(path):
        if candidate.is_file():
            # override=False → exported environment variables always win.
            load_dotenv(candidate, override=False)
            log.info("Loaded environment file: %s", candidate)
            return candidate

    log.debug("No .env file found; relying on the process environment only")
    return None


def reset_env_loader_state() -> None:
    """Testing helper: forget that a file was already loaded."""
    global _LOADED
    _LOADED = False
