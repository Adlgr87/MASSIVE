"""Request DTO for the benchmark router (POST /v1/benchmarks).

All models use ``extra="forbid"`` to reject unknown fields and enforce
bounds on seed values.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BenchmarkRequest(BaseModel):
    """Request body for ``POST /v1/benchmarks``.

    Payload fields:
        cases: str         – path to cases directory (default ``datasets/pvu_cases``).
        mode: str          – ``"offline"`` | ``"real"`` | ``"llm"`` (default ``offline``).
        seed: int          – RNG seed (default 42, non-negative).
        out: str           – output directory (default ``reports/validation/ci``).

    Path traversal is rejected at the router level via ``_sanitize_path``
    on top of these bounded fields.
    """

    model_config = {"extra": "forbid"}

    cases: str = Field(
        default="datasets/pvu_cases",
        description="Path to cases directory (relative).",
    )
    mode: Literal["offline", "real", "llm"] = Field(
        default="offline",
        description="Benchmark execution mode.",
    )
    seed: int = Field(
        default=42,
        ge=0,
        description="RNG seed for reproducibility (non-negative).",
    )
    out: str = Field(
        default="reports/validation/ci",
        description="Output directory (relative).",
    )
