"""
Social dynamics rules for MASSIVE simulator.

This module contains functions for calculating group effects,
social influence, and coalition validation.

Author: MASSIVE Research
"""

import numpy as np
from typing import Dict, Any


def _get_rango(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gets the range configuration for the current simulation mode.
    
    Args:
        cfg: Configuration dictionary.
        
    Returns:
        Dictionary with range parameters (min, max, neutro, etc.).
    """
    bipolar = cfg.get("bipolar", False)
    
    if bipolar:
        return {
            "min": -1.0,
            "max": 1.0,
            "neutro": 0.0,
            "ejemplo_apoyo": 0.8,
            "ejemplo_rechazo": -0.8,
            "descripcion": "Bipolar: rechazo activo ≠ indiferencia"
        }
    else:
        return {
            "min": 0.0,
            "max": 1.0,
            "neutro": 0.5,
            "ejemplo_apoyo": 0.9,
            "ejemplo_rechazo": 0.1,
            "descripcion": "Probabilístico: 0-1 con neutro en 0.5"
        }


def calcular_efecto_grupos(estado: Dict[str, Any], cfg: Dict[str, Any]) -> float:
    """
    Calculates social pressure from affinity and opposing groups.
    Operates on differences, works for both [0,1] and [-1,1] ranges.

    Args:
        estado: Current state dictionary with opinion and group data.
        cfg: Global configuration dictionary.

    Returns:
        Social influence delta to apply to current opinion.
    """
    r = _get_rango(cfg)
    
    # Extract group opinions and belonging
    op_a = estado.get("opinion_grupo_a", r["ejemplo_apoyo"])
    op_b = estado.get("opinion_grupo_b", r["ejemplo_rechazo"])
    perten = estado.get("pertenencia_grupo", 0.6)
    
    # Calculate reference point (weighted average of group opinions)
    ref = perten * op_a + (1.0 - perten) * op_b
    
    # Apply social pressure towards reference
    return cfg["efecto_vecinos_peso"] * (ref - estado["opinion"])


def validar_coalicion(
    grupos: Dict[str, float], 
    umbral_coalicion: float = 0.5
) -> Dict[str, Any]:
    """
    Validates if a coalition can be formed from given groups.
    
    Args:
        grupos: Dictionary mapping group names to their support levels.
        umbral_coalicion: Minimum support threshold for coalition formation.
        
    Returns:
        Dictionary with coalition validity and supporting groups.
    """
    # Sort groups by support level
    sorted_groups = sorted(grupos.items(), key=lambda x: x[1], reverse=True)
    
    # Accumulate support until threshold is reached
    coalition_groups = []
    total_support = 0.0
    
    for group_name, support in sorted_groups:
        coalition_groups.append(group_name)
        total_support += support
        
        if total_support >= umbral_coalicion:
            break
    
    return {
        "valida": total_support >= umbral_coalicion,
        "grupos_apoyo": coalition_groups,
        "soporte_total": total_support,
        "umbral": umbral_coalicion
    }


def influencia_grupos(
    opinion_actual: float,
    grupos_opiniones: list[float],
    pesos: list[float],
    cfg: Dict[str, Any]
) -> float:
    """
    Calculates weighted influence from multiple groups.
    
    Args:
        opinion_actual: Current opinion value.
        grupos_opiniones: List of group opinion values.
        pesos: List of weights for each group.
        cfg: Configuration dictionary.
        
    Returns:
        Net influence value to apply.
    """
    # Normalize weights
    total_peso = sum(pesos)
    if total_peso == 0:
        return 0.0
        
    normalized_pesos = [p / total_peso for p in pesos]
    
    # Calculate weighted average of group opinions
    referencia = sum(
        op * peso 
        for op, peso in zip(grupos_opiniones, normalized_pesos)
    )
    
    # Return influence as difference from current opinion
    return cfg.get("influencia_social_factor", 1.0) * (referencia - opinion_actual)


def calcular_presion_social(
    estado: Dict[str, Any],
    red_nx: Any = None,
    cfg: Dict[str, Any] = None
) -> float:
    """
    Calculates comprehensive social pressure including network effects.
    
    Args:
        estado: Current simulation state.
        red_nx: Optional NetworkX graph for network-based calculations.
        cfg: Configuration dictionary.
        
    Returns:
        Total social pressure value.
    """
    cfg = cfg or {}
    
    # Base group effect
    efecto_base = calcular_efecto_grupos(estado, cfg)
    
    # Network effect if graph is provided
    efecto_red = 0.0
    if red_nx is not None:
        try:
            # Get neighbors' opinions if available in state
            vecinos = estado.get("vecinos_opiniones", [])
            if vecinos:
                promedio_vecinos = np.mean(vecinos)
                efecto_red = cfg.get("peso_red", 0.3) * (promedio_vecinos - estado["opinion"])
        except (KeyError, TypeError):
            pass  # Ignore if neighbor data not available
    
    return efecto_base + efecto_red
