"""
MASSIVE Simulator - Advanced Dynamics Rules

Reglas avanzadas de dinámica social:
- regla_hk: Hegselmann-Krause (bounded confidence)
- regla_contagio_competitivo: Competitive contagion
- regla_umbral_heterogeneo: Granovetter threshold model
- regla_homofilia: Co-evolutionary network / homophily
- regla_replicador: Replicator equation (EGT)

Estas reglas extienden los modelos base con mecanismos más complejos
de interacción social.
"""

import numpy as np
from scipy import stats
from scipy.integrate import solve_ivp
from scipy.special import erf
from typing import Dict, Any


def _get_rango(cfg: dict) -> Dict[str, Any]:
    """Obtiene configuración de rango de opinión."""
    return cfg.get("rango", {
        "min": 0.0,
        "max": 1.0,
        "neutro": 0.5,
        "ejemplo_apoyo": 0.8,
        "ejemplo_rechazo": 0.2
    })


def _clip(val: float, cfg: dict) -> float:
    """Clip value to configured opinion range."""
    r = _get_rango(cfg)
    return float(max(r["min"], min(r["max"], val)))


def _amplitud(cfg: dict) -> float:
    """Calcula amplitud del rango de opinión."""
    r = _get_rango(cfg)
    return r["max"] - r["min"]


def _neutro(cfg: dict) -> float:
    """Obtiene punto neutro del rango."""
    return _get_rango(cfg).get("neutro", 0.5)


def _es_bipolar(cfg: dict) -> bool:
    """Verifica si el rango es bipolar [-1, 1] o unitario [0, 1]."""
    r = _get_rango(cfg)
    return r["min"] < 0


def _aplicar_sesgo_confirmacion(propaganda: float, opinion: float, cfg: dict) -> float:
    """
    Aplica sesgo de confirmación: propaganda contraria pierde peso.
    
    Args:
        propaganda: Valor de propaganda [-1, 1]
        opinion: Opinión actual del agente
        cfg: Configuración con rango
        
    Returns:
        Propaganda ajustada por sesgo de confirmación
    """
    neutro = _neutro(cfg)
    amp = _amplitud(cfg)
    
    # Distancia al neutro normalizada
    distancia_normalizada = abs(opinion - neutro) / amp
    
    # Sesgo: propaganda contraria se reduce exponencialmente
    signo_opinion = np.sign(opinion - neutro)
    signo_propaganda = np.sign(propaganda)
    
    if signo_opinion != signo_propaganda and signo_opinion != 0:
        # Propaganda contraria: reducir peso
        factor = np.exp(-2 * distancia_normalizada)
        return propaganda * factor
    else:
        # Propaganda congruente: mantener o amplificar ligeramente
        return propaganda * (1 + 0.2 * distancia_normalizada)


# ============================================================
# REGLA NUEVA 1: HEGSELMANN-KRAUSE (Bounded Confidence)
# Agentes solo interactúan con grupos dentro de radio ε.
# Referencia: Hegselmann & Krause (2002).
# Permite formación natural de clusters de opinión.
# ============================================================

