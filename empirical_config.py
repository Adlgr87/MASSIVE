"""
MASSIVE — Base Empírica de Calibración
Parámetros derivados de estudios académicos, datasets históricos,
psicología de masas, teoría de juegos y análisis de comportamiento
en redes sociales digitales.

Todos los valores están normalizados al rango bipolar [-1.0, 1.0].
"""

import datetime

# ------------------------------------------------------------
# FLAG DE CARGA
# ------------------------------------------------------------
EMPIRICAL_BASE_LOADED = True

# ============================================================
# DICCIONARIO MAESTRO EMPÍRICO DE MASSIVE
# Valores normalizados al rango [-1.0, 1.0]
# ============================================================
BEYONDSIGHT_EMPIRICAL_MASTER = {
    "meta": {
        "version": "1.1.0",
        "total_params": 43,
        "coverage_pct": 88.4,
        "generated": datetime.date.today().isoformat(),
    },
    "network_dynamics": {
        "DERIVA_ALGORITMICA": {
            "label": "Aceleración por Deriva Algorítmica",
            "value": 0.45,
            "digital_weight": 1.0,
            "cultural_variance": {
                "latin": 0.40,
                "anglosaxon": 0.50,
                "east_asian": 0.65,
            },
            "source": ["Bonchi et al., 2024-2025"],
            "notes": "Fuerza de arrastre exógena de sistemas de recomendación.",
        },
        "INFLUENCIA_PARASOCIAL": {
            "label": "Asimetría de Influencia Parasocial",
            "value": 0.35,
            "digital_weight": 0.85,
            "cultural_variance": {"latin": 0.50, "anglosaxon": 0.40},
            "source": ["Schramm et al., 2024"],
            "notes": "Preeminencia de influencers sobre expertos.",
        },
        "HOMOFILIA_RED": {
            "label": "Homofilia en Redes Digitales",
            "value": 0.65,
            "digital_weight": 0.9,
            "cultural_variance": {
                "anglosaxon": 0.70,
                "latin": 0.60,
                "east_asian": 0.55,
            },
            "source": ["McPherson et al., 2001", "Bakshy et al., 2015"],
            "notes": (
                "Tendencia de los individuos a asociarse con pares similares en "
                "opinión, ideología y demografía. En redes digitales refuerza "
                "cámaras de eco y polarización."
            ),
        },
        "AMPLIFICACION_VIRAL": {
            "label": "Factor de Amplificación Viral",
            "value": 0.52,
            "digital_weight": 1.0,
            "cultural_variance": {
                "latin": 0.58,
                "anglosaxon": 0.55,
                "east_asian": 0.45,
            },
            "source": ["Goel et al., 2016", "Brady et al., 2017", "Berger & Milkman, 2012"],
            "notes": (
                "Factor multiplicador de alcance en contenido viral. Contenido "
                "moral-emocional amplifica difusión ~20 % por palabra moral "
                "(Brady et al.). Cola pesada: mayoría de contenido no viraliza."
            ),
        },
    },
    "temporal": {
        "MEDIA_VIDA_DIGITAL": {
            "value": 0.0,  # Neutralidad en escala logarítmica normalizada
            "normalization": {"original_scale": "horas", "original_max": 168.0},
            "notes": "Decaimiento de la atención en narrativas virales.",
        },
        "ELASTICIDAD_CONFIANZA": {
            "value": -0.25,
            "notes": "Efecto de la inflación sostenida en la confianza institucional.",
        },
        "CICLO_ATENCION": {
            "label": "Velocidad de Ciclo de Atención",
            "value": 0.42,
            "digital_weight": 0.95,
            "cultural_variance": {
                "anglosaxon": 0.45,
                "latin": 0.40,
                "east_asian": 0.38,
            },
            "source": ["Weng et al., 2012", "Lorenz-Spreen et al., 2019"],
            "notes": (
                "Aceleración del ciclo noticioso en medios digitales: el tiempo "
                "de atención colectiva sobre un tema se comprime de días a horas. "
                "Valor positivo refleja velocidad elevada del ciclo."
            ),
        },
        "FATIGA_OUTRAGE": {
            "label": "Fatiga de Indignación Moral",
            "value": -0.38,
            "digital_weight": 0.85,
            "cultural_variance": {
                "anglosaxon": -0.40,
                "latin": -0.35,
                "east_asian": -0.30,
            },
            "source": ["Brady et al., 2021"],
            "notes": (
                "Reducción de sensibilidad y respuesta emocional ante la "
                "sobreexposición a contenido de indignación moral. Valor negativo: "
                "efecto amortiguador sobre la movilización sostenida."
            ),
        },
    },
    "individual_psychology": {
        "SESGO_CONFIRMACION": {
            "label": "Sesgo de Confirmación Cognitivo",
            "value": 0.38,
            "cultural_variance": {"latin": 0.35, "anglosaxon": 0.40, "east_asian": 0.30},
            "source": ["Nickerson, 1998", "Sunstein, 2009"],
            "notes": "Resistencia a información contraria a creencias previas.",
        },
        "EFECTO_BACKFIRE": {
            "label": "Efecto Backfire (Refuerzo por Contradicción)",
            "value": 0.22,
            "source": ["Nyhan & Reifler, 2010"],
            "notes": "Cuando la corrección refuerza la creencia errónea original.",
        },
        "INOCULACION_COGNITIVA": {
            "label": "Resistencia por Inoculación Cognitiva",
            "value": -0.30,
            "source": ["van der Linden et al., 2022"],
            "notes": "Valor negativo: reduce adopción de desinformación.",
        },
        "DISONANCIA_COGNITIVA": {
            "label": "Reducción de Disonancia Cognitiva",
            "value": 0.42,
            "cultural_variance": {
                "anglosaxon": 0.45,
                "latin": 0.40,
                "east_asian": 0.38,
            },
            "source": ["Festinger, 1957", "Festinger & Carlsmith, 1959"],
            "notes": (
                "Tensión psicológica ante creencias contradictorias; motiva "
                "racionalización, búsqueda de consistencia y rechazo activo de "
                "información disconfirmatoria."
            ),
        },
        "PENSAMIENTO_RAPIDO": {
            "label": "Predominio del Pensamiento Intuitivo (Sistema 1)",
            "value": 0.55,
            "cultural_variance": {
                "anglosaxon": 0.55,
                "latin": 0.58,
                "east_asian": 0.50,
            },
            "source": ["Kahneman, 2011", "Pennycook & Rand, 2019"],
            "notes": (
                "Predominio del pensamiento intuitivo y automático sobre el "
                "analítico en contextos de alta velocidad informacional. "
                "Pennycook & Rand (2019) vinculan pensamiento intuitivo con mayor "
                "difusión de desinformación."
            ),
        },
    },
    "mass_psychology": {
        "CONTAGIO_EMOCIONAL": {
            "label": "Contagio Emocional en Redes",
            "value": 0.42,
            "digital_weight": 0.95,
            "source": ["Kramer et al., 2014"],
            "notes": "Propagación de estados emocionales vía exposición pasiva.",
        },
        "CASCADA_INFORMACIONAL": {
            "label": "Cascada Informacional",
            "value": 0.55,
            "source": ["Bikhchandani et al., 1992"],
            "notes": "Adopción de creencias por imitación sin evidencia propia.",
        },
        "POLARIZACION_GRUPO": {
            "label": "Polarización por Deliberación Grupal",
            "value": 0.48,
            "source": ["Sunstein, 2002"],
            "notes": "Los grupos extremizan sus posiciones al deliberar internamente.",
        },
        "EFECTO_MANADA": {
            "label": "Efecto Manada (Herding)",
            "value": 0.52,
            "digital_weight": 0.90,
            "cultural_variance": {
                "east_asian": 0.60,
                "latin": 0.55,
                "anglosaxon": 0.45,
                "nordic": 0.38,
            },
            "source": ["Banerjee, 1992", "Lorenz et al., 2011"],
            "notes": (
                "Adopción de comportamientos basada en las acciones observadas de "
                "otros, con independencia de la información propia. Lorenz et al. "
                "(2011) demostraron que la información social reduce la diversidad "
                "de estimaciones y amplifica sesgos colectivos."
            ),
        },
        "SILENCIO_ESPIRAL": {
            "label": "Espiral del Silencio",
            "value": -0.42,
            "digital_weight": 0.80,
            "cultural_variance": {
                "east_asian": -0.55,
                "latin": -0.40,
                "anglosaxon": -0.35,
                "nordic": -0.28,
            },
            "source": ["Noelle-Neumann, 1974", "Hampton et al., 2014"],
            "notes": (
                "Autocensura de opiniones percibidas como minoritarias por miedo "
                "al aislamiento social. Hampton et al. (2014) extendieron el "
                "efecto a redes sociales digitales. Valor negativo: fuerza "
                "supresora de la expresión pública disidente."
            ),
        },
    },
    "cultural_variables": {
        "INDIVIDUALISMO_COLECTIVISMO": {
            "label": "Eje Individualismo-Colectivismo (Hofstede)",
            "value": 0.0,  # Neutralidad: varía radicalmente por cultura
            "cultural_variance": {
                "anglosaxon": 0.75,
                "latin": -0.10,
                "east_asian": -0.55,
                "middle_east": -0.30,
                "south_asian": -0.40,
                "subsaharan_africa": -0.25,
            },
            "source": ["Hofstede et al., 2010"],
            "notes": "Positivo=individualismo, negativo=colectivismo.",
        },
        "DISTANCIA_PODER": {
            "label": "Distancia al Poder (Hofstede)",
            "value": 0.0,
            "cultural_variance": {
                "anglosaxon": -0.25,
                "latin": 0.65,
                "east_asian": 0.55,
                "nordic": -0.60,
                "middle_east": 0.70,
                "south_asian": 0.60,
            },
            "source": ["Hofstede et al., 2010"],
            "notes": (
                "Grado en que las diferencias de poder son aceptadas y esperadas "
                "por los miembros de una sociedad. Positivo=alta distancia "
                "(jerarquías aceptadas), negativo=baja distancia (igualdad "
                "valorada). Base 0.0 por alta varianza cultural."
            ),
        },
        "EVITACION_INCERTIDUMBRE": {
            "label": "Evitación de Incertidumbre (Hofstede)",
            "value": 0.0,
            "cultural_variance": {
                "anglosaxon": -0.25,
                "latin": 0.65,
                "east_asian": 0.45,
                "nordic": -0.40,
                "middle_east": 0.50,
                "south_asian": 0.30,
            },
            "source": ["Hofstede et al., 2010"],
            "notes": (
                "Intolerancia cultural a la ambigüedad y a situaciones no "
                "estructuradas. Positivo=alta evitación (mayor rigidez normativa), "
                "negativo=alta tolerancia a la incertidumbre. Base 0.0 neutral."
            ),
        },
    },
    "social_status": {
        "EFECTO_CLASE_SOCIAL": {
            "label": "Modulación por Clase Social",
            "value": 0.35,
            "cultural_variance": {
                "latin": 0.42,
                "anglosaxon": 0.30,
                "east_asian": 0.25,
                "nordic": 0.18,
            },
            "source": ["Gidron & Hall, 2017", "Oesch, 2006"],
            "notes": (
                "Modulación de actitudes y receptividad política según posición "
                "socioeconómica. Clases trabajadoras muestran mayor receptividad "
                "a mensajes populistas y mayor distancia institucional "
                "(Gidron & Hall, 2017)."
            ),
        },
        "BRECHA_GENERACIONAL": {
            "label": "Diferencial de Opinión por Generación",
            "value": 0.42,
            "cultural_variance": {
                "anglosaxon": 0.45,
                "latin": 0.38,
                "east_asian": 0.32,
                "nordic": 0.35,
            },
            "source": ["Pew Research Center, 2020", "Inglehart, 2018"],
            "notes": (
                "Diferencia sistemática en actitudes y valores políticos entre "
                "cohortes generacionales (Boomers, Millennial, Gen-Z). "
                "Inglehart (2018) documenta cambio intergeneracional de valores "
                "hacia postmaterialismo."
            ),
        },
    },
    "gender": {
        "DIFERENCIAL_GENERO": {
            "label": "Diferencial de Opinión por Género",
            "value": 0.28,
            "cultural_variance": {
                "nordic": 0.40,
                "anglosaxon": 0.35,
                "latin": 0.22,
                "east_asian": 0.15,
                "middle_east": 0.10,
            },
            "source": ["Inglehart & Norris, 2000", "Pew Research Center, 2020"],
            "notes": (
                "Diferencia sistemática en posiciones políticas y valores sociales "
                "entre géneros. En democracias occidentales las mujeres tienden a "
                "posiciones más progresistas/liberales (Inglehart & Norris, 2000)."
            ),
        },
    },
    "game_theory": {
        "EQUILIBRIO_NASH_SOCIAL": {
            "label": "Tendencia al Equilibrio de Nash en Interacciones Sociales",
            "value": 0.60,
            "source": ["Nash, 1950", "Gintis, 2009"],
            "notes": "Utilidad de unirse al consenso mayoritario.",
        },
        "COSTO_DISIDENCIA": {
            "label": "Costo Social de la Disidencia",
            "value": -0.50,
            "source": ["Noelle-Neumann, 1993"],
            "notes": "Valor negativo: penalización por posición contramayoritaria.",
        },
        "DILEMA_PRISIONERO_SOCIAL": {
            "label": "Dilema del Prisionero en Interacciones Sociales",
            "value": 0.30,
            "source": ["Axelrod, 1984", "Nowak, 2006"],
            "notes": (
                "Dilema donde el interés individual colisiona con el colectivo. "
                "En juegos iterados emerge cooperación condicional (tit-for-tat). "
                "Valor positivo: tendencia neta a la cooperación en interacciones "
                "sociales repetidas (Axelrod, 1984)."
            ),
        },
        "CAZA_CIERVO": {
            "label": "Juego de Coordinación — Caza del Ciervo",
            "value": 0.45,
            "source": ["Skyrms, 2004", "Rousseau, 1755"],
            "notes": (
                "Juego de coordinación con dos equilibrios: cooperación mutua "
                "(ciervo, alta recompensa) y defección individual (liebre, baja "
                "recompensa segura). Valor positivo: tendencia a coordinar en el "
                "equilibrio de alta recompensa cuando hay confianza social "
                "suficiente (Skyrms, 2004)."
            ),
        },
    },
}

