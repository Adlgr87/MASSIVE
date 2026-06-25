"""
MASSIVE — app package

Compatibility wrapper that exposes the core simulation API so that
``import app`` works as a lightweight library import without triggering
Streamlit's runtime context requirements.

This module is an active backward-compatibility surface.  Its re-exports
should not be removed or "simplified" unless an equivalent public import
path is introduced and verified across the project.

The interactive Streamlit UI lives in ``app.py`` and is launched via::

    streamlit run app.py
"""

from simulator import (
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
