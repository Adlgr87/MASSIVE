"""DTOs for forecast / predictive analytics endpoints.

These types are returned by endpoints that project future simulation states
given current conditions.  All models use ``extra="forbid"`` to prevent
silent schema drift.
"""

from __future__ import annotations

from typing import Any, Literal

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
    rationale: str | None = None


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
    points: list[ForecastPoint]
    feasibility: Feasibility


class ForecastRequest(BaseModel):
    """Request body for ``POST /v1/forecast``.

    Payload fields:
        simulation_state: dict  – snapshot with optional ``ews`` metrics (required).
        temporal_config: dict  – TemporalConfig overrides (optional).
        mode: "analytical" | "monte_carlo" (optional, default ``analytical``).
        n_runs: int             – MC iterations (default ``200``, capped at 10 000).
        sim_id: str             – simulation run identifier (optional).

    The ``n_runs`` bound (1..10_000) prevents unbounded Monte Carlo DoS.
    """

    model_config = {"extra": "forbid"}

    simulation_state: dict[str, Any] = Field(
        ...,
        description="Snapshot with optional EWS metrics (required).",
    )
    temporal_config: dict[str, Any] | None = Field(
        default=None,
        description="TemporalConfig overrides (optional).",
    )
    mode: Literal["analytical", "monte_carlo"] = Field(
        default="analytical",
        description="Forecast execution mode.",
    )
    n_runs: int = Field(
        default=200,
        ge=1,
        le=10_000,
        description="Monte Carlo iterations (1-10 000).",
    )
    sim_id: str | None = Field(
        default=None,
        description="Simulation run identifier.",
    )
