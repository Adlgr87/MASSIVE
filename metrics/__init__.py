"""
metrics/ — Unified metric calculations for MASSIVE.

This module centralizes metric definitions that were previously scattered
and inconsistently implemented across engines. The goal is to eliminate
Metric-Divergence (the #1 systemic issue) by providing a single source of
truth for polarization and related reactive quantities.
"""

from .unified_metrics import (
    calculate_polarization,
    calculate_polarization_index,
    calculate_partisanship,
    calculate_cooperation,
    calculate_mean_opinion,
    calculate_std_opinion,
    polarization_gradient,
    polarization_velocity,
)

__all__ = [
    "calculate_polarization",
    "calculate_polarization_index",
    "calculate_partisanship",
    "calculate_cooperation",
    "calculate_mean_opinion",
    "calculate_std_opinion",
    "polarization_gradient",
    "polarization_velocity",
]
