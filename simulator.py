"""
MASSIVE — Simulador híbrido de dinámica social
Núcleo numérico + LLM como selector de régimen dinámico

Modelos integrados:
  REGLAS BASE (originales):
    0: lineal       — cambio proporcional suave
    1: umbral       — salto al cruzar punto crítico
    2: memoria      — inercia del estado pasado
    3: backlash     — propaganda refuerza posición contraria
    4: polarizacion — aleja la opinión del neutro (cámara de eco)

  MODELOS NUEVOS:
    5: hk           — Hegselmann-Krause: confianza acotada, formación natural de clusters
    6: contagio_competitivo — dos narrativas compitiendo simultáneamente
    7: umbral_heterogeneo   — distribución de umbrales (Granovetter), cascadas sociales
    8: homofilia    — red co-evolutiva: los pesos de influencia cambian con la opinión

  MECANISMOS TRANSVERSALES (se aplican a todas las reglas):
    · sesgo_confirmacion  — propaganda contraria pierde peso según posición actual
    · homofilia dinámica  — actualiza pesos de grupos en cada paso

RANGOS DE OPINIÓN:
  [0, 1] — Probabilístico. Neutro=0.5
  [-1, 1] — Bipolar. Neutro=0.0. Rechazo activo ≠ indiferencia.

PROVEEDORES LLM:
  heurístico | ollama | groq | openai | openrouter

Autor: MASSIVE Research
"""

import json
import logging
from collections import Counter, deque
from pathlib import Path
from typing import Any

import networkx as nx
import copy

import numpy as np
import requests
from scipy import stats
from scipy.integrate import solve_ivp
from scipy.special import erf

from benchmarks.butterfly_diagnostic import run_butterfly_diagnostic_core
from massive_engine import MassiveEngine
from massive_core.rust_core import langevin_opinion_update_inplace
from multilayer_engine import MultilayerEngine
from schemas import GamePayoff
from utility_logic import calculate_strategic_force
from llm_credentials import resolve_provider_api_key
from empirical_calibration import (
    MASSIVE_EMPIRICAL_MASTER,
    MASSIVE_RUNTIME_PARAMS,
    ENGINE_METADATA_KEYS,
    apply_empirical_profile,
    build_empirical_engine_config,
)
from empirical_config import MASSIVE_EMPIRICAL_MASTER, MASSIVE_RUNTIME_PARAMS

try:
    from ripser import ripser as ripser_compute
    from persim import wasserstein as wasserstein_dist
    TDA_AVAILABLE = True
except ImportError:
    TDA_AVAILABLE = False
    logging.getLogger("massive").warning(
        "[TDA] ripser/persim no instalados — detección topológica desactivada."
    )

try:
    from extended_models import regla_nash, regla_bayesiana, regla_sir
    EXTENDED_MODELS_AVAILABLE = True
except ImportError:
    EXTENDED_MODELS_AVAILABLE = False

# CfC INTEGRATION — fast path neuronal para selector de régimen
try:
    from cfc_router import CfCRouter
    _cfc = CfCRouter.get()
    CFC_AVAILABLE = _cfc.status["regime_selector"]
except ImportError:
    CFC_AVAILABLE, _cfc = False, None

# EMPIRICAL INTEGRATION — importar base empírica si está disponible
try:
    from empirical_config import MASSIVE_RUNTIME_PARAMS, EMPIRICAL_BASE_LOADED
    EMPIRICAL_AVAILABLE = True
except ImportError:
    EMPIRICAL_AVAILABLE = False
    MASSIVE_RUNTIME_PARAMS = {}

