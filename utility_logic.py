"""@deprecated — re-export only. Use massive.core.utility_logic directly."""

from __future__ import annotations

import warnings

warnings.warn(
    "utility_logic.py is a deprecated re-export; import from massive.core.utility_logic",
    DeprecationWarning,
    stacklevel=2,
)

from massive.core.utility_logic import calculate_strategic_force  # noqa: F401

__all__ = ["calculate_strategic_force"]
