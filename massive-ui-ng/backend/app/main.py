"""MASSIVE UI-NG — FastAPI application (Next-Gen UI backend).

Production-ready entrypoint that powers the React translator UI. Features:

- API-key auth (multi-key, constant-time), security headers, TrustedHost
- Sliding-window rate limiting (per client IP, stricter for simulations)
- SQLite-backed run persistence (``MASSIVE_DATA_DIR``)
- SSE streaming for the translator conversation and simulation progress
- Optional self-serving of the built frontend (``MASSIVE_SERVE_FRONTEND``)

Run from the repository root:

    uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# Ensure the repository root is importable (services/, simulator.py, …).
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import Response  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from starlette.middleware.trustedhost import TrustedHostMiddleware  # noqa: E402

from backend.app.rate_limit import RateLimitMiddleware  # noqa: E402
from backend.app.run_store import RunStore  # noqa: E402
from backend.app.metrics import registry  # noqa: E402
from backend.app.settings import UISettings  # noqa: E402

logging.basicConfig(
    level=os.getenv("MASSIVE_LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(name)-28s | %(levelname)-8s | %(message)s",
)
log = logging.getLogger("massive.ui_ng")


def _add_security_headers(app: FastAPI) -> None:
    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        return response


def _add_http_counter(app: FastAPI) -> None:
    @app.middleware("http")
    async def http_counter(request, call_next):
        path = request.url.path
        if path.startswith("/api/simulate"):
            group = "simulate"
        elif path.startswith("/api/conversation"):
            group = "conversation"
        elif path.startswith("/api/runs"):
            group = "runs"
        elif path.startswith("/api/status") or path.startswith("/api/explain"):
            group = "status_explain"
        elif path.startswith("/ws/"):
            group = "ws"
        else:
            group = "other"
        registry.inc("http_requests_total", {"method": request.method, "group": group})
        return await call_next(request)


def create_app(settings: UISettings | None = None) -> FastAPI:
    """Build the UI-NG application with explicit or env-driven settings."""
    settings = settings or UISettings()
    if settings.api_keys:
        log.info("API auth enabled (%d key(s) configured)", len(settings.api_keys))

    app = FastAPI(
        title="MASSIVE UI-NG API",
        version="2.0.0",
        description=(
            "Backend of the Next-Gen MASSIVE UI: LLM translator between natural "
            "language and the simulation/scientific layers."
        ),
    )

    # ── Application state ─────────────────────────────────────────────────
    app.state.settings = settings
    app.state.api_keys = settings.api_keys
    app.state.run_store = RunStore(db_path=settings.db_path, capacity=settings.run_store_capacity)
    if settings.db_path is not None:
        log.info("Run persistence: %s", settings.db_path)

    # ── Middleware (order matters: last added runs first) ─────────────────
    _add_security_headers(app)
    _add_http_counter(app)

    if settings.allowed_hosts and settings.allowed_hosts != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    app.add_middleware(
        RateLimitMiddleware,
        enabled=settings.rate_limit_enabled,
        default_limit=settings.rate_limit_per_minute,
        simulate_limit=settings.rate_limit_simulate_per_minute,
        trust_proxy=settings.trust_proxy_headers,
    )

    if settings.serve_frontend or settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # ── Routers ───────────────────────────────────────────────────────────
    from backend.app.routers import conversation, live, simulation, status

    app.include_router(status.router)
    app.include_router(conversation.router)
    app.include_router(simulation.router)
    app.include_router(live.router)

    serve_frontend = settings.serve_frontend and settings.frontend_dist.exists()
    if not serve_frontend:
        @app.get("/")
        def root() -> dict:
            return {
                "status": "ok",
                "service": "MASSIVE UI-NG API",
                "version": "2.0.0",
                "docs": "/docs",
            }

    @app.get("/metrics")
    def metrics() -> Response:
        """Prometheus text-format metrics (counters only, v1).

        Open for scraping; restrict at the network layer (firewall/Ingress)
        if exposed publicly.
        """
        return Response(content=registry.render(), media_type="text/plain; version=0.0.4")

    @app.get("/health")
    def health_check() -> dict:
        """Liveness + light readiness probe (used by Docker HEALTHCHECK)."""
        store: RunStore = app.state.run_store
        try:
            store.count()
            store_ok = True
        except Exception:  # noqa: BLE001
            store_ok = False
        return {
            "status": "healthy" if store_ok else "degraded",
            "service": "MASSIVE UI-NG API",
            "version": "2.0.0",
            "env": settings.env,
            "store": "ok" if store_ok else "error",
        }

    # ── Self-serve the built frontend (production single-service mode) ────
    if serve_frontend:
        app.mount(
            "/",
            StaticFiles(directory=str(settings.frontend_dist), html=True),
            name="frontend",
        )
        log.info("Serving frontend from %s", settings.frontend_dist)
    elif settings.serve_frontend:
        log.info(
            "MASSIVE_SERVE_FRONTEND=1 but %s missing — API-only mode",
            settings.frontend_dist,
        )

    return app


# Module-level app for `uvicorn backend.app.main:app`.
app = create_app()
