"""@deprecated — re-export only. Use massive.core.intervention_optimizer directly."""

from __future__ import annotations

import warnings

warnings.warn(
    "intervention_optimizer.py is a deprecated re-export; "
    "import from massive.core.intervention_optimizer",
    DeprecationWarning,
    stacklevel=2,
)

from massive.core.intervention_optimizer import optimize_interventions  # noqa: F401

__all__ = ["optimize_interventions"]
