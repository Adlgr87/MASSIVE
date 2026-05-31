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

# Ensure the repository root is importable regardless of the working directory.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from simulator import (  # noqa: E402
    DEFAULT_CONFIG,
    DEFAULT_PAYOFF_MATRIX,
    DESCRIPCIONES_REGLAS,
    NOMBRES_REGLAS,
    PROVEEDORES,
    RANGOS_DISPONIBLES,
    get_graph_metrics,
    load_checkpoint,
    resumen_historial,
    save_checkpoint,
    simular,
    simular_multiples,
)

__all__ = [
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
