"""@deprecated — re-export only. Use massive.core.schemas directly."""

from massive.core.schemas import (  # noqa: F401
    GamePayoff,
    Intervention,
    StrategicConfig,
    StrategyMatrix,
)

__all__ = ["GamePayoff", "StrategicConfig", "Intervention", "StrategyMatrix"]
