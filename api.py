from __future__ import annotations

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
import os
import tempfile
import shutil
from typing import Optional

app = FastAPI(title="MASSIVE UIL API")

# API Key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key: Optional[str] = Header(None)):
    """Validate API key from header."""
    valid_key = os.getenv("MASSIVE_API_KEY", "default-secret-key")
    if api_key != valid_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key

# Allow CORS from local frontend dev origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1234", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazily create adapter to avoid hard dependency at import time
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
            raise RuntimeError(f"Failed to create UIL adapter: {e}")
    return _adapter


@app.post("/api/extract")
async def api_extract(file: UploadFile = File(...), api_key: Optional[str] = Depends(get_api_key)):
    """Upload a file (pdf/json/csv/xlsx) and return extracted MASSIVE config."""
    adapter = get_adapter()
    suffix = "." + (file.filename.split(".")[-1] if file.filename and "." in file.filename else "tmp")
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        config = adapter.from_document(tmp_path)
        return {"config": config}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@app.post("/api/wizard")
async def api_wizard(payload: dict, api_key: Optional[str] = Depends(get_api_key)):
    """Accepts JSON {"description": "..."} and returns a generated config."""
    desc = payload.get("description")
    if not desc:
        raise HTTPException(status_code=400, detail="'description' field required")
    try:
        adapter = get_adapter()
        config = adapter.from_natural_language(desc)
        return {"config": config}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/simulate-uil")
async def api_simulate(payload: dict, api_key: Optional[str] = Depends(get_api_key)):
    """Optional endpoint that runs full_pipeline. Payload may include 'description' and/or 'file' (path not supported via JSON).
    Prefer /api/extract + separate simulate call. This is a convenience wrapper for quick testing.
    """
    description = payload.get("description") if isinstance(payload, dict) else None
    # If client wants to pass a path on server, allow 'file_path' but warn
    file_path = payload.get("file_path") if isinstance(payload, dict) else None
    try:
        adapter = get_adapter()
        result = adapter.full_pipeline(file_path=file_path, description=description)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "status": "ok",
        "service": "MASSIVE UIL API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "MASSIVE UIL API",
        "version": "1.0.0",
    }