# ------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------
LOG_PATH = Path("massive_run.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("massive")


# ------------------------------------------------------------
# RANGOS DE OPINIÓN
# ------------------------------------------------------------
RANGOS_DISPONIBLES: dict[str, dict] = {
    "[0, 1] — Probabilístico": {
        "min": 0.0, "max": 1.0, "neutro": 0.5,
        "descripcion": "Opinión como probabilidad de apoyo. Neutro=0.5. Modelos SIR, adopción.",
        "ejemplo_apoyo": 0.8, "ejemplo_rechazo": 0.2, "ejemplo_neutro": 0.5,
        "defaults": {
            "opinion_inicial": 0.50, "propaganda": 0.70, "confianza": 0.40,
            "opinion_grupo_a": 0.72, "opinion_grupo_b": 0.28,
        },
    },
    "[-1, 1] — Bipolar": {
        "min": -1.0, "max": 1.0, "neutro": 0.0,
        "descripcion": "Rechazo activo en negativo. Neutro=0. Polarización, campañas, elecciones.",
        "ejemplo_apoyo": 0.7, "ejemplo_rechazo": -0.7, "ejemplo_neutro": 0.0,
        "defaults": {
            "opinion_inicial": 0.00, "propaganda": 0.40, "confianza": 0.40,
            "opinion_grupo_a": 0.65, "opinion_grupo_b": -0.55,
        },
    },
}

# ------------------------------------------------------------
# PROVEEDORES LLM
# ------------------------------------------------------------
PROVEEDORES: dict[str, dict] = {
    "heurístico": {
        "descripcion": "Sin LLM — lógica determinista, sin costo ni API key",
        "requiere_key": False, "base_url": None,
        "modelos_sugeridos": ["(ninguno)"],
    },
    "ollama": {
        "descripcion": "LLM local con Ollama — privado, sin costo por llamada",
        "requiere_key": False, "base_url": "http://localhost:11434",
        "modelos_sugeridos": ["llama3:8b", "mistral:7b", "phi3:mini", "gemma2:2b"],
    },
    "groq": {
        "descripcion": "Groq Cloud — muy rápido, tier gratuito generoso",
        "requiere_key": True, "base_url": "https://api.groq.com/openai/v1",
        "modelos_sugeridos": [
            "llama-3.1-8b-instant", "llama-3.3-70b-versatile",
            "meta-llama/llama-4-scout-17b-16e-instruct",
        ],
    },
    "openai": {
        "descripcion": "OpenAI API — GPT-4o, GPT-4o-mini, etc.",
        "requiere_key": True, "base_url": "https://api.openai.com/v1",
        "modelos_sugeridos": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-nano"],
    },
    "openrouter": {
        "descripcion": "OpenRouter — acceso a cientos de modelos con una sola key",
        "requiere_key": True, "base_url": "https://openrouter.ai/api/v1",
        "modelos_sugeridos": [
            "meta-llama/llama-3.3-70b-instruct",
            "google/gemini-flash-1.5",
            "mistralai/mistral-7b-instruct",
        ],
    },
}

# ------------------------------------------------------------
# CONFIGURACIÓN POR DEFECTO
# ------------------------------------------------------------
DEFAULT_CONFIG: dict[str, Any] = {
    # Rango
    "rango": "[0, 1] — Probabilístico",
    # LLM
    "proveedor": "heurístico",
    "modelo": "",
    "api_key": "",
    "ollama_host": "http://localhost:11434",
    "llm_timeout": 20,
    "llm_temperature": 0.0,
    # Motor
    "alpha_blend": 0.8,
    "ruido_base": 0.03,
    "ruido_desconfianza": 0.08,
    "efecto_vecinos_peso": 0.05,
    "ventana_historial_llm": 6,
    # Simulación múltiple
    "ruido_estado_inicial": 0.01,
    # ── Nuevos mecanismos ──────────────────────────────────
    # Sesgo de confirmación: propaganda contraria pierde peso
    # 0.0 = sin sesgo | 1.0 = sesgo total (ignora información contraria)
    "sesgo_confirmacion": 0.3,
    # HK — Confianza Acotada
    # Solo se escucha a quienes están a ≤ epsilon de distancia
    "hk_epsilon": 0.3,
    # Contagio Competitivo
    # Peso de la narrativa B al competir con la A
    "competencia_peso": 0.4,
    # Umbral Heterogéneo (Granovetter)
    # Media y std de la distribución de umbrales individuales
    "umbral_media": 0.5,
    "umbral_std":   0.15,
    # Homofilia dinámica
    # Velocidad con la que los pesos de grupo se actualizan según similitud de opinión
    "homofilia_tasa": 0.05,
    # ── Capa Estratégica (Teoría de Juegos) ───────────────
    # enabled  : activa la fuerza estratégica sobre cada paso
    # payoff   : matriz 2×2 Cooperar/Defectar en rango [-1, 1]
    #   cc =  1.0 → ambos cooperan (consenso)
    #   cd = -1.0 → yo coopero, el otro traiciona (ingenuo)
    #   dc =  1.0 → yo traiciono, el otro coopera (tentación)
    #   dd = -1.0 → ambos traicionan (caos)
    # strategic_weight (ω): cuánto pesa la fuerza estratégica [0.0–1.0]
    "strategic": {
        "enabled": False,
        "payoff_matrix": {"cc": 1.0, "cd": -1.0, "dc": 1.0, "dd": -1.0},
        "strategic_weight": 0.3,
    },
    # Simulador integrado (dinámica emergente)
    "n_agents": 500,
    "n_ticks": 100,
    "dt": 0.1,
    "diffusion_sigma": 0.05,
    "enable_levy_jumps": False,
    "levy_lambda": 0.01,
    "alpha_stable": 1.5,
    "jump_magnitude_scale": 0.5,
    "enable_dynamic_topology": False,
    "topology_update_freq": 10,
    "topology_intensity": 0.05,
    "butterfly_interval": 100,
    "butterfly_threshold": 0.5,
}

# Default 2×2 payoff matrix for the Replicator (EGT) rule.
# Represents a symmetric coordination game where strategy A slightly
# dominates.  Override via cfg["payoff_matrix"] at runtime.
DEFAULT_PAYOFF_MATRIX: list[list[float]] = [[1.0, 0.0], [0.0, 1.0]]

# Rangos válidos de parámetros del LLM
_RANGOS_PARAMS: dict[str, dict[str, tuple]] = {
    "lineal":               {"a": (0.5, 0.9), "b": (0.1, 0.5)},
    "umbral":               {"umbral": (0.3, 0.8), "incremento": (0.05, 0.3)},
    "memoria":              {"alpha": (0.5, 0.8), "beta": (0.1, 0.3), "gamma": (0.05, 0.2)},
    "backlash":             {"penalizacion": (0.05, 0.3)},
    "polarizacion":         {"fuerza": (0.05, 0.25)},
    "hk":                   {"epsilon": (0.1, 0.6)},
    "contagio_competitivo": {"competencia": (0.2, 0.7)},
    "umbral_heterogeneo":   {"media": (0.3, 0.7), "std": (0.05, 0.25)},
    "homofilia":            {"tasa": (0.02, 0.15)},
    "replicador":           {"dt": (0.01, 1.0)},
    "nash":                 {"c_same": (1.0, 3.0), "c_diff": (0.0, 1.5), "intensity": (0.5, 2.0)},
    "bayesiano":            {"n_prior": (5.0, 20.0), "n_obs": (2.0, 10.0), "inertia": (0.1, 0.8)},
    "sir":                  {"beta": (0.05, 0.8), "gamma": (0.01, 0.5), "dt": (0.05, 0.5)},
}

# Sliding-window size used by EWS metrics and TDA detection
HISTORY_BUFFER_SIZE: int = 10

# Fraction of the opinion-range amplitude beyond which groups are considered
# highly polarised when the strategic layer is active (used by the heuristic
# selector to prefer the EGT Replicator rule).
_STRATEGIC_POLARIZATION_THRESHOLD: float = 0.5
_INTEGRATED_CFC_HISTORY_MIN: int = 6
_INTEGRATED_CFC_DRIFT_SCALE: float = 0.002
_INTEGRATED_DRIFT_FALLBACK_STD: float = 0.01
_INTEGRATED_LEVY_CLIP: float = 10.0
_INTEGRATED_CENSORSHIP_POLARIZATION_THRESHOLD: float = 0.7
_INTEGRATED_TOPOLOGY_POLARIZATION_CENTER: float = 0.5
_INTEGRATED_TOPOLOGY_INTENSITY_MIN: float = 0.01
_INTEGRATED_TOPOLOGY_INTENSITY_MAX: float = 0.2


# ============================================================
# HELPERS DE RANGO
# Toda la lógica de rango pasa por aquí — motor agnóstico al rango.
# ============================================================

def _get_rango(cfg: dict) -> dict:
    nombre = cfg.get("rango", "[0, 1] — Probabilístico")
    return RANGOS_DISPONIBLES.get(nombre, RANGOS_DISPONIBLES["[0, 1] — Probabilístico"])

def _clip(val: float, cfg: dict) -> float:
    r = _get_rango(cfg)
    return float(np.clip(val, r["min"], r["max"]))

def _neutro(cfg: dict) -> float:
    return _get_rango(cfg)["neutro"]

def _es_bipolar(cfg: dict) -> bool:
    return _get_rango(cfg)["min"] < 0

def _amplitud(cfg: dict) -> float:
    r = _get_rango(cfg)
    return r["max"] - r["min"]


# ============================================================
# MECANISMO: CAPA ESTRATÉGICA (Teoría de Juegos)
# Transversal — se suma al gradiente físico en cada paso.
# El threshold de "vecinos cerca del neutro" usa 0.2 en rango [-1, 1]
# (|avg| < 0.2) y la misma magnitud absoluta para [0, 1].
# ============================================================

def _calcular_fuerza_estrategica(estado: dict, cfg: dict) -> float:
    """
    Applies the Game Theory strategic force to the current state.

    When the strategic layer is enabled in cfg["strategic"], this
    function calls calculate_strategic_force() with the agent's
    neighbours (groups A and B) and scales the result to the same
    order of magnitude as calcular_efecto_grupos().

    Args:
        estado: Current simulation state.
        cfg: Global configuration, must contain "strategic" sub-dict.

    Returns:
        Signed float delta to add to the opinion update, or 0.0 when
        the layer is disabled.
    """
    strategic_cfg = cfg.get("strategic", {})
    if not strategic_cfg.get("enabled", False):
        return 0.0

    neutro = _neutro(cfg)
    payoff = GamePayoff(**strategic_cfg.get("payoff_matrix", {}))
    w = float(np.clip(strategic_cfg.get("strategic_weight", 0.3), 0.0, 1.0))

    neighbors = [
        estado.get("opinion_grupo_a", neutro),
        estado.get("opinion_grupo_b", neutro),
    ]

    # proximity_threshold: 0.2 absolute — correct for [-1,1] (neutral=0)
    # and reasonable for [0,1] (neutral=0.5, checks |avg-0.5|<0.2)
    force = calculate_strategic_force(
        estado["opinion"], neighbors, payoff,
        neutral=neutro, proximity_threshold=0.2,
    )

    # Scale to match other per-step forces (efecto_vecinos_peso ≈ 0.05)
    scale = cfg.get("efecto_vecinos_peso", 0.05)
    return w * force * scale


# ============================================================
# MECANISMO: SESGO DE CONFIRMACIÓN
# Transversal — se aplica antes de pasar la propaganda a cualquier regla.
# Referencia: Sunstein (2009), Nickerson (1998).
# ============================================================

def _aplicar_sesgo_confirmacion(propaganda: float, opinion: float,
                                 cfg: dict) -> float:
    """
    Reduces the weight of information contrary to the current position.

    If propaganda and opinion point in the same direction from the neutral point,
    the propaganda keeps its full weight. If they are in opposite directions,
    the propaganda is attenuated according to the confirmation bias parameter.

    Args:
        propaganda: The incoming narrative/propaganda value.
        opinion: The current opinion of the agent/system.
        cfg: Configuration dictionary containing "sesgo_confirmacion".

    Returns:
        The attenuated propaganda value.
    """
    sesgo   = float(np.clip(cfg.get("sesgo_confirmacion", 0.0), 0.0, 1.0))
    neutro  = _neutro(cfg)

    if sesgo == 0.0:
        return propaganda

    # Detect if they are in opposite directions from neutral
    misma_dir = (opinion - neutro) * (propaganda - neutro) >= 0
    if misma_dir:
        return propaganda
    else:
        # Attenuation proportional to bias
        return propaganda * (1.0 - sesgo)


# ============================================================
# MECANISMO: HOMOFILIA DINÁMICA
# La fuerza de influencia de cada grupo se ajusta según similitud de opinión.
# Referencia: Axelrod (1997), Flache et al. (2017).
# ============================================================

def _actualizar_pesos_homofilia(estado: dict, cfg: dict) -> float:
    """
    Calculates new influence weights based on opinion similarity.

    The more similar a group's opinion is to the system's state,
    the more influence it gains (selective exposure/homophily).

    Args:
        estado: Current state of the simulation.
        cfg: Configuration dictionary containing "homofilia_tasa".

    Returns:
        The updated group identity/belonging intensity.
    """
    tasa     = float(np.clip(cfg.get("homofilia_tasa", 0.05), 0.0, 0.3))
    opinion  = estado["opinion"]
    op_a     = estado.get("opinion_grupo_a", 0.7)
    op_b     = estado.get("opinion_grupo_b", 0.3)
    perten   = estado.get("pertenencia_grupo", 0.6)

    # Similarity = 1 - normalized distance to range
    amp      = _amplitud(cfg)
    sim_a    = 1.0 - abs(opinion - op_a) / amp
    sim_b    = 1.0 - abs(opinion - op_b) / amp

    # Update belonging towards the most similar group
    nuevo_perten = perten + tasa * (sim_a - sim_b)
    nuevo_perten = float(np.clip(nuevo_perten, 0.1, 0.9))
    return nuevo_perten


# ============================================================
# REGLAS DE TRANSICIÓN — ORIGINALES (mejoradas con rango dual)
# ============================================================

def regla_lineal(estado: dict, params: dict, cfg: dict) -> dict:
    """
    Linear transition rule based on Friedkin-Johnsen model.
    Opinion changes proportionally to current opinion and propaganda.

    Args:
        estado: Current state.
        params: Rule parameters (a: resistance, b: influence).
        cfg: Global configuration.

    Returns:
        Updated state.
    """
    a, b  = params.get("a", 0.7), params.get("b", 0.3)
    prop  = _aplicar_sesgo_confirmacion(estado["propaganda"], estado["opinion"], cfg)
    nuevo = estado.copy()
    nuevo["opinion"] = _clip(a * estado["opinion"] + b * prop, cfg)
    return nuevo


def regla_umbral(estado: dict, params: dict, cfg: dict) -> dict:
    """
    Threshold/Tipping point rule based on Granovetter (Simple).
    A non-linear jump occurs when propaganda exceeds a critical threshold.

    Args:
        estado: Current state.
        params: Rule parameters (umbral, incremento).
        cfg: Global configuration.

    Returns:
        Updated state.
    """
    r          = _get_rango(cfg)
    umbral     = params.get("umbral", 0.65 if not _es_bipolar(cfg) else 0.4)
    incremento = params.get("incremento", 0.15)
    prop       = _aplicar_sesgo_confirmacion(estado["propaganda"], estado["opinion"], cfg)
    nuevo = estado.copy()
    if abs(prop) > abs(umbral):
        signo = np.sign(prop) if _es_bipolar(cfg) else 1.0
        val   = estado["opinion"] + signo * incremento * (r["max"] - abs(estado["opinion"]))
    else:
        val = estado["opinion"]
    nuevo["opinion"] = _clip(val, cfg)
    return nuevo


def regla_memoria(estado: dict, params: dict, cfg: dict) -> dict:
    """
    Inertia rule based on DeGroot with lag.
    The current state depends on the previous state and history.

    Args:
        estado: Current state.
        params: Rule parameters (alpha, beta, gamma).
        cfg: Global configuration.

    Returns:
        Updated state.
    """
    alpha = params.get("alpha", 0.7)
    beta  = params.get("beta",  0.2)
    gamma = params.get("gamma", 0.1)
    prev  = estado.get("opinion_prev", estado["opinion"])
    prop  = _aplicar_sesgo_confirmacion(estado["propaganda"], estado["opinion"], cfg)
    nuevo = estado.copy()
    nuevo["opinion"] = _clip(
        alpha * estado["opinion"] + beta * prev + gamma * prop, cfg
    )
    return nuevo


def regla_backlash(estado: dict, params: dict, cfg: dict) -> dict:
    """
    Backlash/Boomerang effect rule.
    Propaganda reinforces the opposite position when negative sentiment is established.

    Args:
        estado: Current state.
        params: Rule parameters (penalizacion).
        cfg: Global configuration.

    Returns:
        Updated state.
    """
    penalizacion = params.get("penalizacion", 0.15)
    prop         = _aplicar_sesgo_confirmacion(estado["propaganda"], estado["opinion"], cfg)
    nuevo = estado.copy()
    neutro = _neutro(cfg)
    if _es_bipolar(cfg):
        if estado["opinion"] < neutro:
            val = estado["opinion"] - penalizacion * abs(prop)
        else:
            val = estado["opinion"]
    else:
        umbral_inf = params.get("umbral_inferior", 0.35)
        if estado["opinion"] < umbral_inf:
            val = estado["opinion"] - penalizacion * prop
        else:
            val = estado["opinion"]
    nuevo["opinion"] = _clip(val, cfg)
    return nuevo


def regla_polarizacion(estado: dict, params: dict, cfg: dict) -> dict:
    """
    Polarization/Echo chamber rule.
    Moves opinion further away from the neutral point.

    Args:
        estado: Current state.
        params: Rule parameters (fuerza).
        cfg: Global configuration.

    Returns:
        Updated state.
    """
    fuerza  = params.get("fuerza", 0.1)
    opinion = estado["opinion"]
    neutro  = _neutro(cfg)
    r       = _get_rango(cfg)
    nuevo   = estado.copy()
    if opinion >= neutro:
        val = opinion + fuerza * (r["max"] - opinion)
    else:
        val = opinion - fuerza * (opinion - r["min"])
    nuevo["opinion"] = _clip(val, cfg)
    return nuevo


# ============================================================
# REGLA NUEVA 1: HEGSELMANN-KRAUSE (Confianza Acotada)
# Solo se escucha a quienes están dentro de epsilon de distancia.
# Genera clustering y polarización de forma emergente.
# Referencia: Hegselmann & Krause (2002).
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


# ============================================================
# TASK 2 — REPLICATOR EQUATION (EGT)
# Two-strategy evolutionary game theory model.
# Frequencies evolve according to relative payoff.
# Reference: Taylor & Jonker (1978), Weibull (1995).
# ============================================================

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


def regla_replicador(estado: dict, params: dict, cfg: dict) -> dict:
    """
    Replicator Equation (EGT) — two-strategy evolutionary game theory.

    Models the evolutionary pressure between two group alignments:
      Strategy 0 → align with group A (opinion_grupo_a)
      Strategy 1 → align with group B (opinion_grupo_b)

    pertenencia_grupo tracks the frequency of Strategy 0.  After
    integrating the replicator ODE, opinion shifts to the payoff-
    weighted group average.

    Args:
        estado: Current state.
        params: Rule parameters (payoff_matrix, dt).
        cfg: Global configuration.

    Returns:
        Updated state with new opinion and pertenencia_grupo.
    """
    pertenencia = estado.get("pertenencia_grupo", 0.6)
    pop = np.array([pertenencia, 1.0 - pertenencia], dtype=float)

    raw_payoff = params.get(
        "payoff_matrix",
        cfg.get("payoff_matrix", DEFAULT_PAYOFF_MATRIX),
    )
    payoff_matrix = np.array(raw_payoff, dtype=float)
    if payoff_matrix.shape != (2, 2):
        payoff_matrix = np.eye(2)

    dt = float(params.get("dt", cfg.get("dt", 0.1)))
    updated = apply_replicator_equation(pop, payoff_matrix, dt)

    nuevo_perten = float(np.clip(updated[0], 0.1, 0.9))
    op_a = estado.get("opinion_grupo_a", _get_rango(cfg)["ejemplo_apoyo"])
    op_b = estado.get("opinion_grupo_b", _get_rango(cfg)["ejemplo_rechazo"])

    nuevo = estado.copy()
    nuevo["pertenencia_grupo"] = nuevo_perten
    nuevo["opinion"] = _clip(
        nuevo_perten * op_a + (1.0 - nuevo_perten) * op_b,
        cfg,
    )
    return nuevo


# ============================================================
# TASK 3 — TDA / PERSISTENT HOMOLOGY (EWS advanced)
# Detects topological changes in the opinion time series via
# delay-embedding and Wasserstein distance between persistence
# diagrams.  Only activated when ripser + persim are installed.
# Reference: Carlsson (2009), Perea & Harer (2015).
# ============================================================

def detect_topological_change(
    time_series: np.ndarray,
    prev_diagram: "np.ndarray | None",
    embedding_dim: int = 2,
    tau: int = 1,
    wasserstein_threshold: float = 0.3,
) -> "tuple[bool, np.ndarray | None]":
    """
    Detects significant topological changes via Takens-embedding + PH.

    Embeds the scalar time series in R^embedding_dim using a lag of tau,
    computes the H1 persistence diagram via Vietoris-Rips filtration, and
    returns True if the Wasserstein distance to the previous diagram
    exceeds wasserstein_threshold.

    Args:
        time_series: 1-D numpy array of opinion values.
        prev_diagram: H1 persistence diagram from the previous call, or None.
        embedding_dim: Takens embedding dimension (default 2).
        tau: Delay parameter for Takens embedding (default 1).
        wasserstein_threshold: Distance threshold for declaring a change.

    Returns:
        (change_detected: bool, current_h1_diagram: np.ndarray | None)
    """
    if not TDA_AVAILABLE:
        return False, prev_diagram

    min_len = embedding_dim * tau + 1
    if len(time_series) < min_len:
        return False, prev_diagram

    n = len(time_series) - (embedding_dim - 1) * tau
    embedded = np.array(
        [time_series[i: i + embedding_dim * tau: tau] for i in range(n)],
        dtype=float,
    )

    diagrams = ripser_compute(embedded, maxdim=1)["dgms"]
    h1: np.ndarray = diagrams[1] if len(diagrams) > 1 else np.empty((0, 2))

    if prev_diagram is None:
        return False, h1

    finite_prev = (
        prev_diagram[np.isfinite(prev_diagram[:, 1])]
        if len(prev_diagram) > 0
        else np.empty((0, 2))
    )
    finite_curr = (
        h1[np.isfinite(h1[:, 1])]
        if len(h1) > 0
        else np.empty((0, 2))
    )

    if len(finite_prev) == 0 and len(finite_curr) == 0:
        return False, h1

    dist = wasserstein_dist(finite_curr, finite_prev)
    return bool(dist > wasserstein_threshold), h1


# ============================================================
# REGISTRO DE REGLAS
# ============================================================

REGLAS: dict[str, dict[int, Any]] = {
    "campana": {
        0: regla_lineal,
        1: regla_umbral,
        2: regla_memoria,
        3: regla_backlash,
        4: regla_polarizacion,
        5: regla_hk,
        6: regla_contagio_competitivo,
        7: regla_umbral_heterogeneo,
        8: regla_homofilia,
        9: regla_replicador,
    }
}

if EXTENDED_MODELS_AVAILABLE:
    REGLAS["campana"][10] = regla_nash
    REGLAS["campana"][11] = regla_bayesiana
    REGLAS["campana"][12] = regla_sir

NOMBRES_REGLAS = {
    0: "lineal",
    1: "umbral",
    2: "memoria",
    3: "backlash",
    4: "polarizacion",
    5: "hk",
    6: "contagio_competitivo",
    7: "umbral_heterogeneo",
    8: "homofilia",
    9: "replicador",
    10: "nash",
    11: "bayesiano",
    12: "sir",
}

# Descripción de cada regla para la UI
DESCRIPCIONES_REGLAS = {
    0: "Cambio proporcional suave",
    1: "Salto al cruzar punto crítico",
    2: "Inercia del estado pasado",
    3: "Propaganda refuerza posición contraria",
    4: "Aleja del neutro (cámara de eco)",
    5: "Confianza acotada — solo escucha a similares (Hegselmann-Krause)",
    6: "Dos narrativas compiten simultáneamente",
    7: "Distribución de umbrales — cascadas sociales (Granovetter)",
    8: "Red co-evolutiva — homofilia dinámica",
    9: "Ecuación replicadora — dinámica evolutiva de estrategias (EGT)",
    10: "Equilibrio de Nash — estrategias estables en juego de coordinación",
    11: "Red Bayesiana — actualización probabilística de creencias",
    12: "SIR Epidemiológico — contagio de opiniones como epidemia",
}


# ============================================================
# VALIDADOR DE PARÁMETROS LLM
# ============================================================

def _validar_params(regla_nombre: str, params: dict) -> dict:
    rangos = _RANGOS_PARAMS.get(regla_nombre, {})
    return {
        k: float(np.clip(v, *rangos[k])) if k in rangos and isinstance(v, (int, float)) else v
        for k, v in params.items()
    }


# ============================================================
# CONSTRUCCIÓN DEL PROMPT — consciente del rango y nuevas reglas
# ============================================================

def _construir_prompt(estado: dict, escenario: str,
                      historial_reciente: list[dict], cfg: dict) -> str:
    """
    Constructs the prompt for the LLM selector.

    Args:
        estado: Current state of the simulation.
        escenario: The current simulation scenario.
        historial_reciente: Last N steps of history.
        cfg: Global configuration.

    Returns:
        The formatted prompt string.
    """
    es_bipolar = _es_bipolar(cfg)
    tendencia  = [round(h["opinion"], 3) for h in historial_reciente]
    delta      = round(tendencia[-1] - tendencia[0], 3) if len(tendencia) > 1 else 0.0
    direccion  = "rising" if delta > 0.02 else ("falling" if delta < -0.02 else "stable")

    estado_fmt = {
        k: round(v, 3) if isinstance(v, float) else v
        for k, v in estado.items() if not k.startswith("_")
    }

    rango_desc = (
        "[-1, 1]: 0=neutral, negative=active rejection, positive=support"
        if es_bipolar else
        "[0, 1]: 0.5=neutral, 0=total rejection, 1=total support"
    )

    ejemplos = """
Decision Examples:
- opinion near neutral, low propaganda, stable system → memoria
- intense propaganda crosses threshold, system moves → umbral
- groups very distant from each other → hk (bounded confidence)
- established rejection + active propaganda → backlash
- two active and tense narratives → contagio_competitivo
- strong trend already started → polarizacion
- social cascade effect desired → umbral_heterogeneo
- groups tend to cluster by similarity → homofilia
- evolutionary pressure between group strategies → replicador
- groups converging, coordination equilibrium → nash
- probabilistic belief update with evidence → bayesiano
- epidemic-like opinion spread → sir"""

    base_prompt = f"""You are a rule selector for a social dynamics simulation.
Scenario: {escenario} | Range: {rango_desc}

State:
{json.dumps(estado_fmt, ensure_ascii=False)}

Opinion Trend (last {len(tendencia)} steps): {tendencia}
Direction: {direccion} (Δ={delta:+.3f})
{ejemplos}

Available Rules:
0: lineal               — smooth proportional change
1: umbral               — jump when crossing critical point
2: memoria              — past state inertia
3: backlash             — propaganda reinforces opposite position
4: polarizacion         — moves away from neutral (echo chamber)
5: hk                   — bounded confidence, only listen to similar ones
6: contagio_competitivo — two narratives compete simultaneously
7: umbral_heterogeneo   — social cascades (Granovetter)
8: homofilia            — co-evolutionary network, groups by similarity
9: replicador           — evolutionary game theory, strategy frequencies
10: nash               — Nash equilibrium, stable coordination strategies
11: bayesiano          — Bayesian network, probabilistic belief update
12: sir                — SIR epidemiological contagion

Respond ONLY with JSON:
{{"regla": <0-12>, "params": {{...}}, "razon": "<explanation>"}}
Fallback: {{"regla": 0, "params": {{}}, "razon": "fallback"}}
"""

    ews_flags = estado.get("_ews_flags", {})
    ews_context = ""
    if ews_flags:
        ews_context = (
            f"\n[EWS] high_variance={ews_flags.get('high_variance', False)}, "
            f"high_autocorr={ews_flags.get('high_autocorr', False)}, "
            f"high_skewness={ews_flags.get('high_skewness', False)}. "
            "These indicate proximity to a bifurcation tipping point "
            "(B-tipping via Critical Slowing Down)."
        )
    return base_prompt + ews_context


# ============================================================
# CAPA LLM
# ============================================================

def _extraer_json(texto: str) -> dict | None:
    inicio = texto.find("{")
    fin    = texto.rfind("}") + 1
    if inicio == -1 or fin == 0:
        return None
    try:
        return json.loads(texto[inicio:fin])
    except json.JSONDecodeError:
        return None


def _llamar_openai_compatible(
    prompt: str,
    base_url: str,
    modelo: str,
    cfg: dict,
    proveedor: str,
) -> dict | None:
    api_key = resolve_provider_api_key(proveedor, fallback=cfg.get("api_key", ""))
    if not api_key:
        log.warning(f"Sin API key para proveedor '{proveedor}'.")
        return None
    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": modelo,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": cfg.get("llm_temperature", DEFAULT_CONFIG["llm_temperature"]),
                "max_tokens": 300,
            },
            timeout=cfg.get("llm_timeout", DEFAULT_CONFIG["llm_timeout"]),
        )
        resp.raise_for_status()
        return _extraer_json(resp.json()["choices"][0]["message"]["content"])
    except requests.exceptions.ConnectionError:
        log.error(f"No se pudo conectar a {base_url}.")
    except requests.exceptions.Timeout:
        log.warning(f"Timeout ({cfg.get('llm_timeout', DEFAULT_CONFIG['llm_timeout'])}s) en {base_url}.")
    except (KeyError, IndexError) as e:
        log.warning(f"Error parseando respuesta: {e}")
    return None


