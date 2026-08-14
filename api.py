from __future__ import annotations

import os
import tempfile
import logging
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

log = logging.getLogger("massive.api")

app = FastAPI(title="MASSIVE UIL API", version="1.0.0")

# ── Auth ──────────────────────────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Validate API key from header. Fail-closed in production."""
    valid_key = os.getenv("MASSIVE_API_KEY")
    if not valid_key:
        if os.getenv("MASSIVE_ENV") == "dev":
            valid_key = "dev-secret-key"
            log.warning("MASSIVE_API_KEY not set — using dev fallback (dev mode only)")
        else:
            raise HTTPException(status_code=503, detail="API key not configured")
    if api_key != valid_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key


# ── App settings (YAML defaults + env overrides) ─────────────────────
try:
    from massive_core.config import configure_logging, get_app_settings

    configure_logging()
    _app_settings = get_app_settings()
except Exception:  # pragma: no cover - fallback if config package unavailable
    _app_settings = None

# ── CORS (no wildcard when credentials are enabled) ───────────────────
_cors_env = os.getenv("MASSIVE_CORS_ORIGINS", "")
if _cors_env.strip():
    _cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip() and o.strip() != "*"]
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


# ── Rate limit (memory default; file backend for multi-worker) ────────
_RATE_LIMIT = int(
    os.getenv(
        "MASSIVE_RATE_LIMIT_PER_MIN",
        str(_app_settings.rate_limit_per_min if _app_settings else 60),
    )
)
try:
    from massive_core.config import build_rate_limiter

    _rate_limiter = build_rate_limiter(
        backend=os.getenv(
            "MASSIVE_RATE_LIMIT_BACKEND",
            getattr(_app_settings, "rate_limit_backend", None) if _app_settings else "memory",
        ),
        path=os.getenv(
            "MASSIVE_RATE_LIMIT_PATH",
            getattr(_app_settings, "rate_limit_path", None) if _app_settings else None,
        ),
    )
except Exception:  # pragma: no cover
    from massive_core.config.rate_limit import InMemoryRateLimiter

    _rate_limiter = InMemoryRateLimiter()


def _rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    if not _rate_limiter.allow(ip, _RATE_LIMIT):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


# ── Upload constraints ────────────────────────────────────────────────
_MAX_UPLOAD_BYTES = int(os.getenv("MASSIVE_MAX_UPLOAD_MB", "10")) * 1024 * 1024
_ALLOWED_EXT = {".pdf", ".json", ".csv", ".xlsx", ".txt", ".md"}


def _safe_suffix(filename: str | None) -> str:
    if not filename or "." not in filename:
        return ".tmp"
    ext = "." + filename.rsplit(".", 1)[-1].lower()
    if ext not in _ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
    return ext


# Lazily create adapter
_adapter = None


def get_adapter():
    global _adapter
    if _adapter is None:
        try:
            from uil_adapter import create_uil_adapter
            provider = os.getenv("PROVIDER", "groq")
            api_key = os.getenv("GROQ_API_KEY", os.getenv("OPENAI_API_KEY", ""))
            _adapter = create_uil_adapter(llm_provider=provider, llm_api_key=api_key)
        except Exception as e:
            log.exception("Failed to create UIL adapter")
            raise HTTPException(status_code=503, detail="UIL adapter unavailable") from e
    return _adapter


def _public_error(exc: Exception) -> HTTPException:
    """Never leak stack traces / internal paths to clients."""
    log.exception("API error: %s", exc)
    return HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/extract")
async def api_extract(
    request: Request,
    file: UploadFile = File(...),
    api_key: Optional[str] = Depends(get_api_key),
):
    """Upload a file (pdf/json/csv/xlsx) and return extracted MASSIVE config."""
    _rate_limit(request)
    adapter = get_adapter()
    suffix = _safe_suffix(file.filename)
    tmp_path = None
    try:
        content = await file.read()
        if len(content) > _MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File too large")
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        config = adapter.from_document(tmp_path)
        return {"config": config}
    except HTTPException:
        raise
    except Exception as exc:
        raise _public_error(exc)
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@app.post("/api/wizard")
async def api_wizard(
    request: Request,
    payload: dict,
    api_key: Optional[str] = Depends(get_api_key),
):
    """Accepts JSON {"description": "..."} and returns a generated config."""
    _rate_limit(request)
    desc = payload.get("description") if isinstance(payload, dict) else None
    if not desc:
        raise HTTPException(status_code=400, detail="'description' field required")
    try:
        adapter = get_adapter()
        config = adapter.from_natural_language(desc)
        return {"config": config}
    except HTTPException:
        raise
    except Exception as exc:
        raise _public_error(exc)


