"""
Heuristic (deterministic) rule selector for LLM fallback.
"""

from typing import Dict, List


# Constante movida desde simulator.py
_STRATEGIC_POLARIZATION_THRESHOLD: float = 0.5


def llamar_llm_heuristico(estado: dict, escenario: str,
                           historial_reciente: list[dict], cfg: dict) -> dict:
    """
    Deterministic selector with expanded logic for all rules.
    Works as a baseline or fallback when no LLM is available.

    Args:
        estado: Current state.
        escenario: Current scenario.
        historial_reciente: History window.
        cfg: Global configuration.

    Returns:
        Rule decision dictionary.
    """
    from simulator_core.config import _neutro, _amplitud, EXTENDED_MODELS_AVAILABLE
    
    opinion    = estado["opinion"]
    propaganda = estado["propaganda"]
    confianza  = estado.get("confianza", 0.5)
    neutro     = _neutro(cfg)
    amp        = _amplitud(cfg)
    op_a       = estado.get("opinion_grupo_a", neutro + 0.3 * amp)
    op_b       = estado.get("opinion_grupo_b", neutro - 0.3 * amp)

    tendencia  = [h["opinion"] for h in historial_reciente]
    delta      = tendencia[-1] - tendencia[0] if len(tendencia) > 1 else 0.0

    zona_rechazo = neutro - 0.35 * amp
    umbral_prop  = neutro + 0.15 * amp
    distancia_grupos = abs(op_a - op_b)

    # Narrativa B activa → contagio competitivo
    if "narrativa_b" in estado and abs(estado.get("narrativa_b", 0)) > 0.2:
        return {"regla": 6,
                "params": {"competencia": cfg.get("competencia_peso", 0.4)},
                "razon": "contagio_competitivo: narrativa B activa y relevante"}

    # Capa estratégica activa + alta polarización → Replicador EGT
    # Los agentes ya están bajo presión de juego; el modelo evolutivo
    # captura mejor la dinámica de estrategias enfrentadas.
    if cfg.get("strategic", {}).get("enabled", False) and distancia_grupos > _STRATEGIC_POLARIZATION_THRESHOLD * amp:
        return {"regla": 9,
                "params": {"dt": 0.1},
                "razon": "replicador: capa estratégica activa con alta polarización entre grupos"}

    # Grupos muy distantes → HK (solo escucha a similares)
    if distancia_grupos > 0.6 * amp:
        return {"regla": 5,
                "params": {"epsilon": cfg.get("hk_epsilon", 0.3)},
                "razon": f"hk: grupos muy distantes ({distancia_grupos:.2f})"}

    # Rechazo establecido + propaganda → backlash
    if opinion < zona_rechazo and abs(propaganda) > 0.3:
        return {"regla": 3,
                "params": {"penalizacion": 0.12},
                "razon": f"backlash: rechazo establecido (op={opinion:.2f})"}

    # Tendencia fuerte ya iniciada → polarización
    if abs(delta) > 0.05 * amp:
        return {"regla": 4,
                "params": {"fuerza": 0.08},
                "razon": f"polarizacion: tendencia {'positiva' if delta>0 else 'negativa'} fuerte"}

    # Propaganda intensa + baja confianza → umbral
    if abs(propaganda) > abs(umbral_prop) and confianza < 0.5:
        return {"regla": 1,
                "params": {"umbral": round(abs(umbral_prop), 2), "incremento": 0.12},
                "razon": "umbral: propaganda intensa + baja confianza"}

    # Sistema cerca del neutro + grupos similares → homofilia
    if abs(opinion - neutro) < 0.1 * amp and distancia_grupos < 0.4 * amp:
        return {"regla": 8,
                "params": {"tasa": cfg.get("homofilia_tasa", 0.05)},
                "razon": "homofilia: sistema cerca del neutro, grupos convergentes"}

    # Sistema estable → memoria
    if abs(delta) < 0.01 * amp:
        return {"regla": 2,
                "params": {"alpha": 0.75, "beta": 0.18, "gamma": 0.07},
                "razon": "memoria: sistema estable, inercia dominante"}

    # Sistema estable con grupos muy similares → Nash equilibrium
    if EXTENDED_MODELS_AVAILABLE and distancia_grupos < 0.25 * amp and abs(delta) < 0.02 * amp:
        return {"regla": 10,
                "params": {"c_same": 2.0, "c_diff": 0.5},
                "razon": "nash: grupos próximos, equilibrio de coordinación"}

    return {"regla": 0,
            "params": {"a": 0.72, "b": 0.28},
            "razon": "lineal: condiciones moderadas"}