def _llamar_ollama(prompt: str, cfg: dict) -> dict | None:
    try:
        resp = requests.post(
            f"{cfg['ollama_host']}/api/generate",
            json={
                "model":   cfg["modelo"],
                "prompt":  prompt,
                "stream":  False,
                "options": {"temperature": cfg["llm_temperature"]},
            },
            timeout=cfg["llm_timeout"],
        )
        resp.raise_for_status()
        return _extraer_json(resp.json().get("response", ""))
    except requests.exceptions.ConnectionError:
        log.error("Ollama no responde. → ollama serve")
    except requests.exceptions.Timeout:
        log.warning(f"Timeout ({cfg['llm_timeout']}s) en Ollama.")
    except KeyError as e:
        log.warning(f"Error parseando Ollama: {e}")
    return None


def llamar_llm(estado: dict, escenario: str,
                historial_reciente: list[dict], cfg: dict) -> dict:
    """
    Main dispatcher for LLM selectors.

    Args:
        estado: Current state.
        escenario: Current scenario.
        historial_reciente: History window for context.
        cfg: Global configuration.

    Returns:
        A dictionary with "regla", "params", and "razon".
    """
    proveedor = cfg.get("proveedor", "heurístico")

    if proveedor == "heurístico":
        return llamar_llm_heuristico(estado, escenario, historial_reciente, cfg)

    prompt = _construir_prompt(estado, escenario, historial_reciente, cfg)
    data   = None

    if proveedor == "ollama":
        data = _llamar_ollama(prompt, cfg)
    elif proveedor in PROVEEDORES:
        info    = PROVEEDORES[proveedor]
        modelo  = cfg.get("modelo", "").strip() or info["modelos_sugeridos"][0]
        if not resolve_provider_api_key(proveedor, fallback=cfg.get("api_key", "")):
            log.error(f"'{proveedor}' requiere API key. → heurístico.")
            return llamar_llm_heuristico(estado, escenario, historial_reciente, cfg)
        data = _llamar_openai_compatible(
            prompt,
            info["base_url"],
            modelo,
            cfg,
            proveedor,
        )
    else:
        log.error(f"Proveedor desconocido: '{proveedor}'. → heurístico.")
        return llamar_llm_heuristico(estado, escenario, historial_reciente, cfg)

    if data is None:
        log.warning("LLM sin respuesta → heurístico.")
        return llamar_llm_heuristico(estado, escenario, historial_reciente, cfg)

    regla_id = int(data.get("regla", 0))
    if regla_id not in REGLAS.get(escenario, {}):
        log.warning(f"Regla inválida ({regla_id}) → fallback.")
        return {"regla": 0, "params": {}, "razon": "fallback"}

    return {"regla": regla_id, "params": data.get("params", {}), "razon": data.get("razon", "")}


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


