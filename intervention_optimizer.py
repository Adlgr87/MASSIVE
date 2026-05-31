"""Backward-compatible re-export — implementation lives in massive.core.intervention_optimizer."""

from massive.core.intervention_optimizer import optimize_interventions  # noqa: F401

__all__ = ["optimize_interventions"]
