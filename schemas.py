"""Backward-compatible re-export — implementation lives in massive.core.schemas."""

from massive.core.schemas import (  # noqa: F401
    GamePayoff,
    Intervention,
    StrategicConfig,
    StrategyMatrix,
)

__all__ = ["GamePayoff", "StrategicConfig", "Intervention", "StrategyMatrix"]
