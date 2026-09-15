"""LLM orchestration router — ``POST /v1/llm/run_simulation``.

Single entrypoint for LLM agents to run a MASSIVE simulation from a natural-language
intent plus optional partial structured config. Validates against the MASSIVE-LLM
contract, classifies the engine, augments with Factbook params when a country is
mentioned, dispatches the correct engine, and returns structured results +
narrative summary.

Follows the repo-wide convention (ADR-002): input is parsed into a Pydantic
request DTO (validated with ``extra="forbid"``), but the *service layer*
receives the validated model (not a loose dict), keeping strict typing where it
adds value while preserving the existing auth + rate-limit middleware pattern.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from backend.app.models import (
    LLMAmbiguityResponse,
    LLMExtractResponse,
    LLMRunRequest,
    LLMRunResponse,
    LLMWizardRequest,
    LLMWizardResponse,
)
from backend.app.security import get_api_key, rate_limit_dependency
from services.llm_orchestrator import classify_motor

log = logging.getLogger("massive.backend.routers.llm")

# Upload limits + helpers (shared by /extract endpoints)
_ALLOWED_EXT = {".pdf", ".json", ".csv", ".xlsx", ".docx"}
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


def _safe_suffix(filename: str | None) -> str:
    """Return the file extension, rejecting unsupported types."""
    if not filename or "." not in filename:
        return ".tmp"
    ext = "." + filename.rsplit(".", 1)[-1].lower()
    if ext not in _ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
    return ext


def _public_error(exc: Exception) -> HTTPException:
    """Never leak stack traces / internal paths to clients."""
    log.exception("API error: %s", exc)
    return HTTPException(status_code=500, detail="Internal server error")

router = APIRouter(
    prefix="/llm",
    tags=["llm"],
)


@router.post(
    "/run_simulation",
    response_model=LLMRunResponse,
    responses={422: {"model": LLMAmbiguityResponse}},
    dependencies=[Depends(get_api_key), Depends(rate_limit_dependency)],
)
async def v1_llm_run_simulation(
    request: Request,
    payload: LLMRunRequest,
) -> LLMRunResponse:
    """Run a MASSIVE simulation from a natural-language intent.

    Accepts an intent plus optional ``motor``, ``country``,
    ``partial_config``, ``llm``, ``simulation_steps``, ``seed``, and
    ``config_overrides`` (see :class:`LLMRunRequest`).

    The backend:
    1. Classifies the intent against the MASSIVE-LLM contract (or honors an
       explicit ``motor`` override).
    2. If required fields are ambiguous, returns **422** with
       ``requested_fields`` (see :class:`LLMAmbiguityResponse`).
    3. Translates NL → config via the LLM wizard (``services.llm_service``).
    4. Augments with Factbook params when ``country`` is provided.
    5. Dispatches the correct engine and narrates results.

    Returns:
        Validated :class:`LLMRunResponse`.
    """
    from services.llm_orchestrator import run_llm_simulation

    # Early ambiguity check: if motor was not supplied, classify and detect.
    motor_hint = payload.motor
    ambiguities: list[str] = []

    if not motor_hint:
        resolved, amb = classify_motor(payload.intent, None)
        ambiguities = amb
        # Ambiguity that *cannot* be resolved by assumptions → ask the client.
        # Per contract, missing country for energy_engine/forecast may be
        # resolved via defaults, but a missing temporal horizon for a
        # forecast-intent blocks execution and requires user clarification.
    if ambiguities and any(a in ambiguities for a in ("temporal_horizon_days",)) and not motor_hint:
        # If the intent strongly implies a temporal forecast but neither
        # horizon nor country is given, prompt the LLM client to clarify.
        raise HTTPException(
            status_code=422,
            detail={
                "detail": "Intent ambiguous; please provide the requested fields.",
                "requested_fields": ambiguities,
                "motor": motor_hint or resolved,
            },
        )

    try:
        result = run_llm_simulation(
            intent=payload.intent,
            motor=payload.motor,
            country=payload.country,
            partial_config=payload.partial_config,
            llm=payload.llm.model_dump() if payload.llm else None,
            simulation_steps=payload.simulation_steps,
            seed=payload.seed,
            config_overrides=payload.config_overrides,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        log.warning("LLM run_simulation validation error: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        # LLM prerequisite missing for engine types that are inherently LLM-driven.
        log.warning("LLM run_simulation runtime error: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # Assemble the response DTO; ``results`` is a normalized envelope.
    return LLMRunResponse(
        sim_id=result["sim_id"],
        motor=result["motor"],
        config=result["config"],
        summary=result["summary"],
        narrative=result["narrative"],
        results=result["results"],
        assumptions=result["assumptions"],
        factbook_params=result["factbook_params"],
    )


@router.post(
    "/wizard",
    response_model=LLMWizardResponse,
    dependencies=[Depends(get_api_key), Depends(rate_limit_dependency)],
)
async def v1_llm_wizard(payload: LLMWizardRequest) -> LLMWizardResponse:
    """Translate natural language into a MASSIVE config.

    Accepts ``{"description": "...", "llm": {...}}`` and returns the
    generated config dict.
    """
    from services.llm_service import wizard_config

    provider = payload.llm.provider if payload.llm else os.getenv("PROVIDER", "groq")
    api_key = payload.llm.api_key if payload.llm else None

    try:
        config = wizard_config(
            description=payload.description,
            provider=provider,
            api_key=api_key,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return LLMWizardResponse(config=config)


@router.post(
    "/extract",
    response_model=LLMExtractResponse,
    dependencies=[Depends(get_api_key), Depends(rate_limit_dependency)],
)
async def v1_llm_extract(
    request: Request,
    file: UploadFile = File(...),  # B008: avoid function call in default
) -> LLMExtractResponse:
    """Upload a file (pdf/json/csv/xlsx) and return extracted MASSIVE config."""
    import contextlib
    import tempfile

    _MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

    content_length = file.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large")

    tmp_path: str | None = None
    try:
        content = b""
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            content += chunk
            if len(content) > _MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="File too large")

        suffix = _safe_suffix(file.filename)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        from uil_adapter import create_uil_adapter
        adapter = create_uil_adapter(
            llm_provider=os.getenv("PROVIDER", "groq"),
            llm_api_key=os.getenv("GROQ_API_KEY", os.getenv("OPENAI_API_KEY", "")),
        )
        config = adapter.from_document(tmp_path)
        return LLMExtractResponse(config=config)
    except HTTPException:
        raise
    except Exception as exc:
        raise _public_error(exc) from exc
    finally:
        if tmp_path:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
