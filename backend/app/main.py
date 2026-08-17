"""Production FastAPI entry-point for the MASSIVE backend.

This module replaces the legacy ``api.py`` monolith with a modular,
versioned (``/v1``), router-based FastAPI application.

Endpoints (versioned)
    POST  /v1/simulate           →  services.simulation_service.run_scalar_simulation
    POST  /v1/forecast           →  services.forecast_service / forecast.engine
    POST  /v1/engine/energy      →  energy_runner.run_energy_simulation
    POST  /v1/engine/architect   →  social_architect.buscar_estrategia_inversa
    POST  /v1/benchmarks         →  benchmarks.runner.main
    POST  /v1/llm/run_simulation →  uil_adapter.full_pipeline (via api.py compat bridge)

Infra endpoints
    GET   /                        → service info
    GET   /health                  → liveness probe
    GET   /ready                   → readiness (LLM + adapter checks)
    GET   /version                 → build metadata
    GET   /docs | /redoc | /openapi.json → auto-generated

Auth
    All ``/v1/*`` endpoints require ``X-API-Key`` (fail-closed in production).
    Rate-limit: 60 / min per IP (configurable via ``MASSIVE_RATE_LIMIT_PER_MIN``).

Migration note (ADR-001)
    During v0.1 the uvicorn target remains ``api:app``.  When
    ``backend/app/main.py`` is ready, swap the Docker/supervisord target
    to ``backend.app.main:app``.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.app.security import get_api_key
from backend.app.settings import get_app_settings
from backend.app.routers import sim, forecast, engine, benchmark, llm

# --- logging setup -------------------------------------------------------
try:
    from massive_core.config import configure_logging, get_logger
    configure_logging()
    log = get_logger("massive.backend.main")
except Exception:  # pragma: no cover - fallback if config unavailable
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger("massive.backend.main")

_app_settings = get_app_settings()

# --- FastAPI app ---------------------------------------------------------
app = FastAPI(
    title="MASSIVE UIL API",
    version="1.0.0",
    description=(
        "MASSIVE — Mathematical Architecture for Scalable Social Interaction "
        "and Virtual Engine.  Versioned API surface (`/v1/`) for simulation, "
        "forecasting, and intervention analysis."
    ),
)

# --- CORS (no wildcard when credentials are enabled) --------------------
_cors_env = os.getenv("MASSIVE_CORS_ORIGINS", "")
if _cors_env.strip():
    _cors_origins: list[str] = [
        o.strip() for o in _cors_env.split(",") if o.strip() and o.strip() != "*"
    ]
elif _app_settings is not None:
    _cors_origins = list(_app_settings.cors_origins)
else:
    _cors_origins = ["http://localhost:1234", "http://localhost:3000"]

if not _cors_origins:
    _cors_origins = ["http://localhost:1234", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# --- Include versioned routers -------------------------------------------
app.include_router(sim.router, prefix="/v1")
app.include_router(forecast.router, prefix="/v1")
app.include_router(engine.router, prefix="/v1")
app.include_router(benchmark.router, prefix="/v1")
app.include_router(llm.router, prefix="/v1")


# --- Infra endpoints -----------------------------------------------------
@app.get("/")
async def root() -> dict[str, Any]:
    """Service information."""
    return {
        "status": "ok",
        "service": "MASSIVE UIL API",
        "version": "1.0.0",
        "docs": "/docs",
        "api_prefix": "/v1",
    }


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Liveness probe — service is alive."""
    return {
        "status": "healthy",
        "service": "MASSIVE UIL API",
        "version": "1.0.0",
    }


@app.get("/ready")
async def readiness_check() -> dict[str, Any]:
    """Readiness probe — checks LLM provider and UIL adapter."""
    checks: dict[str, Any] = {"status": "ready", "checks": {}}

    has_llm_key = any(
        os.getenv(k) for k in ("GROQ_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY")
    )
    checks["checks"]["llm_provider"] = "available" if has_llm_key else "not_configured"

    try:
        from uil_adapter import create_uil_adapter  # type: ignore[import-not-found]
        provider = os.getenv("PROVIDER", "groq")
        api_key = os.getenv("GROQ_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        create_uil_adapter(llm_provider=provider, llm_api_key=api_key)
        checks["checks"]["uil_adapter"] = "available"
    except Exception:
        checks["checks"]["uil_adapter"] = "unavailable"

    if not has_llm_key:
        raise HTTPException(status_code=503, detail=checks["checks"])
    return checks


@app.get("/version")
async def version_info() -> dict[str, Any]:
    """Build / version metadata."""
    return {
        "version": "1.0.0",
        "python": sys.version.split()[0],
        "service": "MASSIVE UIL API",
        "entrypoint": "backend.app.main:app",
    }