# ============================================================
# EFECTO DE GRUPOS
# ============================================================

def calcular_efecto_grupos(estado: dict, cfg: dict) -> float:
    """
    Calculates social pressure from affin and opposing groups.
    Operates on differences, works for both [0,1] and [-1,1] ranges.

    Args:
        estado: Current state.
        cfg: Global configuration.

    Returns:
        Social influence delta.
    """
    r      = _get_rango(cfg)
    op_a   = estado.get("opinion_grupo_a", r["ejemplo_apoyo"])
    op_b   = estado.get("opinion_grupo_b", r["ejemplo_rechazo"])
    perten = estado.get("pertenencia_grupo", 0.6)
    ref    = perten * op_a + (1.0 - perten) * op_b
    return cfg["efecto_vecinos_peso"] * (ref - estado["opinion"])


# ============================================================
# SIMULADOR PRINCIPAL
# ============================================================

def simular(
    estado_inicial: dict,
    escenario: str = "campana",
    pasos: int = 50,
    cada_n_pasos: int = 5,
    config: dict | None = None,
    verbose: bool = True,
) -> list[dict]:
    """
    Executes the hybrid simulation with all available rules.

    Args:
        estado_inicial: Dictionary with at least "opinion" and "propaganda".
        escenario: Scenario key in REGLAS.
        pasos: Number of time steps.
        cada_n_pasos: Frequency of LLM rule selection updates.
        config: Override dictionary for DEFAULT_CONFIG.
        verbose: If true, logs step details.

    Returns:
        A list of state dictionaries (including t=0).
    """
    cfg         = {**DEFAULT_CONFIG, **(config or {})}
    # EMPIRICAL INTEGRATION — aplicar parámetros empíricos como defaults antes que el usuario los sobreescriba
    # Los parámetros del usuario en config tienen prioridad; los valores 0.0 se tratan como neutralidad activa.
    if EMPIRICAL_AVAILABLE and MASSIVE_RUNTIME_PARAMS:
        cultural_profile = str((config or {}).get("cultural_profile", "mixed"))
        empirical_defaults = build_empirical_engine_config(cultural_profile)
        # Only set keys NOT already overridden by the caller's config argument
        user_keys = set((config or {}).keys())
        for k, v in empirical_defaults.items():
            # strategic requires nested merging; cultural_profile and
            # validation_flags are metadata, not simulator control knobs.
            if k in ENGINE_METADATA_KEYS:
                continue
            if k not in user_keys:
                cfg[k] = v
        if "strategic" not in user_keys:
            # strategic needs nested merging so empirical payoffs enrich the
            # default matrix without discarding other simulator defaults.
            strategic_defaults = empirical_defaults.get("strategic", {})
            payoff_defaults = strategic_defaults.get("payoff_matrix", {})
            cfg["strategic"] = {
                **cfg.get("strategic", {}),
                **{k: v for k, v in strategic_defaults.items() if k != "payoff_matrix"},
                "payoff_matrix": {
                    **cfg.get("strategic", {}).get("payoff_matrix", {}),
                    **payoff_defaults,
                },
            }
    r           = _get_rango(cfg)
    alpha_blend = cfg["alpha_blend"]
    proveedor   = cfg.get("proveedor", "heurístico")
    # Local RNG for all stochastic updates in this run (no process-global RNG).
    _seed = cfg.get("seed", None)
    rng = np.random.default_rng(_seed)

    estado = estado_inicial.copy()
    estado.setdefault("opinion_prev",     estado["opinion"])
    estado.setdefault("confianza",        0.5)
    estado.setdefault("opinion_grupo_a",  min(estado["opinion"] + 0.2 * _amplitud(cfg), r["max"]))
    estado.setdefault("opinion_grupo_b",  max(estado["opinion"] - 0.2 * _amplitud(cfg), r["min"]))
    estado.setdefault("pertenencia_grupo", 0.6)

    historial: list[dict] = [estado.copy()]
    regla_actual   = 0
    params_actuales: dict = {}
    razon_actual   = "inicial"

    # EWS: sliding window of scalar opinion values
    opinion_history: deque = deque(maxlen=HISTORY_BUFFER_SIZE)
    # Mutable runtime state for non-serialisable objects (e.g. TDA diagram)
    cfg_runtime: dict = {}

    def _seleccionar(est, hist):
        # EGT Replicator forced mode: bypass LLM and lock to rule 9
        if cfg.get("modelo_matematico") == "Replicator":
            payoff = np.array(
                cfg.get("payoff_matrix", DEFAULT_PAYOFF_MATRIX),
                dtype=float,
            )
            dt = float(cfg.get("dt", 0.1))
            return 9, {"payoff_matrix": payoff.tolist(), "dt": dt}, "replicador: EGT mode active"

        # CfC fast path — evita llamada LLM cuando hay modelo entrenado y confianza alta
        if CFC_AVAILABLE and len(hist) >= 6:
            opinion_window = [h["opinion"] for h in hist[-6:]]
            rid, source, conf = _cfc.select_regime(
                history=opinion_window, state=est
            )
            if source == "cfc":
                p = _validar_params(NOMBRES_REGLAS[rid], {})
                return rid, p, f"cfc (conf={conf:.2f})"

        ventana = hist[-cfg["ventana_historial_llm"]:]
        dec     = llamar_llm(est, escenario, ventana, cfg)
        r_id    = dec["regla"]
        p       = _validar_params(NOMBRES_REGLAS[r_id], dec.get("params", {}))
        return r_id, p, dec.get("razon", "")

    regla_actual, params_actuales, razon_actual = _seleccionar(estado, historial)
    if verbose:
        log.info(
            f"t=0 | [{proveedor}] rango={r['min']},{r['max']} "
            f"| {NOMBRES_REGLAS[regla_actual]} | {razon_actual}"
        )

    for paso in range(1, pasos + 1):

        if paso % cada_n_pasos == 0:
            regla_actual, params_actuales, razon_actual = _seleccionar(estado, historial)
            if verbose:
                log.info(
                    f"t={paso:3d} | [{proveedor}] {NOMBRES_REGLAS[regla_actual]:22s} "
                    f"op={estado['opinion']:+.3f} | {razon_actual}"
                )

        # Aplicar regla elegida
        regla_func    = REGLAS[escenario].get(regla_actual, regla_lineal)
        estado_regla  = regla_func(estado, params_actuales, cfg)
        opinion_regla = _clip(estado_regla["opinion"], cfg)

        # Tendencia base + blending
        tendencia_base = 0.92 * estado["opinion"] + 0.08 * estado["propaganda"]
        opinion_blend  = alpha_blend * opinion_regla + (1.0 - alpha_blend) * tendencia_base

        # Efecto de grupos + fuerza estratégica + ruido adaptativo
        ruido_std     = cfg["ruido_base"] + cfg["ruido_desconfianza"] * (1.0 - estado["confianza"])
        opinion_final = _clip(
            opinion_blend
            + calcular_efecto_grupos(estado, cfg)
            + _calcular_fuerza_estrategica(estado, cfg)
            + float(rng.normal(0.0, ruido_std)),
            cfg
        )

        # Construir nuevo estado
        nuevo = copy.deepcopy(estado)
        # Si la regla actualizó pertenencia_grupo (homofilia), persiste
        if "pertenencia_grupo" in estado_regla:
            nuevo["pertenencia_grupo"] = estado_regla["pertenencia_grupo"]
        # Métricas auxiliares de reglas avanzadas
        for k in ("_fraccion_adoptantes", "_sim_grupo_a", "_sim_grupo_b",
                  "_nash_sigma_a", "_nash_sigma_b", "_bayes_uncertainty",
                  "_sir_S", "_sir_I", "_sir_R"):
            if k in estado_regla:
                nuevo[k] = estado_regla[k]

        nuevo["opinion_prev"]  = estado["opinion"]
        nuevo["opinion"]       = opinion_final
        nuevo["_paso"]         = paso
        nuevo["_regla"]        = regla_actual
        nuevo["_regla_nombre"] = NOMBRES_REGLAS[regla_actual]
        nuevo["_razon"]        = razon_actual
        nuevo["_rango"]        = cfg["rango"]

        estado = nuevo
        historial.append(copy.deepcopy(estado))

        # ── EWS: collect opinion, compute CSD metrics ─────────────────
        opinion_history.append(estado["opinion"])
        if len(opinion_history) == HISTORY_BUFFER_SIZE:
            ews_metrics = calculate_ews_metrics(list(opinion_history))
            ews_flags   = check_ews_signals(ews_metrics, cfg.get("ews_thresholds", {}))
            estado["_ews_flags"] = ews_flags
            historial[-1]["ews"] = {
                "metrics": {k: v.tolist() for k, v in ews_metrics.items()},
                "flags":   ews_flags,
            }

        # ── TDA: topological change detection every 5 steps ───────────
        if TDA_AVAILABLE and paso % 5 == 0 and len(opinion_history) >= HISTORY_BUFFER_SIZE:
            mean_opinions = np.array(list(opinion_history), dtype=float)
            tda_change, prev_diagram = detect_topological_change(
                mean_opinions,
                prev_diagram=cfg_runtime.get("prev_tda_diagram"),
                wasserstein_threshold=cfg.get("tda_wasserstein_threshold", 0.3),
            )
            cfg_runtime["prev_tda_diagram"] = prev_diagram
            historial[-1]["tda_change"] = tda_change

    if verbose:
        log.info(
            f"Completo: {pasos} pasos | "
            f"{historial[0]['opinion']:+.3f} → {historial[-1]['opinion']:+.3f} "
            f"(neutro={_neutro(cfg)})"
        )
    return historial


