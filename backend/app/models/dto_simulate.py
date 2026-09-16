"""Request DTOs for simulation endpoints (POST /v1/simulate).

These types govern the *input* contract for the simulation router.
All models use ``extra="forbid"`` to reject unknown fields (contract drift
detection) and enforce explicit anti-DoS bounds on population-intensive knobs.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SimRequest(BaseModel):
    """Request body for ``POST /v1/simulate``.

    Payload fields (all optional except noted):
        estado_inicial: dict  – initial simulator state (optional).
        escenario: str        – scenario key (default ``campana``).
        pasos: int            – number of simulation steps (default ``50``).
        config: dict          – overrides for ``DEFAULT_CONFIG``.
        verbose: bool         – emit step logs.

    The ``pasos`` bound (1..10_000) prevents unbounded step-count DoS.
    Extra fields are rejected (``extra="forbid"``) so clients cannot inject
    undocumented parameters.
    """

    model_config = {"extra": "forbid"}

    estado_inicial: dict[str, Any] | None = Field(
        default=None,
        description="Initial simulator state (defaults to neutral opinion).",
    )
    escenario: str = Field(
        default="campana",
        description="Scenario key in the rule registry.",
    )
    pasos: int = Field(
        default=50,
        ge=1,
        le=10_000,
        description="Number of simulation steps (1-10 000).",
    )
    config: dict[str, Any] | None = Field(
        default=None,
        description="Overrides for ``DEFAULT_CONFIG`` (may include ``seed``).",
    )
    verbose: bool = Field(
        default=False,
        description="Emit per-step logs.",
    )
