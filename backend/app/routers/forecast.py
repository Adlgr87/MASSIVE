"""Forecast router — ``POST /v1/forecast``.

Projects future simulation states with confidence intervals using the
forecast engine.  Outgoing responses are validated against the DTO
namespace (``ForecastPoint``, ``Feasibility``, ``ForecastResponse``).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import ValidationError

from backend.app.models import (
    Feasibility,
    ForecastPoint,
    ForecastRequest,
    ForecastResponse,
)
from backend.app.security import get_api_key, rate_limit_dependency

router = APIRouter(
    prefix="/forecast",
    tags=["forecast"],
)


@router.post(
    "",
    dependencies=[Depends(get_api_key), Depends(rate_limit_dependency)],
)
async def v1_forecast(
    request: Request,
    payload: Annotated[ForecastRequest, Body()],
) -> ForecastResponse:
    """Run the MASSIVE temporal forecast engine.

    Payload fields:
        simulation_state: dict  – snapshot with optional ``ews`` metrics (required).
        temporal_config: dict  – TemporalConfig overrides (optional).
        mode: "analytical" | "monte_carlo" (optional, default ``analytical``).
        n_runs: int             – MC iterations (1–10 000, default ``200``).

    Returns:
        ``ForecastResponse`` validated against the DTO schema.
    """
    from forecast.temporal_config import TemporalConfig

    sim_state = payload.simulation_state
    temporal_cfg = payload.temporal_config or {}
    try:
        temporal_config = TemporalConfig(**(temporal_cfg if isinstance(temporal_cfg, dict) else {}))
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=exc.errors(),
        ) from exc

    import asyncio

    from forecast.engine import forecast as _run_forecast

    # Monte Carlo mode with high n_runs is CPU-bound (numpy batch sampling).
    # Offload to a thread pool so the FastAPI event loop stays responsive
    # and concurrent requests are not blocked by a single slow forecast.
    result = await asyncio.to_thread(
        _run_forecast,
        sim_state,
        temporal_config=temporal_config,
        mode=payload.mode,
        n_runs=payload.n_runs,
    )
    data = result.model_dump() if hasattr(result, "model_dump") else dict(result)

    p_event = float(data.get("p_event", 0.0))
    # Use engine-reported confidence bounds if available, otherwise use ±5%
    confidence_lower = data.get("p_ci_low", data.get("confidence_lower"))
    confidence_upper = data.get("p_ci_high", data.get("confidence_upper"))
    if confidence_lower is not None and confidence_upper is not None:
        cl, cu = float(confidence_lower), float(confidence_upper)
    else:
        cl, cu = max(0.0, p_event - 0.05), min(1.0, p_event + 0.05)
    point = ForecastPoint(
        tick=data.get("steps_to_event") or 0,
        mean_opinion=p_event,
        polarization=0.0,
        confidence_lower=cl,
        confidence_upper=cu,
    )
    feas = Feasibility(
        score=p_event,
        label=data.get("confidence") or "low",
        rationale=data.get("mode"),
    )
    return ForecastResponse(
        sim_id=payload.sim_id or "unknown",
        horizon_ticks=data.get("steps_to_event") or 0,
        points=[point],
        feasibility=feas,
    )