def regla_hk(estado: dict, params: dict, cfg: dict) -> dict:
    """
    Hegselmann-Krause (2002) - Bounded Confidence model.
    Agents only interact with groups whose opinion is within a radius ε.

    Args:
        estado: Current state.
        params: Rule parameters (epsilon).
        cfg: Global configuration.

    Returns:
        Updated state.
    """
    epsilon = params.get("epsilon", cfg.get("hk_epsilon", 0.3))
    opinion = estado["opinion"]
    op_a    = estado.get("opinion_grupo_a", _get_rango(cfg)["ejemplo_apoyo"])
    op_b    = estado.get("opinion_grupo_b", _get_rango(cfg)["ejemplo_rechazo"])
    perten  = estado.get("pertenencia_grupo", 0.6)
    prop    = _aplicar_sesgo_confirmacion(estado["propaganda"], opinion, cfg)

    # Determinar qué grupos están dentro del radio de confianza
    grupos_validos = []
    pesos_validos  = []

    if abs(opinion - op_a) <= epsilon:
        grupos_validos.append(op_a)
        pesos_validos.append(perten)

    if abs(opinion - op_b) <= epsilon:
        grupos_validos.append(op_b)
        pesos_validos.append(1.0 - perten)

    nuevo = estado.copy()
    if grupos_validos:
        # Promedio ponderado solo de grupos dentro del radio
        total_peso   = sum(pesos_validos)
        opinion_ref  = sum(g * p for g, p in zip(grupos_validos, pesos_validos)) / total_peso
        # Convergencia gradual hacia la referencia de confianza
        alpha        = params.get("alpha", 0.3)
        val          = opinion + alpha * (opinion_ref - opinion) + 0.05 * prop
    else:
        # Nadie dentro del radio → fragmentación, opinión casi estática
        val = opinion + 0.01 * prop  # influencia mínima de propaganda

    nuevo["opinion"] = _clip(val, cfg)
    return nuevo


# ============================================================
# REGLA NUEVA 2: CONTAGIO COMPETITIVO
# Dos narrativas compiten simultáneamente.
# La narrativa B frena el avance de la narrativa A.
# Referencia: Beutel et al. (2012), Gleeson et al. (2014).
# ============================================================

def regla_contagio_competitivo(estado: dict, params: dict, cfg: dict) -> dict:
    """
    Competitive Contagion model based on Beutel et al. (2012).
    Models competition between two simultaneous narratives.

    Args:
        estado: Current state.
        params: Rule parameters (competencia).
        cfg: Global configuration.

    Returns:
        Updated state.
    """
    competencia  = params.get("competencia", cfg.get("competencia_peso", 0.4))
    opinion      = estado["opinion"]
    narrativa_a  = _aplicar_sesgo_confirmacion(estado["propaganda"], opinion, cfg)
    # narrativa_b puede estar en el estado o inferirse como la opuesta
    narrativa_b  = estado.get("narrativa_b", -narrativa_a if _es_bipolar(cfg) else 1.0 - narrativa_a)

    # Influencia neta: A gana si es más fuerte que B
    influencia_neta = narrativa_a - competencia * narrativa_b
    neutro          = _neutro(cfg)

    # La influencia neta empuja la opinión hacia o desde el neutro
    nuevo = estado.copy()
    val   = opinion + 0.15 * influencia_neta * (1.0 - abs(opinion - neutro) / _amplitud(cfg))
    nuevo["opinion"] = _clip(val, cfg)
    return nuevo


# ============================================================
# REGLA NUEVA 3: UMBRAL HETEROGÉNEO (Granovetter)
# Cada "agente" tiene su propio umbral de adopción.
# La distribución de umbrales genera cascadas sociales.
# Referencia: Granovetter (1978).
# ============================================================

def regla_umbral_heterogeneo(estado: dict, params: dict, cfg: dict) -> dict:
    """
    Heterogeneous Threshold model based on Granovetter (1978).
    Thresholds are normally distributed, enabling social cascades.

    Args:
        estado: Current state.
        params: Rule parameters (media, std).
        cfg: Global configuration.

    Returns:
        Updated state.
    """
    media   = params.get("media", cfg.get("umbral_media", 0.5))
    std     = params.get("std",   cfg.get("umbral_std",   0.15))
    opinion = estado["opinion"]
    neutro  = _neutro(cfg)
    prop    = _aplicar_sesgo_confirmacion(estado["propaganda"], opinion, cfg)

    # Fracción de la población que ya superó su umbral personal
    # (modelado con CDF de la normal)
    fraccion_adoptantes = 0.5 * (1 + erf((opinion - neutro - media + 0.5) / (std * np.sqrt(2))))
    fraccion_adoptantes = float(np.clip(fraccion_adoptantes, 0.0, 1.0))

    # La fracción de adoptantes genera presión social adicional
    r    = _get_rango(cfg)
    val  = opinion + 0.2 * fraccion_adoptantes * (r["max"] - opinion) + 0.05 * prop

    nuevo = estado.copy()
    nuevo["opinion"] = _clip(val, cfg)
    # Guardar fracción para análisis
    nuevo["_fraccion_adoptantes"] = round(fraccion_adoptantes, 3)
    return nuevo


