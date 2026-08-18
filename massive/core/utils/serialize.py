# massive/core/utils/serialize.py - unified numpy->JSON serializer
"""JSON-safe serialization utilities for numpy arrays and scalars.

Centralizes the conversion logic used previously inline in
``backend/app/routers/simulation.py`` so every service layer
(country_params, LLM orchestrator, simulation_service) shares one
implementation — eliminating BUG-02 class serialization errors.
"""

from __future__ import annotations

from typing import Any

try:
    import numpy as np

    _numpy_available = True
except ImportError:  # pragma: no cover - numpy is a hard dep of massive_core
    np = None  # type: ignore[assignment]
    _numpy_available = False


def to_jsonable(value: Any) -> Any:
    """Recursively convert numpy types to JSON-friendly Python types.

    Handles: dict, list, tuple, np.ndarray, np.floating, np.integer,
    np.bool_, and falls back to ``str(value)`` for anything unknown.
    """
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if _numpy_available:
        if isinstance(value, np.ndarray):
            return to_jsonable(value.tolist())
        if isinstance(value, np.bool_):
            return bool(value)
        if isinstance(value, (np.floating, np.integer)):
            return value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, float):
        # handles non-numpy floats that are not JSON-finite
        import math

        if math.isnan(value) or math.isinf(value):
            return 0.0
        return value
    return str(value)


def is_numpy(value: Any) -> bool:
    """Return True if value is a numpy scalar or ndarray."""
    return _numpy_available and isinstance(value, (np.number, np.bool_, np.ndarray))
