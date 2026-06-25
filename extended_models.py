"""Backward-compatible re-export — implementation lives in massive.core.extended_models."""

from massive.core.extended_models import (  # noqa: F401
    regla_bayesiana,
    regla_nash,
    regla_sir,
)

__all__ = ["regla_nash", "regla_bayesiana", "regla_sir"]