# ============================================================
# REGLA NUEVA 4: HOMOFILIA (Red Co-evolutiva)
# Los pesos de influencia de los grupos cambian con la opinión.
# Cuanto más similar la opinión de un grupo, más influye.
# Referencia: Axelrod (1997), Centola et al. (2007).
# ============================================================

def regla_homofilia(estado: dict, params: dict, cfg: dict) -> dict:
    """
    Axelrod (1997) - Co-evolutionary Network / Homophily.
    Influence weights change based on opinion similarity.

    Args:
        estado: Current state.
        params: Rule parameters (tasa).
        cfg: Global configuration.

    Returns:
        Updated state.
    """
    tasa    = params.get("tasa", cfg.get("homofilia_tasa", 0.05))
    opinion = estado["opinion"]
    op_a    = estado.get("opinion_grupo_a", _get_rango(cfg)["ejemplo_apoyo"])
    op_b    = estado.get("opinion_grupo_b", _get_rango(cfg)["ejemplo_rechazo"])
    perten  = estado.get("pertenencia_grupo", 0.6)
    prop    = _aplicar_sesgo_confirmacion(estado["propaganda"], opinion, cfg)

    amp    = _amplitud(cfg)
    # Similitud normalizada al rango
    sim_a  = 1.0 - abs(opinion - op_a) / amp
    sim_b  = 1.0 - abs(opinion - op_b) / amp

    # Actualizar pertenencia según similitud (homofilia)
    nuevo_perten = float(np.clip(perten + tasa * (sim_a - sim_b), 0.1, 0.9))

    # Calcular referencia social con nuevos pesos
    ref_social   = nuevo_perten * op_a + (1.0 - nuevo_perten) * op_b
    peso_social  = cfg.get("efecto_vecinos_peso", 0.05)

    val  = opinion + peso_social * (ref_social - opinion) + 0.08 * prop

    nuevo = estado.copy()
    nuevo["opinion"]           = _clip(val, cfg)
    nuevo["pertenencia_grupo"] = nuevo_perten  # persiste al próximo paso
    nuevo["_sim_grupo_a"]      = round(sim_a, 3)
    nuevo["_sim_grupo_b"]      = round(sim_b, 3)
    return nuevo


# ============================================================
# TASK 2 — REPLICATOR EQUATION (EGT)
# Two-strategy evolutionary game theory model.
# Frequencies evolve according to relative payoff.
# Reference: Taylor & Jonker (1978), Weibull (1995).
# ============================================================

def regla_replicador(estado: dict, params: dict, cfg: dict) -> dict:
    """
    Replicator Equation - Evolutionary Game Theory.
    Strategy frequencies evolve based on relative payoffs.

    Args:
        estado: Current state with 'population_frequencies' and 'payoff_matrix'.
        params: Rule parameters (dt).
        cfg: Global configuration.

    Returns:
        Updated state with new population frequencies.
    """
    from simulator_core.dynamics_rules.basic import _clip
    
    dt = params.get("dt", cfg.get("replicador_dt", 0.1))
    population_states = estado.get("population_frequencies", np.array([0.5, 0.5]))
    payoff_matrix = estado.get("payoff_matrix", np.array([[3, 0], [5, 1]]))
    
    # Aplicar ecuación del replicador
    new_pop = apply_replicator_equation(population_states, payoff_matrix, dt)
    
    nuevo = estado.copy()
    nuevo["population_frequencies"] = new_pop
    
    # Convertir a opinión dominante para compatibilidad
    if len(new_pop) >= 2:
        # Opinión basada en estrategia más exitosa
        nuevo["opinion"] = _clip(new_pop[0], cfg)
    
    return nuevo