# ============================================================
# SIMULACIÓN MÚLTIPLE
# ============================================================

def simular_multiples(
    estado_inicial: dict,
    escenario: str = "campana",
    pasos: int = 50,
    cada_n_pasos: int = 5,
    config: dict | None = None,
    n_simulaciones: int = 100,
) -> dict:
    """
    Runs N simulations with variations in the initial state to return a distribution.

    Args:
        estado_inicial: Base state for all simulations.
        escenario: Scenario key.
        pasos: Steps per simulation.
        cada_n_pasos: LLM update frequency.
        config: Override config.
        n_simulaciones: Number of runs.

    Returns:
        Statistics dictionary of the final opinion distribution.
    """
    cfg        = {**DEFAULT_CONFIG, **(config or {})}
    r          = _get_rango(cfg)
    ruido_ini  = cfg["ruido_estado_inicial"]
    resultados = np.zeros(n_simulaciones)
    base_seed = cfg.get("seed", None)
    root_rng = np.random.default_rng(base_seed)

    # Keys whose valid range is [0, 1] regardless of the opinion range.
    # Clipping these to the opinion range (e.g. [-1, 1] in bipolar mode) is
    # incorrect: with low values and non-zero noise, they can go negative,
    # which inflates ruido_std beyond its intended maximum and corrupts the
    # noise model for the entire Monte Carlo run.
    _UNIT_INTERVAL_KEYS = {"confianza", "pertenencia_grupo"}

    for i in range(n_simulaciones):
        estado_ruido = {}
        # Per-replica seed for independent but reproducible noise + simular noise
        rep_seed = int(root_rng.integers(0, 2**31 - 1))
        rep_rng = np.random.default_rng(rep_seed)
        for k, v in estado_inicial.items():
            if isinstance(v, float):
                noisy = v + float(rep_rng.normal(0, ruido_ini))
                if k in _UNIT_INTERVAL_KEYS:
                    estado_ruido[k] = float(np.clip(noisy, 0.0, 1.0))
                else:
                    estado_ruido[k] = float(np.clip(noisy, r["min"], r["max"]))
            else:
                estado_ruido[k] = v
        run_cfg = {**(config or {}), "seed": rep_seed}
        hist = simular(estado_ruido, escenario=escenario, pasos=pasos,
                       cada_n_pasos=cada_n_pasos, config=run_cfg, verbose=False)
        resultados[i] = hist[-1]["opinion"]

    neutro = _neutro(cfg)
    p10, p25, p50, p75, p90 = np.percentile(resultados, [10, 25, 50, 75, 90])
    return {
        "media":          float(resultados.mean()),
        "std":            float(resultados.std()),
        "p_sobre_neutro": float((resultados > neutro).mean()),
        "percentiles":    {"p10": float(p10), "p25": float(p25), "p50": float(p50),
                           "p75": float(p75), "p90": float(p90)},
        "escenarios":     {"optimista": float(p90), "mediano": float(p50),
                           "pesimista":  float(p10)},
        "neutro":         neutro,
        "n_simulaciones": n_simulaciones,
        "rango":          cfg["rango"],
    }


