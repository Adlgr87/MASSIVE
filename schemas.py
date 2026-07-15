"""@deprecated — re-export only. Use massive.core.schemas directly."""

from __future__ import annotations

import warnings

warnings.warn(
    "schemas.py is a deprecated re-export; import from massive.core.schemas instead",
    DeprecationWarning,
    stacklevel=2,
)

from massive.core.schemas import (  # noqa: F401
    GamePayoff,
    Intervention,
    StrategicConfig,
    StrategyMatrix,
)

__all__ = ["GamePayoff", "StrategicConfig", "Intervention", "StrategyMatrix"]
