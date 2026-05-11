"""
empirical_calibration.py — Traducción empírica al motor de simulación MASSIVE.

Este módulo toma la base empírica normalizada de ``empirical_config.py`` como
fuente única de verdad y la convierte en parámetros directamente utilizables por
``simulator.py``.  La calibración mantiene la API pública existente, pero evita
escalas inconsistentes entre la carga automática del simulador y el perfil
empírico aplicado manualmente desde la UI.
"""

from __future__ import annotations

import json

from empirical_config import (
    BEYONDSIGHT_EMPIRICAL_MASTER,
    BEYONDSIGHT_RUNTIME_PARAMS,
    get_runtime_params,
)

HK_EPSILON_MIN = 0.20
HK_EPSILON_MAX = 0.35
RUIDO_BASE_MIN = 0.01
RUIDO_BASE_MAX = 0.20
RUIDO_DESCONFIANZA_MIN = 0.04
RUIDO_DESCONFIANZA_MAX = 0.18
EFECTO_VECINOS_MIN = 0.02
EFECTO_VECINOS_MAX = 0.12
ALPHA_BLEND_MIN = 0.55
ALPHA_BLEND_MAX = 0.85
COMPETENCIA_PESO_MIN = 0.25
COMPETENCIA_PESO_MAX = 0.60
HOMOFILIA_TASA_MIN = 0.02
HOMOFILIA_TASA_MAX = 0.12
STRATEGIC_WEIGHT_MIN = 0.18
STRATEGIC_WEIGHT_MAX = 0.32
# Centola et al. (2018) and Everall et al. (2025) place practical social
# tipping points near one quarter of the population, with a common 20–30% band.
TIPPING_POINT_MEAN = 0.25
TIPPING_POINT_STD = 0.05


def _clamp(value: float, lower: float, upper: float) -> float:
    return float(max(lower, min(upper, value)))


def _scale_unit_to_range(value: float, lower: float, upper: float) -> float:
    """
    Projects a normalised [0, 1] empirical intensity into an engine-safe range.

    Args:
        value: Normalised empirical magnitude in [0, 1].
        lower: Lower bound of the simulator-native range.
        upper: Upper bound of the simulator-native range.

    Returns:
        Float rescaled to the inclusive ``[lower, upper]`` interval.
    """
    value = _clamp(value, 0.0, 1.0)
    return float(lower + (upper - lower) * value)


def _profile_value(category: str, param_id: str, cultural_profile: str) -> float:
    entry = BEYONDSIGHT_EMPIRICAL_MASTER[category][param_id]
    if cultural_profile != "mixed":
        variance = entry.get("cultural_variance", {})
        if cultural_profile in variance:
            return float(variance[cultural_profile])
    return float(entry["value"])


