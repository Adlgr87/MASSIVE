from __future__ import annotations

"""
⚠️ DEPRECATION NOTICE
====================
This file is part of a legacy schema system.

Canonical location: massive/core/schemas.py
This file: Primary schema file - contains core DTOs

Migration: Update all imports from schemas.py to massive.core.schemas
"""
"""@deprecated — re-export only. Use massive.core.schemas directly."""

import warnings

warnings.warn(
    "schemas.py is a deprecated re-export; import from massive.core.schemas instead",
    DeprecationWarning,
    stacklevel=2,
)

from massive.core.schemas import (  # noqa: E402, F401
    GamePayoff,
    Intervention,
    StrategicConfig,
    StrategyMatrix,
)

__all__ = ["GamePayoff", "StrategicConfig", "Intervention", "StrategyMatrix"]
