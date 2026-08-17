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

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.app.models import LLMAmbiguityResponse, LLMRunRequest, LLMRunResponse
from backend.app.security import get_api_key, rate_limit_dependency
from services.llm_orchestrator import classify_motor

log = logging.getLogger("massive.backend.routers.llm")

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
    country = payload.country
    ambiguities: list[str] = []

    if not motor_hint:
        resolved, amb = classify_motor(payload.intent, None)
        ambiguities = amb
        # Ambiguity that *cannot* be resolved by assumptions → ask the client.
        # Per contract, missing country for energy_engine/forecast may be
        # resolved via defaults, but a missing temporal horizon for a
        # forecast-intent blocks execution and requires user clarification.
    if ambiguities and any(
        a in ambiguities for a in ("temporal_horizon_days",)
    ) and not motor_hint:
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
    except ValueError as exc:
        log.warning("LLM run_simulation validation error: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        # LLM prerequisite missing for engine types that are inherently LLM-driven.
        log.warning("LLM run_simulation runtime error: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc))

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
