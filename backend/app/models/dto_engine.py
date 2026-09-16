"""Request DTOs for the engine router (POST /v1/engine/energy, /v1/engine/architect).

All models use ``extra="forbid"`` and enforce anti-DoS bounds on the
population-size and iteration-count parameters that dominate compute cost.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class EngineEnergyRequest(BaseModel):
    """Request body for ``POST /v1/engine/energy``.

    Payload fields:
        user_goal: str        (required) – qualitative description driving
                                      the energy-landscape attractor/repeller setup.
        n_agents: int         (default 50)  – population size, capped at 200 000.
        steps: int            (default 100) – integration steps, capped at 10 000.
        connectivity: float   (default 0.3) – network density in ``[0, 1]``.
        range_type: str       (default ``"bipolar"``) – ``"bipolar"`` | ``"unipolar"``.
        seed: int             (default 42)  – RNG seed for reproducibility.
        config_overrides: dict            – extra engine-specific config.
    """

    model_config = {"extra": "forbid"}

    user_goal: str = Field(..., min_length=1, description="User goal driving the landscape.")
    n_agents: int = Field(
        default=50,
        ge=1,
        le=200_000,
        description="Population size (1–200 000).",
    )
    steps: int = Field(
        default=100,
        ge=1,
        le=10_000,
        description="Integration steps (1–10 000).",
    )
    connectivity: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Network connectivity density in [0, 1].",
    )
    range_type: Literal["bipolar", "unipolar"] = Field(
        default="bipolar",
        description="Opinion encoding range type.",
    )
    seed: int = Field(default=42, description="RNG seed for reproducibility.")
    config_overrides: dict[str, Any] | None = Field(
        default=None,
        description="Extra engine-specific configuration overrides.",
    )


class ArchitectRequest(BaseModel):
    """Request body for ``POST /v1/engine/architect``.

    Payload fields:
        estado_inicial: dict  (required) – initial simulator state.
        objetivo_usuario: str (required) – desired end-state description.
        max_intentos: int     (default 3) – inverse-search iterations, capped at 10.
        config: dict          – optional overrides.
        modo_simulacion: str  (default ``"macro"``) – simulation macro-mode.
        metricas_red: str     (default ``""``) – network metric selection.

    The ``max_intentos`` bound (1..10) prevents unbounded inverse-search DoS.
    """

    model_config = {"extra": "forbid"}

    estado_inicial: dict[str, Any] = Field(
        ...,
        description="Initial simulator state (required).",
    )
    objetivo_usuario: str = Field(
        ...,
        min_length=1,
        description="Desired end-state description (required).",
    )
    max_intentos: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Inverse-search iterations (1–10).",
    )
    config: dict[str, Any] | None = Field(
        default=None,
        description="Optional configuration overrides.",
    )
    modo_simulacion: str = Field(
        default="macro",
        description="Simulation macro-mode key.",
    )
    metricas_red: str = Field(
        default="",
        description="Network metric selection key (optional).",
    )
