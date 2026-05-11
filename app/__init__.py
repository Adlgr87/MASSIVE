"""
MASSIVE — app package

Exposes the core simulation API so that ``import app`` works as a library
import without triggering Streamlit's runtime context requirements.

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