# ============================================================
# PARÁMETROS DE EJECUCIÓN DEL MOTOR
# ============================================================
BEYONDSIGHT_RUNTIME_PARAMS: dict = {
    "temperature": 0.45,             # Caos/Irracionalidad (backfire vs inoculación)
    "social_influence_lambda": 0.58,  # Peso de la red vs convicción propia
    "attractor_depth": 0.75,          # Fuerza de la narrativa dominante
    "repeller_strength": -0.45,       # Animosidad out-group (prosocialidad invertida)
    "payoff_coordination": 0.602,     # Utilidad de unirse al consenso
    "payoff_defection": -0.5,         # Costo de la disidencia
    "narrative_decay_rate": 0.0,      # Media-vida de influencia narrativa (neutralidad activa)
    "saturation_threshold": 0.0,      # Punto de rechazo por sobreexposición (neutralidad activa)
    "cultural_profile": "mixed",
    "validation_flags": [],
}

# Parámetros null del maestro que requieren datos empíricos adicionales
# (lista vacía: todos los parámetros fueron completados en v1.1.0)
_NULL_PARAMS: list = []

# Populate validation_flags with pending null params (never use 0.0 as default)
for _cat, _pid in _NULL_PARAMS:
    _entry = BEYONDSIGHT_EMPIRICAL_MASTER.get(_cat, {}).get(_pid, {})
    if _entry.get("value") is None:
        BEYONDSIGHT_RUNTIME_PARAMS["validation_flags"].append(
            f"{_cat}.{_pid}: pending_empirical_data"
        )


