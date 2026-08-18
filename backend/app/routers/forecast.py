"""Forecast router — ``POST /v1/forecast``.

Projects future simulation states with confidence intervals using the
forecast engine.  Outgoing responses are validated against the DTO
namespace (``ForecastPoint``, ``Feasibility``, ``ForecastResponse``).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError

from backend.app.models import Feasibility, ForecastPoint, ForecastResponse
from backend.app.security import get_api_key, rate_limit_dependency

router = APIRouter(
    prefix="/forecast",
    tags=["forecast"],
)


@router.post("", dependencies=[Depends(get_api_key), Depends(rate_limit_dependency)])
async def v1_forecast(request: Request, payload: dict[str, Any]) -> ForecastResponse:
    """Run the MASSIVE temporal forecast engine.

    Payload fields:
        simulation_state: dict  – snapshot with optional ``ews`` metrics (required).
        temporal_config: dict  – TemporalConfig overrides (optional).
        mode: "analytical" | "monte_carlo" (optional, default ``analytical``).
        n_runs: int             – MC iterations (optional, default ``200``).

    Returns:
        ``ForecastResponse`` validated against the DTO schema.
    """
    from forecast.engine import forecast
    from forecast.temporal_config import TemporalConfig

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON body required")
    sim_state = payload.get("simulation_state")
    if not isinstance(sim_state, dict):
        raise HTTPException(status_code=400, detail="'simulation_state' (dict) is required")
    temporal_cfg = payload.get("temporal_config") or {}
    try:
        temporal_config = TemporalConfig(**(temporal_cfg if isinstance(temporal_cfg, dict) else {}))
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=exc.errors(),
        ) from exc
    result = forecast(
        sim_state,
        temporal_config=temporal_config,
        mode=payload.get("mode", "analytical"),
        n_runs=int(payload.get("n_runs", 200)),
    )
    data = result.model_dump() if hasattr(result, "model_dump") else dict(result)

    p_event = float(data.get("p_event", 0.0))
    point = ForecastPoint(
        tick=data.get("steps_to_event") or 0,
        mean_opinion=p_event,
        polarization=0.0,
        confidence_lower=max(0.0, p_event - 0.05),
        confidence_upper=min(1.0, p_event + 0.05),
    )
    feas = Feasibility(
        score=p_event,
        label=data.get("confidence") or "low",
        rationale=data.get("mode"),
    )
    return ForecastResponse(
        sim_id=payload.get("sim_id", "unknown"),
        horizon_ticks=data.get("steps_to_event") or 0,
        points=[point],
        feasibility=feas,
    )