def apply_replicator_equation(
    population_states: np.ndarray,
    payoff_matrix: np.ndarray,
    dt: float,
) -> np.ndarray:
    """
    Integrates one step of the replicator ODE using RK45.

    Args:
        population_states: 1-D array of strategy frequencies summing to 1.
        payoff_matrix: Square payoff matrix (n_strategies × n_strategies).
        dt: Integration time span [0, dt].

    Returns:
        Updated normalised frequency array after one step.
    """
    pop = np.array(population_states, dtype=float)
    total = np.sum(pop)
    if total == 0.0:
        return pop
    pop = pop / total

    def replicator_rhs(t: float, x: np.ndarray) -> np.ndarray:
        x = np.clip(x, 0.0, 1.0)
        s = np.sum(x)
        if s > 0.0:
            x = x / s
        f = payoff_matrix @ x
        f_avg = x @ f
        return x * (f - f_avg)

    sol = solve_ivp(replicator_rhs, [0.0, dt], pop, method="RK45", dense_output=False)
    new_pop = sol.y[:, -1]
    new_pop = np.clip(new_pop, 0.0, 1.0)
    total_new = np.sum(new_pop)
    return new_pop / total_new if total_new > 0.0 else pop


# ============================================================
# TASK 1 — EWS / CRITICAL SLOWING DOWN (CSD)
# Early Warning Signals based on variance, lag-1 autocorrelation,
# and skewness computed over a sliding opinion window.
# References: Scheffer et al. (2009), Dakos et al. (2012).
# ============================================================

def calculate_ews_metrics(window_data: list) -> dict:
    """
    Calculates Early Warning Signal metrics over a sliding window.

    Accepts a list of scalar floats (one opinion per time step) and
    returns per-variable arrays for variance, lag-1 autocorrelation,
    and skewness. The scalar time series is reshaped to (T, 1) so
    the return dict always contains 1-D arrays of length 1.

    Args:
        window_data: List of scalar opinion values, length == HISTORY_BUFFER_SIZE.

    Returns:
        Dict with keys "variance", "autocorr", "skewness", each a np.ndarray
        of shape (n_vars,).
    """
    data_array = np.array(window_data, dtype=float)
    if data_array.ndim == 1:
        data_array = data_array.reshape(-1, 1)  # shape: (T, n_vars)

    variance = np.var(data_array, axis=0)

    n_vars = data_array.shape[1]
    autocorr = np.zeros(n_vars)
    for i in range(n_vars):
        if data_array.shape[0] > 1:
            cc = np.corrcoef(data_array[:-1, i], data_array[1:, i])
            val = cc[0, 1]
            autocorr[i] = val if not np.isnan(val) else 0.0

    skewness = stats.skew(data_array, axis=0)
    return {"variance": variance, "autocorr": autocorr, "skewness": skewness}


def check_ews_signals(metrics: dict, thresholds: dict) -> dict:
    """
    Checks computed EWS metrics against configurable thresholds.

    Args:
        metrics: Output of calculate_ews_metrics.
        thresholds: Dict with optional keys "mean_variance_threshold"
                    (default 0.1), "mean_autocorr_threshold" (default 0.5),
                    "mean_skewness_threshold" (default 0.5).

    Returns:
        Dict with bool flags "high_variance", "high_autocorr", "high_skewness".
    """
    return {
        "high_variance": bool(
            np.mean(metrics["variance"]) > thresholds.get("mean_variance_threshold", 0.1)
        ),
        "high_autocorr": bool(
            np.mean(metrics["autocorr"]) > thresholds.get("mean_autocorr_threshold", 0.5)
        ),
        "high_skewness": bool(
            np.mean(np.abs(metrics["skewness"])) > thresholds.get("mean_skewness_threshold", 0.5)
        ),
    }


__all__ = [
    # Advanced rules
    'regla_hk',
    'regla_contagio_competitivo',
    'regla_umbral_heterogeneo',
    'regla_homofilia',
    'regla_replicador',
    
    # EWS functions
    'calculate_ews_metrics',
    'check_ews_signals',
    
    # Replicator
    'apply_replicator_equation',
]
