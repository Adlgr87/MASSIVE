"""backend.app — FastAPI app sub-package.

``app`` is exposed lazily (PEP 562) so that importing lightweight submodules
(e.g. ``backend.app.models`` for TS type generation in minimal environments)
does not require fastapi/uvicorn/the simulation stack. Use
``backend.app.main:app`` as the canonical uvicorn target.
"""

from __future__ import annotations

__all__ = ["app"]


def __getattr__(name: str):
    if name == "app":
        from backend.app.main import app

        return app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
