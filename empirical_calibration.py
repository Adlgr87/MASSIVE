"""
empirical_calibration.py — Índices de Calibración Empírica para MASSIVE
Consolida investigaciones sobre dinámicas de red, efectos temporales y teoría
de juegos, normalizados al espectro [-1.0, 1.0].

Referencias:
  I1 — Cartografía de la Opinión Pública: Un Marco Empírico Normalizado.
  I2 — BeyondSight-Data-Architect v2 - Gap Search.
  I3 — Cartografía Empírica Avanzada para BeyondSight v2.
"""

import datetime
import json

# ============================================================
# DICCIONARIO MAESTRO EMPÍRICO
# Metadata completa, varianza cultural y modificadores demográficos.
# Todos los valores normalizados al espectro [-1.0, 1.0].
# ============================================================

BEYONDSIGHT_EMPIRICAL_MASTER: dict = {
    "meta": {
        "version": "1.0.0",
        "total_params": 43,
        "coverage_pct": 53.8,
        "generated": datetime.date.today().isoformat(),
        "conflicts_resolved": 1,
        "high_confidence_pct": 37.2,
        "cultural_blocks": [
            "latino", "anglosaxon", "east_asian",
            "south_asian", "middle_eastern", "nordic",
        ],
        "notes": (
            "Conflicto resuelto: Umbral de Inflexión (P026) — datos empíricos I1 "
            "prevalecen sobre Granovetter por rigor metodológico."
        ),
    },

    # ── Dinámica de redes ──────────────────────────────────────────────────────
    "network_dynamics": {
        "DERIVA_ALGORITMICA": {
            "id": "P022",
            "label": "Aceleración por Deriva Algorítmica",
            "value": 0.45,
            "digital_weight": 1.0,
            "cultural_variance": {
                "latin": 0.40,
                "anglosaxon": 0.50,
                "east_asian": 0.65,
            },
            "source": ["Bonchi et al., 2024-2025"],
            "notes": "Fuerza de arrastre exógena de sistemas de recomendación (ADS).",
        },
        "INFLUENCIA_PARASOCIAL": {
            "id": "P023",
            "label": "Asimetría de Influencia Parasocial",
            "value": 0.35,
            "digital_weight": 0.85,
            "cultural_variance": {
                "latin": 0.50,
                "anglosaxon": 0.40,
            },
            "source": ["Schramm et al., 2024"],
            "notes": "Preeminencia de influencers sobre expertos en autoridad epistémica.",
        },
        "UMBRAL_INFLEXION": {
            "id": "P026",
            "label": "Umbral de Inflexión de Cascada",
            "value": -0.50,
            "digital_weight": 0.90,
            "cultural_variance": {
                "latin": -0.45,
                "anglosaxon": -0.55,
                "east_asian": -0.60,
            },
            "source": ["I1", "I3"],
            "conflict_resolution": "Datos empíricos I1 prevalecen sobre Granovetter.",
            "notes": "Punto de inflexión donde la cascada social se vuelve autosuficiente.",
        },
    },

    # ── Efectos temporales ─────────────────────────────────────────────────────
    "temporal": {
        "ASIMETRIA_NEG_POS": {
            "id": "P032",
            "label": "Asimetría Negativo/Positivo",
            "value": 0.00,
            "normalization": {
                "note": "Valor neutro activo — asimetría nula en condiciones basales.",
            },
            "source": ["I2"],
            "notes": "Diferencia en velocidad de propagación entre contenido negativo y positivo.",
        },
        "MEDIA_VIDA_DIGITAL": {
            "id": "P033",
            "label": "Media-Vida de Atención Digital",
            "value": 0.00,
            "normalization": {
                "original_scale": "horas",
                "original_value": 36.0,
                "original_max": 168.0,
                "note": "Decaimiento estándar ~36h → 0.0 en escala logarítmica normalizada.",
            },
            "source": ["I2"],
            "notes": "Velocidad de decaimiento de la atención en narrativas virales.",
        },
        "PUNTO_SATURACION": {
            "id": "P035",
            "label": "Punto de Saturación de Mensaje",
            "value": 0.00,
            "normalization": {
                "note": "Umbral de fatiga de mensaje — efecto boomerang a partir de este punto.",
            },
            "source": ["I2"],
            "notes": "Sobreexposición a un mensaje dispara rechazo activo (efecto boomerang).",
        },
        "ELASTICIDAD_CONFIANZA": {
            "id": "P037",
            "label": "Elasticidad de Confianza Institucional",
            "value": -0.25,
            "digital_weight": 0.70,
            "cultural_variance": {
                "latin": -0.30,
                "anglosaxon": -0.20,
                "nordic": -0.10,
            },
            "source": ["I2"],
            "notes": "Efecto de la inflación sostenida en la confianza institucional.",
        },
        "SILENCIO_ESTRATEGICO": {
            "id": "P044",
            "label": "Costo del Silencio Estratégico",
            "value": 0.30,
            "digital_weight": 0.75,
            "cultural_variance": {
                "latin": 0.25,
                "anglosaxon": 0.35,
                "east_asian": 0.20,
            },
            "source": ["I2", "I3"],
            "notes": (
                "Diferenciado de autocensura pasiva. Representa el costo activo de "
                "abstenerse deliberadamente de expresar una opinión en contexto público."
            ),
        },
    },

    # ── Teoría de juegos ───────────────────────────────────────────────────────
    "game_theory": {
        "UTILIDAD_COORDINACION": {
            "label": "Utilidad de Unirse al Consenso",
            "value": 0.602,
            "notes": "Payoff de coordinación — recompensa por unirse a la narrativa dominante.",
        },
        "COSTO_DISIDENCIA": {
            "label": "Costo de la Disidencia",
            "value": -0.50,
            "notes": "Costo social y epistémico de mantener una posición minoritaria.",
        },
        "ANIMOSIDAD_OUTGROUP": {
            "label": "Animosidad Hacia el Exogrupo",
            "value": -0.45,
            "notes": "Prosocialidad invertida — fuerza repulsora hacia el grupo contrario.",
        },
    },
}


