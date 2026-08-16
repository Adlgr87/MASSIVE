"""DTOs for forecast / predictive analytics endpoints.

These types are returned by endpoints that project future simulation states
given current conditions.  All models use ``extra="forbid"`` to prevent
silent schema drift.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ForecastPoint(BaseModel):
    """Predicted state at a single future tick.

    Args:
        tick: Future tick index (relative to the forecast origin).
        mean_opinion: Predicted population mean opinion.
        polarization: Predicted polarization index.
        confidence_lower: Lower bound of the 95 % confidence interval.
        confidence_upper: Upper bound of the 95 % confidence interval.
    """

    model_config = {"extra": "forbid"}

    tick: int
    mean_opinion: float
    polarization: float
    confidence_lower: float
    confidence_upper: float


class Feasibility(BaseModel):
    """Feasibility assessment of reaching a target state.

    Args:
        score: Feasibility score in ``[0, 1]`` (higher → more feasible).
        label: Human-readable category (e.g. ``"high"``, ``"low"``).
        rationale: Optional explanation produced by the forecast model.
    """

    model_config = {"extra": "forbid"}

    score: float = Field(..., ge=0.0, le=1.0)
    label: str
    rationale: Optional[str] = None


class ForecastResponse(BaseModel):
    """Complete forecast for a simulation run.

    Args:
        sim_id: Simulation run identifier.
        horizon_ticks: Number of future ticks covered by the forecast.
        points: Ordered list of predicted tick states.
        feasibility: Feasibility assessment of the forecast target.
    """

    model_config = {"extra": "forbid"}

    sim_id: str
    horizon_ticks: int
    points: List[ForecastPoint]
    feasibility: Feasibility
