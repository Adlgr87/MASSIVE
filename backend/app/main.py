"""Production FastAPI entry-point for the MASSIVE backend.

This module replaces the legacy ``api.py`` monolith with a modular,
versioned (``/v1``), router-based FastAPI application.

Endpoints (versioned)
    POST  /v1/simulate           →  services.simulation_service.run_scalar_simulation
    POST  /v1/forecast           →  services.forecast_service / forecast.engine
    POST  /v1/engine/energy      →  energy_runner.run_energy_simulation
    POST  /v1/engine/architect   →  social_architect.buscar_estrategia_inversa
    POST  /v1/benchmarks         →  benchmarks.runner.main
    POST  /v1/llm/run_simulation →  services.llm_orchestrator.run_llm_simulation

Infra endpoints
    GET   /                        → service info
    GET   /health                  → liveness probe
    GET   /ready                   → readiness (LLM + adapter checks)
    GET   /version                 → build metadata
    GET   /docs | /redoc | /openapi.json → auto-generated

Auth
    All ``/v1/*`` endpoints require ``X-API-Key`` (fail-closed in production).
    Rate-limit: 60 / min per IP (configurable via ``MASSIVE_RATE_LIMIT_PER_MIN``).
"""

from __future__ import annotations

import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from backend.app.metrics import registry as metrics_registry
from backend.app.routers import benchmark, engine, forecast, llm, sim
from backend.app.settings import get_app_settings

# --- logging setup -------------------------------------------------------
try:
    from massive_core.config import configure_logging, get_logger

    configure_logging()
    log = get_logger(__name__)
except Exception as exc:  # pragma: no cover - fallback if config unavailable
    log = logging.getLogger(__name__)
    log.warning("Logging config unavailable, using defaults: %s", exc, exc_info=True)

_app_settings = get_app_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN001
    yield