# ============================================================
# SIMULACIÓN MÚLTIPLE — PARALELA CON DASK
# ============================================================

def simular_multiples_dask(
    estado_inicial: dict,
    escenario: str = "campana",
    pasos: int = 50,
    cada_n_pasos: int = 5,
    config: dict | None = None,
    n_simulaciones: int = 100,
    seed: int | None = None,
) -> dict:
    """
    Runs N simulations in parallel using Dask delayed computation.
    Falls back to sequential simular_multiples if Dask is unavailable.

    Args:
        estado_inicial: Base state for all simulations.
        escenario: Scenario key.
        pasos: Steps per simulation.
        cada_n_pasos: LLM update frequency.
        config: Override config.
        n_simulaciones: Number of runs.
        seed: Optional RNG seed for reproducibility (default: None = random).

    Returns:
        Same statistics dictionary as simular_multiples, with "parallel" key.
    """
    try:
        from dask import delayed, compute as dask_compute
    except ImportError:
        log.warning("Dask no disponible — usando modo secuencial.")
        return simular_multiples(estado_inicial, escenario, pasos,
                                 cada_n_pasos, config, n_simulaciones)

    cfg       = {**DEFAULT_CONFIG, **(config or {})}
    r         = _get_rango(cfg)
    ruido_ini = cfg["ruido_estado_inicial"]
    rng       = np.random.default_rng(seed)
    noises    = rng.normal(0, ruido_ini, size=(n_simulaciones, len(estado_inicial)))

    @delayed
    def _run_one(noise_row: np.ndarray) -> float:
        keys = list(estado_inicial.keys())
        estado_ruido = {}
        for idx, k in enumerate(keys):
            v = estado_inicial[k]
            if isinstance(v, float):
                estado_ruido[k] = float(np.clip(v + noise_row[idx], r["min"], r["max"]))
            else:
                estado_ruido[k] = v
        hist = simular(estado_ruido, escenario=escenario, pasos=pasos,
                       cada_n_pasos=cada_n_pasos, config=config, verbose=False)
        return hist[-1]["opinion"]

    tasks      = [_run_one(noises[i]) for i in range(n_simulaciones)]
    resultados = np.array(dask_compute(*tasks))

    neutro = _neutro(cfg)
    p10, p25, p50, p75, p90 = np.percentile(resultados, [10, 25, 50, 75, 90])
    return {
        "media":          float(resultados.mean()),
        "std":            float(resultados.std()),
        "p_sobre_neutro": float((resultados > neutro).mean()),
        "percentiles":    {"p10": float(p10), "p25": float(p25), "p50": float(p50),
                           "p75": float(p75), "p90": float(p90)},
        "escenarios":     {"optimista": float(p90), "mediano": float(p50),
                           "pesimista":  float(p10)},
        "neutro":         neutro,
        "n_simulaciones": n_simulaciones,
        "rango":          cfg["rango"],
        "parallel":       True,
    }


# ============================================================
# UTILIDADES
# ============================================================

def resumen_historial(historial: list[dict], config: dict | None = None) -> dict:
    """
    Calculates descriptive statistics for a simulation history.

    Args:
        historial: List of state dictionaries.
        config: Configuration for range/neutral reference.

    Returns:
        Dictionary with mean, std, delta, and dominant regime.
    """
    cfg       = {**DEFAULT_CONFIG, **(config or {})}
    neutro    = _neutro(cfg)
    opiniones = np.array([h["opinion"] for h in historial])
    reglas    = [h["_regla_nombre"] for h in historial if "_regla_nombre" in h]
    return {
        "opinion_inicial":    float(opiniones[0]),
        "opinion_final":      float(opiniones[-1]),
        "delta_total":        float(opiniones[-1] - opiniones[0]),
        "media":              float(opiniones.mean()),
        "desviacion":         float(opiniones.std()),
        "minimo":             float(opiniones.min()),
        "maximo":             float(opiniones.max()),
        "polarizacion_media": float(np.mean(np.abs(opiniones - neutro))),
        "pasos":              len(historial) - 1,
        "regla_dominante":    Counter(reglas).most_common(1)[0][0] if reglas else "—",
        "neutro":             neutro,
        "rango":              cfg.get("rango", "—"),
    }


# ============================================================
# CHECKPOINTING y RECOVERY
# ============================================================

def save_checkpoint(historial: list[dict], filepath: str | Path) -> None:
    """
    Saves simulation history to a JSON checkpoint file for later recovery.

    Only JSON-serializable fields are preserved; non-serializable values
    (numpy arrays, etc.) are converted to Python native types where possible
    or dropped with a warning.

    Args:
        historial: List of state dictionaries from :func:`simular`.
        filepath: Destination path for the checkpoint file.
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    def _make_serializable(obj: Any) -> Any:
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, dict):
            return {k: _make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_make_serializable(v) for v in obj]
        if isinstance(obj, set):
            return sorted(_make_serializable(v) for v in obj)
        if not isinstance(obj, (str, int, float, bool, type(None))):
            log.warning(
                "save_checkpoint: tipo no serializable ignorado: %s=%r",
                type(obj).__name__,
                obj,
            )
            return None
        return obj

    serializable = _make_serializable(historial)
    with filepath.open("w", encoding="utf-8") as fh:
        json.dump({"version": 1, "historial": serializable}, fh, ensure_ascii=False, indent=2)
    log.info(f"Checkpoint guardado: {filepath} ({len(historial)} pasos)")


def load_checkpoint(filepath: str | Path) -> list[dict]:
    """
    Loads a simulation history from a JSON checkpoint file.

    Args:
        filepath: Path to the checkpoint file previously saved by
            :func:`save_checkpoint`.

    Returns:
        List of state dictionaries (historial) that can be passed directly
        to :func:`resumen_historial` or used as the base for continued
        simulation.

    Raises:
        FileNotFoundError: If *filepath* does not exist.
        ValueError: If the file format is unrecognised or corrupted.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Checkpoint no encontrado: {filepath}")
    with filepath.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or "historial" not in data:
        raise ValueError(f"Formato de checkpoint inválido: {filepath}")
    historial = data["historial"]
    if not isinstance(historial, list):
        raise ValueError(f"Campo 'historial' debe ser una lista: {filepath}")
    log.info(f"Checkpoint cargado: {filepath} ({len(historial)} entradas)")
    return historial


