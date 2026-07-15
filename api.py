from __future__ import annotations

import os
import tempfile
import time
import logging
from collections import defaultdict
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

log = logging.getLogger("massive.api")

app = FastAPI(title="MASSIVE UIL API", version="1.0.0")

# ── Auth ──────────────────────────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Validate API key from header."""
    valid_key = os.getenv("MASSIVE_API_KEY")
    if not valid_key:
        # Dev fallback only when MASSIVE_API_KEY unset
        valid_key = "default-secret-key"
        log.warning("MASSIVE_API_KEY not set — using insecure default")
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


# ── Simple in-process rate limit ──────────────────────────────────────
_RATE_LIMIT = int(
    os.getenv(
        "MASSIVE_RATE_LIMIT_PER_MIN",
        str(_app_settings.rate_limit_per_min if _app_settings else 60),
    )
)
_hits: dict[str, list[float]] = defaultdict(list)


def _rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = _hits[ip]
    _hits[ip] = [t for t in window if now - t < 60.0]
    if len(_hits[ip]) >= _RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    _hits[ip].append(now)


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