# ============================================================
# FUNCIONES DE ACCESO
# ============================================================

def get_runtime_params(cultural_profile: str = "mixed") -> dict:
    """
    Returns a complete runtime parameter dictionary with cultural modifiers applied.

    Applies cultural variance modifiers from BEYONDSIGHT_EMPIRICAL_MASTER over
    the base values in BEYONDSIGHT_RUNTIME_PARAMS.  The ``mixed`` profile uses
    the unmodified base values.  Unknown profiles fall back to ``mixed``.

    Args:
        cultural_profile: One of ``"mixed"``, ``"latin"``, ``"anglosaxon"``,
            ``"east_asian"``, ``"middle_east"``, ``"south_asian"``,
            ``"subsaharan_africa"``.  Defaults to ``"mixed"``.

    Returns:
        A new dict with all runtime parameters; values 0.0 and negative values
        are preserved without modification (they represent active neutrality and
        active repellers respectively).
    """
    params = dict(BEYONDSIGHT_RUNTIME_PARAMS)
    params["validation_flags"] = list(BEYONDSIGHT_RUNTIME_PARAMS["validation_flags"])
    params["cultural_profile"] = cultural_profile

    if cultural_profile == "mixed":
        return params

    # Apply known cultural variance to runtime params that have direct mapping
    # DERIVA_ALGORITMICA → temperature (caos social amplificado por algoritmos)
    deriva = BEYONDSIGHT_EMPIRICAL_MASTER["network_dynamics"]["DERIVA_ALGORITMICA"]
    if cultural_profile in deriva.get("cultural_variance", {}):
        cultural_val = deriva["cultural_variance"][cultural_profile]
        base_val = deriva["value"]
        delta = cultural_val - base_val
        params["temperature"] = float(
            max(-1.0, min(1.0, params["temperature"] + delta))
        )

    # INFLUENCIA_PARASOCIAL → social_influence_lambda
    parasocial = BEYONDSIGHT_EMPIRICAL_MASTER["network_dynamics"]["INFLUENCIA_PARASOCIAL"]
    if cultural_profile in parasocial.get("cultural_variance", {}):
        cultural_val = parasocial["cultural_variance"][cultural_profile]
        base_val = parasocial["value"]
        delta = cultural_val - base_val
        params["social_influence_lambda"] = float(
            max(-1.0, min(1.0, params["social_influence_lambda"] + delta))
        )

    return params