# ============================================================
# MÉTRICAS DE GRAFO (NetworkX) — para el Arquitecto Social
# ============================================================

def get_graph_metrics(G: nx.Graph, modo: str = "macro", top_n: int = 5) -> str:
    """
    Calcula centralidad de grado y betweenness sobre un grafo NetworkX
    y devuelve un resumen textual para el Arquitecto Social.

    Args:
        G: Grafo NetworkX (dirigido o no dirigido).
        modo: 'macro' o 'corporativo' — ajusta el vocabulario del resumen.
        top_n: Número de nodos más influyentes a listar.

    Returns:
        String con el resumen de métricas listo para inyectar en el prompt.
    """
    if G is None or G.number_of_nodes() == 0:
        return "Red vacía — no se pudieron calcular métricas de grafo."

    # Centralidad de grado (normalizada)
    degree_cent = nx.degree_centrality(G)
    top_degree = sorted(degree_cent.items(), key=lambda x: x[1], reverse=True)[:top_n]

    # Betweenness centrality (control de flujo de información)
    try:
        between_cent = nx.betweenness_centrality(G, normalized=True)
        top_between = sorted(between_cent.items(), key=lambda x: x[1], reverse=True)[:top_n]
    except Exception:
        top_between = top_degree  # fallback si el grafo es trivial

    label_influencia = "Nodos más influyentes (grado)"
    label_puentes    = "Nodos puente (betweenness)"
    if modo == "corporativo":
        label_influencia = "Empleados/Directivos con más conexiones directas"
        label_puentes    = "Líderes informales que controlan el flujo de información"

    def fmt(items):
        return ", ".join(
            f"{nodo} ({v:.2f})" for nodo, v in items
        )

    resumen = (
        f"Red: {G.number_of_nodes()} nodos, {G.number_of_edges()} conexiones.\n"
        f"{label_influencia}: {fmt(top_degree)}.\n"
        f"{label_puentes}: {fmt(top_between)}."
    )
    return resumen


# ============================================================
# SIMULADOR INTEGRADO (MOTORES DINÁMICOS CONDICIONALES)
# ============================================================

