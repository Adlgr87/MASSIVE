"""Single source of truth for upload limits and the extension allow-list.

Both API surfaces (the canonical ``backend.app`` routers and the legacy
``api.py``) previously declared these independently and had drifted apart:

* ``backend/app/routers/llm.py`` hardcoded a 10 MB cap, ignoring
  ``MASSIVE_MAX_UPLOAD_MB`` entirely, and then *shadowed* that module
  constant with an identical local inside the handler — so the environment
  variable documented in ``.env.example`` had no effect on the canonical API.
* The allow-lists disagreed: the router accepted ``.docx`` but rejected
  ``.txt``/``.md``, while the legacy API did the exact opposite. The same
  upload was therefore accepted or rejected depending on which path the
  client happened to hit.

A security control that differs between two entry points to the same system
is not a control. Import from here instead of redeclaring.
"""

from __future__ import annotations

import os

#: Extensions accepted by every upload endpoint. The union of what the two
#: surfaces used to accept, so neither entry point loses functionality.
ALLOWED_UPLOAD_EXTENSIONS: frozenset[str] = frozenset(
    {".pdf", ".json", ".csv", ".xlsx", ".docx", ".txt", ".md"}
)

#: Default cap in megabytes when ``MASSIVE_MAX_UPLOAD_MB`` is unset.
DEFAULT_MAX_UPLOAD_MB = 10


def max_upload_bytes() -> int:
    """Return the upload cap in bytes, honouring ``MASSIVE_MAX_UPLOAD_MB``.

    Read at call time rather than at import time so tests and deployments can
    change the limit without re-importing the whole application.

    Falls back to :data:`DEFAULT_MAX_UPLOAD_MB` when the variable is missing
    or not a positive integer, so a malformed value fails safe (to the
    default) instead of raising at request time or disabling the limit.
    """
    raw = os.getenv("MASSIVE_MAX_UPLOAD_MB")
    try:
        megabytes = int(raw) if raw is not None else DEFAULT_MAX_UPLOAD_MB
    except (TypeError, ValueError):
        megabytes = DEFAULT_MAX_UPLOAD_MB
    if megabytes < 1:
        megabytes = DEFAULT_MAX_UPLOAD_MB
    return megabytes * 1024 * 1024


def safe_suffix(filename: str | None, *, default: str = ".tmp") -> str:
    """Return a filename's extension if it is on the allow-list.

    Raises:
        ValueError: if the extension is not allowed. Callers translate this
            into their own HTTP error so this module stays framework-free.
    """
    if not filename or "." not in filename:
        return default
    ext = "." + filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")
    return ext