# --- FastAPI app ---------------------------------------------------------
app = FastAPI(
    title="MASSIVE UIL API",
    version="1.0.0",
    description=(
        "MASSIVE — Mathematical Architecture for Scalable Social Interaction "
        "and Virtual Engine.  Versioned API surface (`/v1/`) for simulation, "
        "forecasting, and intervention analysis."
    ),
    lifespan=lifespan,
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


# --- Request body size limit (defence against oversized payloads) --------
_MAX_BODY_BYTES = int(os.getenv("MASSIVE_MAX_BODY_MB", "10")) * 1024 * 1024


@app.middleware("http")
async def body_size_limit(request: Request, call_next):
    """Reject requests whose declared body exceeds ``MASSIVE_MAX_BODY_MB``.

    Uploads are size-checked inside the upload handlers; this guard covers
    every other JSON endpoint so a single huge payload cannot exhaust memory
    before validation runs.
    """
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > _MAX_BODY_BYTES:
        return JSONResponse(
            status_code=413,
            content={"detail": f"Request body exceeds {_MAX_BODY_BYTES // (1024 * 1024)} MB limit"},
        )
    return await call_next(request)


# --- Request correlation + access log + metrics ---------------------------
def _path_group(path: str) -> str:
    if path.startswith("/v1/llm"):
        return "llm"
    if path.startswith("/v1/simulate") or path.startswith("/v1/scientific"):
        return "simulate"
    if path.startswith("/v1/forecast"):
        return "forecast"
    if path.startswith("/v1/engine"):
        return "engine"
    if path.startswith("/v1/benchmarks"):
        return "benchmarks"
    if path in ("/health", "/ready", "/version", "/metrics"):
        return "infra"
    return "other"


@app.middleware("http")
async def deprecation_warning(request: Request, call_next):
    """Emit X-API-Warn header on legacy /api/* (non-v1) routes.

    These endpoints are superseded by the /v1/* API surface and will be
    removed in v1.0. The warning gives clients a migration signal without
    breaking existing integrations.
    """
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/api/") and not path.startswith("/api/v1"):
        response.headers["X-API-Warn"] = (
            "Deprecated endpoint. Use /v1/* instead. " "See PRODUCTION_ARCHITECTURE_SPEC.md §5.1"
        )
    return response


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Propagate/generate X-Request-ID, record histogram + response-code metrics,
    and support distributed tracing via the W3C TraceContext traceparent header.

    The ID is accepted from trusted upstream proxies (nginx sets none today,
    so it is client-supplied only when the proxy allows it) and echoed back so
    operators can correlate a user report with logs.
    """
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_s = time.perf_counter() - start
    path_group = _path_group(request.url.path)
    status_code = str(response.status_code)

    # ── Metric recording ─────────────────────────────────────────────────
    metrics_registry.inc(
        "http_requests_total",
        {"method": request.method, "group": path_group, "status": status_code},
    )
    metrics_registry.inc(
        "http_responses_total",
        {"method": request.method, "group": path_group, "status_code": status_code},
    )
    metrics_registry.observe(
        "http_request_duration_seconds",
        elapsed_s,
        {"method": request.method, "group": path_group},
    )

    # ── Response headers ─────────────────────────────────────────────────
    response.headers["X-Request-ID"] = request_id

    # Propagate / generate W3C TraceContext traceparent for distributed tracing.
    # Format: version-traceid-spanid-traceflags (hex, 32-16-16-2 chars).
    incoming_tp = request.headers.get("traceparent")
    if incoming_tp:
        traceparent = incoming_tp
        response.headers["traceparent"] = incoming_tp
    else:
        trace_id = uuid.uuid4().hex[:32]
        span_id = uuid.uuid4().hex[:16]
        traceparent = f"00-{trace_id}-{span_id}-01"
        response.headers["traceparent"] = traceparent
    response.headers.setdefault("access-control-expose-headers", "X-Request-ID, traceparent")

    log.info(
        "http request_id=%s traceparent=%s method=%s path=%s status=%s duration_s=%.4f",
        request_id,
        traceparent,
        request.method,
        request.url.path,
        status_code,
        elapsed_s,
    )
    return response


# --- Include versioned routers -------------------------------------------
# Routers are mounted under `/v1/*` (canonical, per ADR-001). An alias at
# `/api/v1/*` is also registered so the existing UI-NG frontend
# (`frontend/src/services/api.ts` baseURL `/api`) and the nginx `/api/` proxy
# keep functioning without a frontend/nginx rewrite. See AGENTS.md §Routing.
app.include_router(sim.router, prefix="/v1")
app.include_router(forecast.router, prefix="/v1")
app.include_router(engine.router, prefix="/v1")
app.include_router(benchmark.router, prefix="/v1")
app.include_router(llm.router, prefix="/v1")
# Compatibility alias: /api/v1/* → same router stack (no double-handling;
# FastAPI mounts by route signature, not path text, so re-inclusion is safe).
app.include_router(sim.router, prefix="/api/v1")
app.include_router(forecast.router, prefix="/api/v1")
app.include_router(engine.router, prefix="/api/v1")
app.include_router(benchmark.router, prefix="/api/v1")
app.include_router(llm.router, prefix="/api/v1")


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


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus text-format metrics (read-only counters, no secrets)."""
    return Response(
        content=metrics_registry.render(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.get("/ready")
async def readiness_check() -> dict[str, Any]:
    """Readiness probe — required dependencies only.

    Required (503 on failure): typed settings load and the core simulation
    stack imports. Optional dependencies (LLM provider, UIL adapter) are
    reported informationally: the API's simulation endpoints work without
    them, so their absence degrades ``/v1/llm/*`` (which returns 503 itself)
    but must NOT remove the whole service from load-balancer rotation.
    """
    checks: dict[str, Any] = {"status": "ready", "mode": "full", "checks": {}}

    # -- Required: typed configuration ------------------------------------
    try:
        get_app_settings()
        checks["checks"]["settings"] = "ok"
    except Exception as exc:
        checks["checks"]["settings"] = f"error: {type(exc).__name__}"
        raise HTTPException(status_code=503, detail=checks) from exc

    # -- Required: core simulation stack ----------------------------------
    try:
        import simulator  # noqa: F401  (canonical engine module)

        checks["checks"]["simulation_core"] = "ok"
    except Exception as exc:
        checks["checks"]["simulation_core"] = f"error: {type(exc).__name__}"
        raise HTTPException(status_code=503, detail=checks) from exc

    # -- Optional: LLM provider (informational) ---------------------------
    has_llm_key = any(
        os.getenv(k) for k in ("GROQ_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY")
    )
    checks["checks"]["llm_provider"] = "available" if has_llm_key else "not_configured"

    # -- Optional: UIL adapter (informational) ----------------------------
    try:
        from uil_adapter import create_uil_adapter  # type: ignore[import-not-found]

        provider = os.getenv("PROVIDER", "groq")
        api_key = os.getenv("GROQ_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        create_uil_adapter(llm_provider=provider, llm_api_key=api_key)
        checks["checks"]["uil_adapter"] = "available"
    except Exception:
        checks["checks"]["uil_adapter"] = "unavailable"

    if not has_llm_key:
        checks["mode"] = "degraded"  # /v1/llm/* unavailable; core works
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


@app.get("/openapi/v1.json")
async def openapi_v1_spec() -> dict[str, Any]:
    """Export the canonical OpenAPI v1 spec (excluding /docs, /metrics, etc.)."""
    schema = app.openapi()
    v1_paths = {
        path: methods for path, methods in schema["paths"].items() if path.startswith("/v1")
    }
    schema["paths"] = v1_paths
    schema.setdefault("info", {})["version"] = "1.0.0"
    schema["info"]["title"] = "MASSIVE UIL API v1"
    return schema