@app.post("/api/simulate-uil")
async def api_simulate(
    request: Request,
    payload: dict,
    api_key: Optional[str] = Depends(get_api_key),
):
    """
    Run full_pipeline from a natural-language description only.

    Server filesystem paths are intentionally not accepted (no file_path).
    Upload documents via /api/extract instead.
    """
    _rate_limit(request)
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON body required")
    if "file_path" in payload:
        raise HTTPException(
            status_code=400,
            detail="file_path is not allowed; use /api/extract to upload files",
        )
    description = payload.get("description")
    if not description:
        raise HTTPException(status_code=400, detail="'description' field required")
    try:
        adapter = get_adapter()
        result = adapter.full_pipeline(description=description)
        # Drop raw history if huge — keep summary + config
        return {
            "config": result.get("config"),
            "summary": result.get("summary"),
            "n_steps": len(result.get("history") or []),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise _public_error(exc)




# ── API v1: Architect, Forecast, Energy endpoints ───────────────────────────
# Wired to the real core functions (see social_architect.py, forecast/engine.py,
# energy_runner.py). Incoming payloads are validated loosely as dicts to stay
# consistent with the existing /api/wizard and /api/simulate-uil endpoints;
# outgoing / error shapes follow the same _public_error + _rate_limit pattern.
#
# The /api/v1/forecast endpoint validates its projected point against the
# existing DTOs from backend.app.models (ForecastPoint / Feasibility).

@app.post("/api/v1/architect")
async def api_architect(
    request: Request,
    payload: dict,
    api_key: Optional[str] = Depends(get_api_key),
):
    """Social architect inverse-strategy endpoint.

    Runs the inverse-search architect to find a strategy reaching a user goal.
    Payload fields:
        estado_inicial: dict  – initial simulator state.
        objetivo_usuario: str – desired end-state description.
        max_intentos: int     (optional, default 3)
        config: dict          (optional, simulator overrides)
        modo_simulacion: str  (optional, "macro" | "corporativo")
        metricas_red: str     (optional, network metrics summary)
    """
    _rate_limit(request)
    from social_architect import buscar_estrategia_inversa
    try:
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="JSON body required")
        estado_inicial = payload.get("estado_inicial")
        objetivo_usuario = payload.get("objetivo_usuario")
        if not isinstance(estado_inicial, dict) or not isinstance(objetivo_usuario, str)                 or not objetivo_usuario.strip():
            raise HTTPException(
                status_code=400,
                detail="'estado_inicial' (dict) and 'objetivo_usuario' (str) are required",
            )
        estrategia, narrativa, intentos, historial = buscar_estrategia_inversa(
            estado_inicial=estado_inicial,
            objetivo_usuario=objetivo_usuario,
            max_intentos=int(payload.get("max_intentos", 3)),
            config=payload.get("config"),
            modo_simulacion=payload.get("modo_simulacion", "macro"),
            metricas_red=payload.get("metricas_red", ""),
        )
        return {
            "strategy": estrategia,
            "narrative": narrativa,
            "attempts": intentos,
            "history_summary": historial[:5] if isinstance(historial, list) else [],
            "history_length": len(historial) if isinstance(historial, list) else 0,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise _public_error(exc)


@app.post("/api/v1/forecast")
async def api_forecast(
    request: Request,
    payload: dict,
    api_key: Optional[str] = Depends(get_api_key),
):
    """Forecast endpoint with confidence intervals.

    Projects temporal risk metrics over a simulation state snapshot.
    Payload fields:
        simulation_state: dict – snapshot with optional "ews" metrics.
        temporal_config: dict  (optional) – TemporalConfig overrides.
        mode: "analytical" | "monte_carlo" (optional, default "analytical")
        n_runs: int             (optional, MC mode only)
    """
    _rate_limit(request)
    from forecast.engine import forecast
    try:
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="JSON body required")
        simulation_state = payload.get("simulation_state")
        if not isinstance(simulation_state, dict):
            raise HTTPException(status_code=400, detail="'simulation_state' (dict) is required")
        temporal_cfg = payload.get("temporal_config") or {}
        result = forecast(
            simulation_state,
            temporal_config=temporal_cfg if isinstance(temporal_cfg, dict) else {},
            mode=payload.get("mode", "analytical"),
            n_runs=int(payload.get("n_runs", 200)),
        )
        data = result.model_dump() if hasattr(result, "model_dump") else dict(result)
        # Validate the projected point against the existing ForecastPoint /
        # Feasibility DTOs (backend.app.models.dto_forecast) so the response
        # stays schema-aligned with the forecast domain contract.
        try:
            from backend.app.models import ForecastPoint, Feasibility
            _p_event = float(data.get("p_event", 0.0))
            _lower = max(0.0, _p_event - 0.05)
            _upper = min(1.0, _p_event + 0.05)
            point = ForecastPoint(
                tick=data.get("steps_to_event") or 0,
                mean_opinion=_p_event,
                polarization=0.0,
                confidence_lower=_lower,
                confidence_upper=_upper,
            )
            feas = Feasibility(
                score=_p_event,
                label=data.get("confidence", "low"),
                rationale=data.get("mode"),
            )
        except Exception:
            # DTO validation is best-effort; never leak internals.
            point = {"tick": data.get("steps_to_event") or 0,
                     "mean_opinion": float(data.get("p_event", 0.0)),
                     "polarization": 0.0,
                     "confidence_lower": max(0.0, float(data.get("p_event", 0.0)) - 0.05),
                     "confidence_upper": min(1.0, float(data.get("p_event", 0.0)) + 0.05)}
            feas = {"score": float(data.get("p_event", 0.0)),
                    "label": data.get("confidence", "low"),
                    "rationale": data.get("mode")}
        point_dict = point.model_dump() if hasattr(point, "model_dump") else dict(point)
        feas_dict = feas.model_dump() if hasattr(feas, "model_dump") else dict(feas)
        return {
            "forecast": {
                "sim_id": payload.get("sim_id"),
                "horizon_ticks": data.get("steps_to_event"),
                "points": [point_dict],
                "feasibility": feas_dict,
            },
            "raw": data,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise _public_error(exc)


@app.post("/api/v1/energy")
async def api_energy(
    request: Request,
    payload: dict,
    api_key: Optional[str] = Depends(get_api_key),
):
    """Energy landscape analysis endpoint.

    Runs the Langevin energy engine to evolve opinions on a social energy
    landscape derived from a user goal.
    Payload fields:
        user_goal: str       – goal description (required)
        n_agents: int          (optional, default 50)
        steps: int             (optional, default 100)
        connectivity: float    (optional, default 0.3)
        range_type: "bipolar"|"unipolar" (optional, default "bipolar")
        seed: int              (optional, default 42)
        config_overrides: dict (optional)
    """
    _rate_limit(request)
    from energy_runner import run_energy_simulation
    try:
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="JSON body required")
        user_goal = payload.get("user_goal")
        if not isinstance(user_goal, str) or not user_goal.strip():
            raise HTTPException(status_code=400, detail="'user_goal' (str) is required")
        result = run_energy_simulation(
            user_goal=user_goal,
            n_agents=int(payload.get("n_agents", 50)),
            steps=int(payload.get("steps", 100)),
            connectivity=float(payload.get("connectivity", 0.3)),
            range_type=payload.get("range_type", "bipolar"),
            seed=int(payload.get("seed", 42)),
            config_overrides=payload.get("config_overrides"),
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise _public_error(exc)

@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "MASSIVE UIL API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "MASSIVE UIL API",
        "version": "1.0.0",
    }


@app.get("/ready")
async def readiness_check():
    """Check if the API is ready to accept requests (not just healthy)."""
    checks = {"status": "ready", "checks": {}}

    # Check if LLM provider is configured
    has_llm_key = any(os.getenv(k) for k in ("GROQ_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY"))
    checks["checks"]["llm_provider"] = "available" if has_llm_key else "not_configured"

    # Check if UIL adapter can be instantiated (lazy check)
    try:
        get_adapter()
        checks["checks"]["uil_adapter"] = "available"
    except Exception:
        checks["checks"]["uil_adapter"] = "unavailable"

    if not has_llm_key:
        raise HTTPException(status_code=503, detail=checks["checks"])

    return checks


@app.get("/version")
async def version_info():
    """Version and build information."""
    import sys
    return {
        "version": "1.0.0",
        "python": sys.version.split()[0],
        "service": "MASSIVE UIL API"
    }