def build_empirical_engine_config(cultural_profile: str = "mixed") -> dict:
    """
    Builds simulator-facing defaults from the normalised empirical runtime base.

    Relevant parameters are translated only when they already exist in the
    simulator, avoiding speculative integrations.  All returned values are in the
    native ranges expected by ``simulator.py``.

    Args:
        cultural_profile: Cultural block used to apply variance modifiers before
            translating the empirical values to simulator-native defaults.

    Returns:
        Dict with simulator-facing defaults such as noise, social influence,
        bounded confidence, threshold parameters and strategic payoffs.
    """
    runtime = get_runtime_params(cultural_profile)

    homophily = _clamp(
        _profile_value("network_dynamics", "HOMOFILIA_RED", cultural_profile),
        0.0,
        1.0,
    )
    confirmation_bias = _clamp(
        _profile_value("individual_psychology", "SESGO_CONFIRMACION", cultural_profile),
        0.0,
        1.0,
    )
    viral_amplification = _clamp(
        _profile_value("network_dynamics", "AMPLIFICACION_VIRAL", cultural_profile),
        0.0,
        1.0,
    )

    return {
        "ruido_base": round(
            _scale_unit_to_range(runtime["temperature"], RUIDO_BASE_MIN, RUIDO_BASE_MAX),
            4,
        ),
        "ruido_desconfianza": round(
            _scale_unit_to_range(
                runtime["narrative_decay_rate"],
                RUIDO_DESCONFIANZA_MIN,
                RUIDO_DESCONFIANZA_MAX,
            ),
            4,
        ),
        "efecto_vecinos_peso": round(
            _scale_unit_to_range(
                runtime["social_influence_lambda"],
                EFECTO_VECINOS_MIN,
                EFECTO_VECINOS_MAX,
            ),
            4,
        ),
        "alpha_blend": round(
            _scale_unit_to_range(
                runtime["attractor_depth"],
                ALPHA_BLEND_MIN,
                ALPHA_BLEND_MAX,
            ),
            4,
        ),
        "sesgo_confirmacion": round(confirmation_bias, 4),
        # Online homophily lowers the bounded-confidence radius instead of
        # increasing it, keeping epsilon in the empirically plausible
        # Hegselmann-Krause / bounded-confidence ~0.20–0.35 band.
        "hk_epsilon": round(
            HK_EPSILON_MIN + (HK_EPSILON_MAX - HK_EPSILON_MIN) * (1.0 - homophily),
            4,
        ),
        "competencia_peso": round(
            _scale_unit_to_range(
                viral_amplification,
                COMPETENCIA_PESO_MIN,
                COMPETENCIA_PESO_MAX,
            ),
            4,
        ),
        "umbral_media": TIPPING_POINT_MEAN,
        "umbral_std": TIPPING_POINT_STD,
        "homofilia_tasa": round(
            _scale_unit_to_range(
                homophily,
                HOMOFILIA_TASA_MIN,
                HOMOFILIA_TASA_MAX,
            ),
            4,
        ),
        "cultural_profile": cultural_profile,
        "validation_flags": list(runtime["validation_flags"]),
        "strategic": {
            "enabled": False,
            "payoff_matrix": {
                "cc": float(runtime["payoff_coordination"]),
                "dd": float(runtime["payoff_defection"]),
            },
            "strategic_weight": round(
                _scale_unit_to_range(
                    abs(runtime["repeller_strength"]),
                    STRATEGIC_WEIGHT_MIN,
                    STRATEGIC_WEIGHT_MAX,
                ),
                4,
            ),
        },
    }


def apply_empirical_profile(cfg: dict) -> dict:
    """
    Merges empirically calibrated values into a MASSIVE simulator config.

    Args:
        cfg: Existing simulator configuration dict (may be empty).

    Returns:
        New dict with empirical engine values merged in. The original dict is not
        mutated.
    """
    merged = dict(cfg)
    cultural_profile = str(merged.get("cultural_profile", "mixed"))
    engine_cfg = build_empirical_engine_config(cultural_profile)

    for key in (
        "efecto_vecinos_peso",
        "ruido_base",
        "ruido_desconfianza",
        "alpha_blend",
        "sesgo_confirmacion",
        "hk_epsilon",
        "competencia_peso",
        "umbral_media",
        "umbral_std",
        "homofilia_tasa",
    ):
        merged[key] = engine_cfg[key]

    strategic = dict(merged.get("strategic", {}))
    strategic.setdefault("enabled", False)
    strategic.setdefault("strategic_weight", engine_cfg["strategic"]["strategic_weight"])
    payoff = dict(
        strategic.get(
            "payoff_matrix",
            {"cc": 1.0, "cd": -1.0, "dc": 1.0, "dd": -1.0},
        )
    )
    payoff["cc"] = engine_cfg["strategic"]["payoff_matrix"]["cc"]
    payoff["dd"] = engine_cfg["strategic"]["payoff_matrix"]["dd"]
    strategic["payoff_matrix"] = payoff
    merged["strategic"] = strategic

    merged["_empirical_profile"] = BEYONDSIGHT_EMPIRICAL_MASTER["meta"]["version"]
    return merged


def export_to_json(path: str | None = None) -> str:
    """
    Serialises both dictionaries to a JSON string and optionally writes to disk.

    Args:
        path: Optional file path where the serialised payload should be written.

    Returns:
        JSON string containing the empirical master data, runtime parameters and
        derived engine defaults.
    """
    payload = {
        "master": BEYONDSIGHT_EMPIRICAL_MASTER,
        "runtime_params": BEYONDSIGHT_RUNTIME_PARAMS,
        "engine_defaults": build_empirical_engine_config(),
    }
    result = json.dumps(payload, ensure_ascii=False, indent=2)

    if path is not None:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(result)

    return result
