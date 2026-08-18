"""Application settings for the production backend entry-point.

Thin re-export shim so that ``backend.app.settings`` resolves regardless
of whether the import is resolved against the legacy ``massive_core``
config package or a future backend-only copy.

The canonical settings live in ``massive_core.config.settings``.
"""

from __future__ import annotations

from massive_core.config.settings import AppSettings, clear_settings_cache, get_app_settings

__all__ = ["AppSettings", "get_app_settings", "clear_settings_cache"]