class IntegratedSimulator:
    """Coordinador central de dinámica interna con motores contextuales."""

    def __init__(self, config: dict | None = None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.n_agents = int(self.config["n_agents"])
        self.n_ticks = int(self.config["n_ticks"])
        self.dt = float(self.config.get("dt", 0.1))
        self.diffusion_sigma = float(self.config.get("diffusion_sigma", 0.05))
        self.rng = np.random.default_rng(self.config.get("seed"))

        self.massive_engine = MassiveEngine(self.config)
        self.multilayer_engine = MultilayerEngine(
            N=self.n_agents,
            dt=self.dt,
            coupling=float(self.config.get("coupling", 0.3)),
            layer_config=self.config.get("layers"),
            seed=int(self.config.get("seed", 42)),
        )

        self.enable_levy_jumps = bool(self.config.get("enable_levy_jumps", False))
        self.levy_lambda = float(self.config.get("levy_lambda", 0.01))
        self.alpha_stable = float(self.config.get("alpha_stable", 1.5))
        self.jump_magnitude_scale = float(self.config.get("jump_magnitude_scale", 0.5))

        self.enable_dynamic_topology = bool(self.config.get("enable_dynamic_topology", False))
        self.topology_update_freq = max(1, int(self.config.get("topology_update_freq", 10)))
        self.topology_intensity = float(self.config.get("topology_intensity", 0.05))

        self.butterfly_interval = max(1, int(self.config.get("butterfly_interval", 100)))
        self.butterfly_threshold = float(self.config.get("butterfly_threshold", 0.5))

        self.tick_counter = 0
        self.lyapunov_history: list[float] = []
        self.topology_history: list[dict[str, Any]] = []
        self.opinion_history: list[float] = []
        self._prev_opinions = self.massive_engine.agents[:, 0].copy()

    def _build_runtime_context(self) -> dict[str, Any]:
        return {
            "tick": self.tick_counter,
            "polarization": self.calculate_polarization(),
            "viral_activity": self.calculate_viral_activity(),
            "lyapunov": self.lyapunov_history[-1] if self.lyapunov_history else 0.0,
        }

    def _emit_runtime_context(self) -> None:
        context = self._build_runtime_context()
        for hook_name in ("router_feedback_hook", "social_architect_hook"):
            hook = self.config.get(hook_name)
            if callable(hook):
                try:
                    hook(context)
                except Exception as exc:  # noqa: BLE001
                    log.warning(
                        "[IntegratedSimulator] Hook '%s' failed at tick=%s: %s | payload=%s",
                        hook_name,
                        self.tick_counter,
                        exc,
                        context,
                    )

    def select_drift_vector(self) -> np.ndarray:
        callback = self.config.get("drift_selector")
        if callable(callback):
            drift = callback(self._build_runtime_context())
            arr = np.asarray(drift, dtype=np.float64)
            if arr.shape == (self.n_agents,):
                return arr

        if (
            CFC_AVAILABLE
            and len(self.opinion_history) >= _INTEGRATED_CFC_HISTORY_MIN
            and _cfc is not None
        ):
            rid, source, _ = _cfc.select_regime(
                history=self.opinion_history[-_INTEGRATED_CFC_HISTORY_MIN:],
                state={
                    "opinion": float(np.mean(self.massive_engine.agents[:, 0])),
                    "propaganda": float(np.mean(self.massive_engine.agents[:, 1])),
                    "confianza": 0.5,
                    "opinion_grupo_a": float(np.percentile(self.massive_engine.agents[:, 0], 75)),
                    "opinion_grupo_b": float(np.percentile(self.massive_engine.agents[:, 0], 25)),
                },
            )
            if source == "cfc":
                scale = _INTEGRATED_CFC_DRIFT_SCALE * (1 + rid)
                return self.rng.normal(0.0, scale, self.n_agents)

        return self.rng.normal(0.0, _INTEGRATED_DRIFT_FALLBACK_STD, self.n_agents)

    def _sample_levy_jump_magnitudes(self, n_jumps: int) -> np.ndarray:
        if n_jumps <= 0:
            return np.zeros(0, dtype=np.float64)
        alpha = float(np.clip(self.alpha_stable, 1.0, 2.0))
        if abs(alpha - 1.0) < 1e-8:
            jumps = self.rng.standard_cauchy(n_jumps)
        else:
            jumps = stats.levy_stable.rvs(
                alpha,
                0.0,
                size=n_jumps,
                random_state=self.rng,
            )
        jumps = np.asarray(jumps, dtype=np.float64)
        jumps = np.clip(jumps, -_INTEGRATED_LEVY_CLIP, _INTEGRATED_LEVY_CLIP)
        return jumps * self.jump_magnitude_scale

    def update_agents_with_langevin(self, drift_vector: np.ndarray) -> None:
        agents = self.massive_engine.agents
        n_agents = agents.shape[0]
        dW = self.rng.normal(0.0, np.sqrt(self.dt), n_agents)
        dx_jump = np.zeros(n_agents, dtype=np.float64)
        if self.enable_levy_jumps:
            jump_occurred = self.rng.poisson(self.levy_lambda, n_agents) > 0
            n_jumps = int(np.sum(jump_occurred))
            if n_jumps > 0:
                dx_jump[jump_occurred] = self._sample_levy_jump_magnitudes(n_jumps)

        langevin_opinion_update_inplace(
            agents,
            drift_vector,
            dW,
            dx_jump,
            self.dt,
            self.diffusion_sigma,
            -1.0,
            1.0,
        )
        self.massive_engine.agents = agents

    def apply_levy_jumps_to_agents(self) -> None:
        """No-op por compatibilidad: Lévy se integra en update_agents_with_langevin."""
        return None

    def calculate_polarization(self) -> float:
        opinions = self.massive_engine.agents[:, 0]
        return float(np.clip(np.std(opinions) * 2.0, 0.0, 1.0))

    def calculate_viral_activity(self) -> float:
        opinions = self.massive_engine.agents[:, 0]
        delta = np.abs(opinions - self._prev_opinions)
        return float(np.clip(np.mean(delta) * 10.0, 0.0, 1.0))

    def update_network_topology(self) -> None:
        polarization_current = self.calculate_polarization()
        mode = (
            "censorship"
            if polarization_current > _INTEGRATED_CENSORSHIP_POLARIZATION_THRESHOLD
            else "viral_hub"
        )
        intensity = float(
            np.clip(
                max(
                    self.topology_intensity,
                    abs(polarization_current - _INTEGRATED_TOPOLOGY_POLARIZATION_CENTER),
                ),
                _INTEGRATED_TOPOLOGY_INTENSITY_MIN,
                _INTEGRATED_TOPOLOGY_INTENSITY_MAX,
            )
        )
        for layer_name in self.multilayer_engine.layers.keys():
            if hasattr(self.multilayer_engine, 'dynamic_rewiring'):
                self.multilayer_engine.dynamic_rewiring(
                    layer_name=layer_name,
                    mode=mode,
                    intensity=intensity,
                )
        self.topology_history.append(
            {
                "tick": self.tick_counter,
                "mode": mode,
                "intensity": intensity,
                "polarization": polarization_current,
            }
        )

    def run_butterfly_diagnostic(self) -> float:
        snapshot = {
            "agents": self.massive_engine.agents.copy(),
            "graphs": getattr(self.multilayer_engine, "graphs", self.multilayer_engine.layers),
            "n_ticks_left": max(self.n_ticks - self.tick_counter, 1),
        }
        result = run_butterfly_diagnostic_core(snapshot)
        return float(result.get("divergence_score", 0.0))

    def step(self) -> dict[str, Any]:
        drift_vector = self.select_drift_vector()
        self.update_agents_with_langevin(drift_vector)
        self.multilayer_engine.update_opinions(self.massive_engine.agents.copy())

        if self.enable_dynamic_topology and self.tick_counter % self.topology_update_freq == 0:
            self.update_network_topology()

        if self.tick_counter > 0 and self.tick_counter % self.butterfly_interval == 0:
            lyapunov_score = self.run_butterfly_diagnostic()
            self.lyapunov_history.append(lyapunov_score)
            if lyapunov_score > self.butterfly_threshold:
                log.warning(
                    "⚠️ ALERTA: transición caótica detectada (Lyapunov=%.4f)",
                    lyapunov_score,
                )

        self.opinion_history.append(float(np.mean(self.massive_engine.agents[:, 0])))
        self._emit_runtime_context()
        self._prev_opinions = self.massive_engine.agents[:, 0].copy()
        self.tick_counter += 1

        return {
            "tick": self.tick_counter,
            "mean_opinion": float(np.mean(self.massive_engine.agents[:, 0])),
            "polarization": self.calculate_polarization(),
            "viral_activity": self.calculate_viral_activity(),
            "lyapunov": self.lyapunov_history[-1] if self.lyapunov_history else 0.0,
        }

    def run(self, steps: int | None = None) -> list[dict[str, Any]]:
        total = self.n_ticks if steps is None else int(steps)
        history: list[dict[str, Any]] = []
        for _ in range(max(0, total)):
            history.append(self.step())
        return history


# ============================================================
# MODO ARQUITECTO SOCIAL (EJECUCIÓN POR ITINERARIO)
# ============================================================

def run_with_schedule(
    estado_inicial: dict,
    strategy_schedule: dict,
    escenario: str = "campana",
    config: dict | None = None,
    verbose: bool = True,
) -> list[dict]:
    """
    Ejecuta la simulación siguiendo estrictamente un schedule de intervenciones
    generado por el LLM en Modo Inverso.
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    r = _get_rango(cfg)
    alpha_blend = cfg["alpha_blend"]
    sched_rng = np.random.default_rng(cfg.get("seed"))
    
    estado = estado_inicial.copy()
    estado.setdefault("opinion_prev", estado["opinion"])
    estado.setdefault("confianza", 0.5)
    estado.setdefault("opinion_grupo_a", min(estado["opinion"] + 0.2 * _amplitud(cfg), r["max"]))
    estado.setdefault("opinion_grupo_b", max(estado["opinion"] - 0.2 * _amplitud(cfg), r["min"]))
    estado.setdefault("pertenencia_grupo", 0.6)

    historial: list[dict] = [estado.copy()]
    
    name_to_id = {v: k for k, v in NOMBRES_REGLAS.items()}
    
    paso_actual = 1
    for fase in strategy_schedule.get("interventions", []):
        start = max(paso_actual, fase["time_start"])
        end = fase["time_end"]
        # Parsing fallback for manual LLM responses
        regla_nombre = fase["model_name"].lower().strip()
        if "degroot" in regla_nombre: regla_nombre = "memoria"
        if "granovetter" in regla_nombre: regla_nombre = "umbral_heterogeneo"
        if "hegselmann" in regla_nombre or "hk" in regla_nombre: regla_nombre = "hk"
        
        regla_id = name_to_id.get(regla_nombre, 0) # Fallback a lineal(0)
        params = _validar_params(NOMBRES_REGLAS.get(regla_id, "lineal"), fase.get("parameters", {}))
        razon = fase.get("fase_rationale", "")
        
        # Extraer target_nodes desde parameters o desde la fase directamente
        target_nodes = params.pop("target_nodes", None) or fase.get("target_nodes", None)

        for paso in range(start, end + 1):
            if verbose and paso == start:
                log.info(
                    f"Fase Inversa [{start}-{end}]: {NOMBRES_REGLAS[regla_id]} | {razon}"
                    + (f" | target_nodes={target_nodes}" if target_nodes else "")
                )

            regla_func = REGLAS[escenario].get(regla_id, regla_lineal)
            estado_regla = regla_func(estado, params, cfg)
            opinion_regla = _clip(estado_regla["opinion"], cfg)

            # ── Aplicar boosting de target_nodes (modo corporativo) ──────
            # Si se especifican nodos líderes, su „voto" fuerza la propaganda
            # hacia el centro de sus posiciones, aumentando la convergencia.
            if target_nodes:
                proporcion_target = min(1.0, len(target_nodes) / max(1, cfg.get("_n_nodos", 20)))
                # La opinión de los nodos target jala la opinión global con extra peso
                opinion_regla = _clip(
                    opinion_regla + 0.12 * proporcion_target * (
                        estado.get("propaganda", 0.5) - opinion_regla
                    ),
                    cfg,
                )

            tendencia_base = 0.92 * estado["opinion"] + 0.08 * estado["propaganda"]
            opinion_blend = alpha_blend * opinion_regla + (1.0 - alpha_blend) * tendencia_base
            ruido_std = cfg["ruido_base"] + cfg["ruido_desconfianza"] * (1.0 - estado["confianza"])

            opinion_final = _clip(
                opinion_blend
                + calcular_efecto_grupos(estado, cfg)
                + _calcular_fuerza_estrategica(estado, cfg)
                + float(sched_rng.normal(0.0, ruido_std)),
                cfg,
            )

            nuevo = copy.deepcopy(estado)
            if "pertenencia_grupo" in estado_regla:
                nuevo["pertenencia_grupo"] = estado_regla["pertenencia_grupo"]
            for k in ("_fraccion_adoptantes", "_sim_grupo_a", "_sim_grupo_b",
                      "_nash_sigma_a", "_nash_sigma_b", "_bayes_uncertainty",
                      "_sir_S", "_sir_I", "_sir_R"):
                if k in estado_regla:
                    nuevo[k] = estado_regla[k]

            nuevo["opinion_prev"]   = estado["opinion"]
            nuevo["opinion"]        = opinion_final
            nuevo["_paso"]          = paso
            nuevo["_regla"]         = regla_id
            nuevo["_regla_nombre"]  = NOMBRES_REGLAS.get(regla_id, regla_nombre)
            nuevo["_razon"]         = razon
            nuevo["_rango"]         = cfg["rango"]
            nuevo["_target_nodes"]  = target_nodes  # trazabilidad

            estado = nuevo
            historial.append(estado.copy())
            paso_actual = paso + 1

    return historial


# ============================================================
# EJECUCIÓN DIRECTA
# ============================================================
if __name__ == "__main__":
    for nombre_rango in RANGOS_DISPONIBLES:
        r = RANGOS_DISPONIBLES[nombre_rango]
        print(f"\n{'='*65}")
        print(f"Rango: {nombre_rango}")
        print(f"{'='*65}")

        estado = {
            "opinion":          r["defaults"]["opinion_inicial"],
            "propaganda":       r["defaults"]["propaganda"],
            "confianza":        r["defaults"]["confianza"],
            "opinion_grupo_a":  r["defaults"]["opinion_grupo_a"],
            "opinion_grupo_b":  r["defaults"]["opinion_grupo_b"],
            "pertenencia_grupo": 0.65,
            "narrativa_b":      -0.3 if r["min"] < 0 else 0.3,
        }

        config = {
            "rango":              nombre_rango,
            "sesgo_confirmacion": 0.3,
            "hk_epsilon":         0.3,
        }
        hist  = simular(estado, pasos=20, cada_n_pasos=5, config=config, verbose=True)
        stats = resumen_historial(hist, config)

        print(f"\n  opinion: {stats['opinion_inicial']:+.3f} → {stats['opinion_final']:+.3f}")
        print(f"  delta_total:        {stats['delta_total']:+.3f}")
        print(f"  polarizacion_media: {stats['polarizacion_media']:.3f}")
        print(f"  regla_dominante:    {stats['regla_dominante']}")
        print(f"  neutro:             {stats['neutro']}")
