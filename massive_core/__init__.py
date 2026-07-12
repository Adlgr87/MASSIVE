"""massive_core — stable adapter layer over the legacy MASSIVE simulator.

This package acts as the stable import surface for newer backend/frontend code.
It re-exports the public simulation API without touching the legacy Streamlit
root modules so that existing runtime behavior and import paths remain stable.

This module is an active compatibility adapter, not a redundant wrapper.
Its re-exports should only change as part of an explicit migration slice with
consumer mapping and validation.

Usage::

    from massive_core import simular, DEFAULT_CONFIG

No legacy files are moved; they continue to live at the repository root.
"""

from __future__ import annotations

import os
import sys
from typing import Any

# Ensure the repository root is importable regardless of the working directory.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from massive_core.benchmarks import run_canonical_benchmarks  # noqa: E402
from massive_core.config import ScientificRuntimeConfig  # noqa: E402
from massive_core.data_assimilation import (  # noqa: E402
    AssimilationResult,
    assimilate_history_observations,
)
from massive_core.diagnostics import (  # noqa: E402
    ScientificReport,
    build_scientific_report,
    trajectory_from_history,
)
from massive_core.metalearning import (
    build_cfc_regime_dataset_from_history,  # noqa: E402
)
from massive_core.scientific_runner import (  # noqa: E402
    ScientificEngineResult,
    ScientificSimulationResult,
    run_energy_scientific_simulation,
    run_multilayer_scientific_simulation,
    run_scientific_simulation,
)

_LEGACY_EXPORTS = {
    "DEFAULT_CONFIG",
    "DEFAULT_PAYOFF_MATRIX",
    "DESCRIPCIONES_REGLAS",
    "NOMBRES_REGLAS",
    "PROVEEDORES",
    "RANGOS_DISPONIBLES",
    "get_graph_metrics",
    "load_checkpoint",
    "resumen_historial",
    "save_checkpoint",
    "simular",
    "simular_multiples",
}


def __getattr__(name: str) -> Any:
    """Load legacy simulator exports on demand.

    Args:
        name: Public attribute requested from ``massive_core``.

    Returns:
        Attribute imported from the legacy ``simulator`` module.
    """

    if name in _LEGACY_EXPORTS:
        from simulator import __dict__ as simulator_symbols

        value = simulator_symbols[name]
        globals()[name] = value
        return value
    raise AttributeError(f"module 'massive_core' has no attribute {name!r}")


__all__ = [
    "ScientificRuntimeConfig",
    "run_canonical_benchmarks",
    "build_cfc_regime_dataset_from_history",
    "AssimilationResult",
    "assimilate_history_observations",
    "ScientificEngineResult",
    "ScientificSimulationResult",
    "run_energy_scientific_simulation",
    "run_multilayer_scientific_simulation",
    "run_scientific_simulation",
    "ScientificReport",
    "build_scientific_report",
    "trajectory_from_history",
    "DEFAULT_CONFIG",
    "DEFAULT_PAYOFF_MATRIX",
    "DESCRIPCIONES_REGLAS",
    "NOMBRES_REGLAS",
    "PROVEEDORES",
    "RANGOS_DISPONIBLES",
    "get_graph_metrics",
    "load_checkpoint",
    "resumen_historial",
    "save_checkpoint",
    "simular",
    "simular_multiples",
]
