"""
MASSIVE Simulator Configuration

Configuración unificada y helpers del simulador.
Fix: Unifica imports duplicados de empirical_calibration y empirical_config.
"""

import logging
from typing import Dict, Any, Tuple

# ============================================================
# EMPÍRICAL CONFIGURATION - UNIFIED IMPORT
# Fix: Elimina shadowing bug donde empirical_config sobrescribía
#      los nombres importados de empirical_calibration
# ============================================================

try:
    from empirical_calibration import (
        MASSIVE_EMPIRICAL_MASTER,
        MASSIVE_RUNTIME_PARAMS,
        ENGINE_METADATA_KEYS,
        apply_empirical_profile,
        build_empirical_engine_config,
    )
    EMPIRICAL_AVAILABLE = True
except ImportError:
    # Fallback seguro si empirical_calibration no está disponible
    MASSIVE_EMPIRICAL_MASTER = {}
    MASSIVE_RUNTIME_PARAMS = {}
    ENGINE_METADATA_KEYS = []
    
    def apply_empirical_profile(config: dict) -> dict:
        """Stub: aplica perfil empírico (no-op si no disponible)"""
        return config
    
    def build_empirical_engine_config(base_config: dict) -> dict:
        """Stub: construye configuración empírica (no-op si no disponible)"""
        return base_config
    
    EMPIRICAL_AVAILABLE = False
    logging.getLogger("massive").warning(
        "[Empirical] empirical_calibration no disponible — usando configuración default."
    )

# ============================================================
# OPTIONAL DEPENDENCIES AVAILABILITY FLAGS
# Pattern: try/except ImportError para activación condicional
# CRÍTICO: No modificar estos guards sin mantener fallbacks
# ============================================================

# TDA (Topological Data Analysis)
try:
    from ripser import ripser as ripser_compute
    from persim import wasserstein as wasserstein_dist
    TDA_AVAILABLE = True
except ImportError:
    TDA_AVAILABLE = False
    logging.getLogger("massive").warning(
        "[TDA] ripser/persim no instalados — detección topológica desactivada."
    )

# Extended Models (Nash, Bayesian, SIR)
try:
    from extended_models import regla_nash, regla_bayesiana, regla_sir
    EXTENDED_MODELS_AVAILABLE = True
except ImportError:
    EXTENDED_MODELS_AVAILABLE = False
    logging.getLogger("massive").info(
        "[Extended] extended_models no disponible — reglas Nash/Bayes/SIR desactivadas."
    )

# CfC (Computational Flow Control) - Fast path neuronal
try:
    from cfc_router import CfCRouter
    _cfc = CfCRouter.get()
    CFC_AVAILABLE = _cfc.status["regime_selector"]
except ImportError:
    CFC_AVAILABLE = False
    _cfc = None
    logging.getLogger("massive").info(
        "[CfC] cfc_router no disponible — fast path neuronal desactivado."
    )

# ============================================================
# RANGE HELPERS
# Funciones auxiliares para manejo de rangos de opinión
# ============================================================

def clip_to_unit_interval(val: float) -> float:
    """
    Clip value to [0, 1] range.
    
    Used for confidence, belonging, and other unit-interval metrics.
    Critical fix: These should NOT be clipped to opinion range [-1, 1] in bipolar mode.
    
    Args:
        val: Value to clip
        
    Returns:
        Clipped value in [0, 1]
    """
    return max(0.0, min(1.0, val))


def normalize_opinion(val: float, opinion_range: Dict[str, float]) -> float:
    """
    Normalize opinion value to [0, 1] regardless of configured range.
    
    Args:
        val: Opinion value in current range
        opinion_range: Range dict with 'min', 'max', 'neutro' keys
        
    Returns:
        Normalized value in [0, 1]
    """
    r_min = opinion_range.get("min", 0.0)
    r_max = opinion_range.get("max", 1.0)
    
    if r_max == r_min:
        return 0.5
        
    return (val - r_min) / (r_max - r_min)


def opinion_range_clip(val: float, cfg: dict) -> float:
    """
    Clip value to configured opinion range.
    
    IMPORTANT: This is for OPINION values only.
    For confidence/belonging metrics, use clip_to_unit_interval() instead.
    
    See tests: test_simular_multiples_confianza_stays_non_negative_bipolar
               test_simular_multiples_unit_interval_keys_clipped_correctly
    
    Args:
        val: Value to clip
        cfg: Config dict with 'rango' key
        
    Returns:
        Clipped value to opinion range
    """
    rango_cfg = _get_rango(cfg)
    return float(max(rango_cfg["min"], min(rango_cfg["max"], val)))


def _get_rango(cfg: dict) -> Dict[str, Any]:
    """
    Get range configuration from config dict.
    
    Args:
        cfg: Config dict
        
    Returns:
        Range dict with 'min', 'max', 'neutro' keys
    """
    RANGOS_DISPONIBLES = {
        "[0, 1] — Probabilístico": {"min": 0.0, "max": 1.0, "neutro": 0.5},
        "[-1, 1] — Bipolar": {"min": -1.0, "max": 1.0, "neutro": 0.0},
    }
    
    nombre = cfg.get("rango", "[0, 1] — Probabilístico")
    return RANGOS_DISPONIBLES.get(nombre, RANGOS_DISPONIBLES["[0, 1] — Probabilístico"])


def get_neutro(cfg: dict) -> float:
    """Get neutral point from config."""
    return _get_rango(cfg)["neutro"]


def is_bipolar(cfg: dict) -> bool:
    """Check if range is bipolar (min < 0)."""
    return _get_rango(cfg)["min"] < 0


def get_amplitud(cfg: dict) -> float:
    """Get amplitude (max - min) of configured range."""
    r = _get_rango(cfg)
    return r["max"] - r["min"]

# ============================================================
# STRATEGIC LAYER WRAPPER
# Wrapper para fuerza estratégica (Teoría de Juegos)
# ============================================================

def calculate_strategic_force_wrapper(estado: dict, cfg: dict) -> float:
    """
    Wrapper para calcular fuerza estratégica.
    
    Delega a utility_logic.calculate_strategic_force manteniendo
    compatibilidad con la firma original.
    
    Args:
        estado: Estado actual del sistema
        cfg: Configuración del simulador
        
    Returns:
        Fuerza estratégica calculada
    """
    from utility_logic import calculate_strategic_force
    from schemas import GamePayoff
    
    return calculate_strategic_force(estado, cfg, GamePayoff)


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
    
    # Range helpers
    'clip_to_unit_interval',
    'normalize_opinion',
    'opinion_range_clip',
    '_get_rango',
    'get_neutro',
    'is_bipolar',
    'get_amplitud',
    
    # Strategic
    'calculate_strategic_force_wrapper',
]
