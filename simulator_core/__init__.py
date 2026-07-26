"""
MASSIVE Simulator Core

Módulos refactorizados del núcleo de simulación.
Ver simulator.py para interfaz pública legacy (backward-compatible).
"""

from simulator_core.config import (
    # Empirical configuration (unified - fixes duplicate import bug)
    MASSIVE_EMPIRICAL_MASTER,
    MASSIVE_RUNTIME_PARAMS,
    ENGINE_METADATA_KEYS,
    apply_empirical_profile,
    build_empirical_engine_config,
    EMPIRICAL_AVAILABLE,
    
    # Optional dependencies availability flags
    TDA_AVAILABLE,
    EXTENDED_MODELS_AVAILABLE,
    CFC_AVAILABLE,
    
    # Range helpers
    clip_to_unit_interval,
    normalize_opinion,
    opinion_range_clip,
)

# GamePayoff se importa directamente de schemas para evitar circular imports
from schemas import GamePayoff

# Strategic force wrapper
from simulator_core.config import calculate_strategic_force_wrapper

__all__ = [
    # Empirical config
    'MASSIVE_EMPIRICAL_MASTER',
    'MASSIVE_RUNTIME_PARAMS',
    'ENGINE_METADATA_KEYS',
    'apply_empirical_profile',
    'build_empirical_engine_config',
    'EMPIRICAL_AVAILABLE',
    
    # Availability flags
    'TDA_AVAILABLE',
    'EXTENDED_MODELS_AVAILABLE',
    'CFC_AVAILABLE',
    
    # Helpers
    'clip_to_unit_interval',
    'normalize_opinion',
    'opinion_range_clip',
    
    # Strategic
    'calculate_strategic_force_wrapper',
    'GamePayoff',
]
