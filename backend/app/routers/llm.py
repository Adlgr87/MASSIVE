"""LLM orchestration router — POST /v1/llm/run_simulation.

Maps natural-language intents to MASSIVE motors via
``backend.app.services.llm_orchestrator``. Error contract (per
configs/llm_contract/massive_llm_contract.json):

  - 400 bad request  : intent too short / invalid payload
  - 422 unprocessable: ambiguous intent  -> LLMAmbiguityResponse (requested_fields)
  - 503              : LLM provider not configured
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.app.models.dto_llm import LLMRunRequest, LLMRunResponse, LLMAmbiguityResponse
from backend.app.services.llm_orchestrator import (
    AmbiguityError,
    ServiceUnavailable,
    run_simulation,
)
from backend.app.security import get_api_key

log = logging.getLogger("massive.ui_ng.llm")

router = APIRouter(prefix="/v1/llm", tags=["llm"], dependencies=[Depends(get_api_key)])


@router.post("/run_simulation", response_model=LLMRunResponse)
async def api_run_simulation(
    request: Request,
    payload: LLMRunRequest,
) -> Any:
    """Translate a natural-language intent into a simulation run.

    Args:
        payload.intent: NL intent (min 5 chars).
        payload.country_code: Optional ISO-3166-1 alpha-2 hint.
        payload.api_key: Optional provider key override (tests).

    Returns:
        LLMRunResponse with classified motor, metrics, timeline, narrative.
    """
    try:
        result = run_simulation(payload)
    except AmbiguityError as exc:
        return JSONResponse(
            status_code=422,
            content=LLMAmbiguityResponse(detail=exc.detail, requested_fields=exc.requested_fields).model_dump(),
        )
    except ServiceUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:  # pragma: no cover - defensive
        log.exception("run_simulation failed")
        raise HTTPException(status_code=500, detail="Internal server error")
    return result