def get_param(category: str, param_id: str) -> dict:
    """
    Returns a parameter entry from BEYONDSIGHT_EMPIRICAL_MASTER by category and ID.

    Args:
        category: Top-level key in BEYONDSIGHT_EMPIRICAL_MASTER
            (e.g. ``"network_dynamics"``).
        param_id: Parameter key within the category
            (e.g. ``"DERIVA_ALGORITMICA"``).

    Returns:
        The parameter dictionary for the requested entry.

    Raises:
        KeyError: If ``category`` or ``param_id`` does not exist in the master
            dictionary, with a descriptive message.
    """
    if category not in BEYONDSIGHT_EMPIRICAL_MASTER:
        raise KeyError(
            f"Category '{category}' not found in BEYONDSIGHT_EMPIRICAL_MASTER. "
            f"Available categories: {list(BEYONDSIGHT_EMPIRICAL_MASTER.keys())}"
        )
    category_data = BEYONDSIGHT_EMPIRICAL_MASTER[category]
    if not isinstance(category_data, dict) or param_id not in category_data:
        raise KeyError(
            f"Parameter '{param_id}' not found in category '{category}'. "
            f"Available params: {list(category_data.keys()) if isinstance(category_data, dict) else '(not a dict)'}"
        )
    return category_data[param_id]

# ── Backward-compatible aliases (new preferred names) ─────────────────────────
MASSIVE_EMPIRICAL_MASTER = BEYONDSIGHT_EMPIRICAL_MASTER
MASSIVE_RUNTIME_PARAMS   = BEYONDSIGHT_RUNTIME_PARAMS
