"""MASSIVE backend package.

Deliberately empty: importing ``backend`` must NOT pull the FastAPI app.
``backend/app/__init__.py`` still re-exports ``app`` for convenience, but the
top-level package stays import-light so tooling that only needs the pydantic
DTOs (e.g. ``scripts/gen_ts_types.py`` in the minimal CI environment) can
import ``backend.app.models`` without fastapi/uvicorn/the simulation stack.
"""