# ============================================================
# PARÁMETROS DE EJECUCIÓN (RUNTIME)
# Valores directos para alimentar el motor de simulación.
# Todos normalizados al espectro [-1.0, 1.0].
# ============================================================

BEYONDSIGHT_RUNTIME_PARAMS: dict = {
    # Caos/Irracionalidad — modula backfire vs. efecto de inoculación
    "temperature": 0.45,
    # Peso de la red vs. convicción propia (λ — social influence lambda)
    "social_influence_lambda": 0.58,
    # Fuerza de la narrativa dominante (profundidad del atractor)
    "attractor_depth": 0.75,
    # Animosidad out-group — prosocialidad invertida (repulsor)
    "repeller_strength": -0.45,
    # Utilidad de unirse al consenso (payoff cooperación-cooperación)
    "payoff_coordination": 0.602,
    # Costo de la disidencia (payoff defección-defección)
    "payoff_defection": -0.50,
    # Media-vida de influencia narrativa (0.0 = decaimiento estándar ~36h)
    "narrative_decay_rate": 0.00,
    # Punto de rechazo por sobreexposición (0.0 = umbral de saturación neutro)
    "saturation_threshold": 0.00,
    # Perfil cultural activo
    "cultural_profile": "mixed",
    # Flags de validación de síntesis (vacío = todos OK)
    "validation_flags": [],
}


# ============================================================
# FUNCIÓN DE APLICACIÓN DE PERFIL EMPÍRICO
# Traduce los parámetros de runtime al formato de configuración
# del simulador MASSIVE (simulator.py / energy_runner.py).
# ============================================================

def apply_empirical_profile(cfg: dict) -> dict:
    """
    Merges empirically calibrated values into a MASSIVE simulator config.

    Maps BEYONDSIGHT_RUNTIME_PARAMS fields to the keys expected by simulator.py
    and energy_runner.py, without overwriting user-set LLM or range options.

    The mapping is:
      social_influence_lambda → efecto_vecinos_peso
      temperature             → ruido_base   (scaled ×0.20 to match [0.01, 0.20])
      payoff_coordination     → strategic.payoff_matrix.cc
      payoff_defection        → strategic.payoff_matrix.dd

    Args:
        cfg: Existing simulator configuration dict (may be empty).

    Returns:
        New dict with empirical values merged in. The original dict is not mutated.
    """
    merged = dict(cfg)

    rp = BEYONDSIGHT_RUNTIME_PARAMS

    # Social influence weight
    merged["efecto_vecinos_peso"] = float(rp["social_influence_lambda"])

    # Noise / chaos level — runtime temperature is in [-1,1] normalised scale;
    # simulator ruido_base operates in [0.01, 0.20].  We scale proportionally.
    merged["ruido_base"] = float(max(0.01, min(0.20, rp["temperature"] * 0.20)))

    # Narrative decay maps to ruido_desconfianza only when non-zero
    if rp["narrative_decay_rate"] != 0.0:
        merged["ruido_desconfianza"] = float(
            max(0.01, min(0.30, abs(rp["narrative_decay_rate"]) * 0.30))
        )

    # Confirmation bias — asymmetric neg/pos response
    asim = BEYONDSIGHT_EMPIRICAL_MASTER["temporal"]["ASIMETRIA_NEG_POS"]["value"]
    if asim != 0.0:
        merged["sesgo_confirmacion"] = float(max(0.0, min(1.0, abs(asim))))

    # Strategic layer — payoff matrix from empirical game-theory values
    strategic = dict(merged.get("strategic", {}))
    strategic.setdefault("enabled", False)
    payoff = dict(strategic.get("payoff_matrix", {"cc": 1.0, "cd": -1.0, "dc": 1.0, "dd": -1.0}))
    payoff["cc"] = float(rp["payoff_coordination"])   # consensus reward
    payoff["dd"] = float(rp["payoff_defection"])       # mutual defection cost
    strategic["payoff_matrix"] = payoff
    merged["strategic"] = strategic

    # Tag the config with the empirical profile version for traceability
    merged["_empirical_profile"] = BEYONDSIGHT_EMPIRICAL_MASTER["meta"]["version"]

    return merged


# ============================================================
# EXPORTACIÓN JSON
# ============================================================

def export_to_json(path: str | None = None) -> str:
    """
    Serialises both dictionaries to a JSON string and optionally writes to disk.

    Args:
        path: If provided, the JSON string is written to this file path.

    Returns:
        JSON string representation of the full calibration data.
    """
    payload = {
        "master": BEYONDSIGHT_EMPIRICAL_MASTER,
        "runtime_params": BEYONDSIGHT_RUNTIME_PARAMS,
    }
    # Re-stamp generation date
    payload["master"]["meta"]["generated"] = datetime.date.today().isoformat()

    result = json.dumps(payload, ensure_ascii=False, indent=2)

    if path is not None:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(result)

    return result


# ── Backward-compatible aliases (new preferred names) ─────────────────────────
MASSIVE_EMPIRICAL_MASTER = BEYONDSIGHT_EMPIRICAL_MASTER
MASSIVE_RUNTIME_PARAMS   = BEYONDSIGHT_RUNTIME_PARAMS
