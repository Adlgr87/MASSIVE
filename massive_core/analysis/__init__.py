"""Canonical analysis surface for MASSIVE.

Re-exports the preferred StabilityAnalyzer / StabilityReport implementations
from ``massive_core.numerics.stability`` so callers have one import path.

Note:
    ``massive_core.physics.perturbation_theory.StabilityReport`` is a related
    but physics-specific dataclass used by PerturbationTheorySolver — keep it.
    ``massive_core.numerics.multilayer_engine_sparse.StabilityAnalyzer`` is a
    sparse-engine helper; prefer ``SparseStabilityAnalyzer`` for that path.
"""

from massive_core.numerics.stability import (
    StabilityAnalyzer,
    StabilityReport,
    SparseStabilityAnalyzer,
)

__all__ = [
    "StabilityAnalyzer",
    "StabilityReport",
    "SparseStabilityAnalyzer",
]
