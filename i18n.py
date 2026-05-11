"""
MASSIVE — Internationalization (i18n)
Supports English and Spanish for the UI.
"""

STRINGS = {
    "en": {
        "title": "MASSIVE",
        "subtitle": "Hybrid Simulator · Social Dynamics · LLM + Numerical Core",
        "opinion_space": "#### 📐 Opinion Space",
        "opinion_range": "Opinion Range",
        "bipolar_label": "[-1 rejection] ← 0 → [+1 support]",
        "probabilistic_label": "[0] → [0.5 neutral] → [1]",
        "llm_provider": "#### 🤖 LLM Provider",
        "provider": "Provider",
        "ollama_host": "Ollama Host",
        "model": "Model",
        "write_exact_id": "Or write exact ID:",
        "api_key": "API Key",
        "get_api_key": "Get API key →",
        "initial_state": "#### 🌍 Initial State",
        "initial_opinion": "Initial Opinion",
        "propaganda": "Main Narrative (A)",
        "institutional_trust": "Institutional Trust",
        "social_groups": "#### 👥 Social Groups",
        "opinion_group_a": "Affin Group Opinion",
        "opinion_group_b": "Opposing Group Opinion",
        "group_identity": "Group Identity Intensity",
        "advanced_mechanisms": "#### 🔬 Advanced Mechanisms",
        "confirmation_bias": "Confirmation Bias",
        "activate_narrative_b": "Activate Competing Narrative (B)",
        "narrativa_b_intensity": "Narrative B Intensity",
        "hk_epsilon": "HK Confidence Radius (ε)",
        "homophily_rate": "Homophily Rate",
        "egt_section": "#### ⚗️ EGT Replicator Model",
        "activate_replicator": "Activate Replicator (EGT)",
        "payoff_matrix": "Payoff Matrix (JSON 2D array)",
        "dt_step": "dt (integration step)",
        "strategic_section": "#### 🎮 Strategic Layer (Game Theory)",
        "activate_strategic": "Activate Strategic Layer",
        "strategic_weight": "Strategic Weight (ω)",
        "strategic_preset": "Game Preset",
        "strategic_preset_options": ["Custom", "Prisoner's Dilemma", "Stag Hunt", "Coordination"],
        "strategic_cc": "cc — Both cooperate (consensus)",
        "strategic_cd": "cd — I cooperate, other defects (sucker)",
        "strategic_dc": "dc — I defect, other cooperates (temptation)",
        "strategic_dd": "dd — Both defect (chaos)",
        "strategic_help": "The strategic force biases agents toward cooperation or defection based on their neighbours' positions. Range [-1, 1].",
        "ews_section": "#### 🚨 Early Warning Signals",
        "ews_warning": "⚠️ EWS: high_variance={hv}, high_autocorr={ha}, high_skewness={hs}",
        "tda_change": "🔺 Topological change detected (TDA/PH)",
        "simulation_settings": "#### ⚙️ Simulation Settings",
        "time_steps": "Time Steps",
        "llm_every_n": "LLM every N steps",
        "blend_alpha": "Blend (rule vs base)",
        "probabilistic_mode": "#### 🎲 Probabilistic Mode",
        "activate_multi_sim": "Activate Multiple Simulations",
        "num_simulations": "Number of Simulations",
        "run_simulation": "▶  Execute Simulation",
        "results": "### Results",
        "final_opinion": "Final Opinion",
        "vs_start": "vs start",
        "avg_polarization": "Average Polarization",
        "dist_to_neutral": "distance to neutral",
        "mean_std": "Mean ± σ",
        "dominant_regime": "Dominant Regime",
        "opinion_trajectory": "**Opinion Trajectory**",
        "rule_distribution": "**Rule Distribution**",
        "group_identity_evolution": "**Group Identity Evolution**",
        "probabilistic_dist": "### Probabilistic Distribution",
        "final_mean": "Final Mean",
        "p_over_neutral": "P(opinion > {neutro})",
        "pos_prob": "positive position probability",
        "p10_p90_range": "P10–P90 Range",
        "confidence_band": "80% confidence band",
        "log_expander": "🔍 Selector Decision Log",
        "export_expander": "⬇️ Export",
        "empty_state": "CONFIGURE PARAMETERS IN THE LEFT PANEL AND PRESS ▶ EXECUTE SIMULATION",
        "guide_expander": "📖 Guide to Available Models",
        "range_guide_expander": "📖 Which range to use?",
        "error_api_key": "⚠️ **{proveedor}** requires an API key.",
        "simulating": "Simulating...",
        "model_guide_content": """
**Transition Rules:**

| ID | Name | Basis | When it dominates |
|---|---|---|---|
| 0 | Lineal | Friedkin-Johnsen | Moderate conditions |
| 1 | Threshold | Granovetter (simple) | Propaganda crosses critical point |
| 2 | Memory | DeGroot with lag | Stable system, inertia |
| 3 | Backlash | Persuasion literature | Established rejection + propaganda |
| 4 | Polarization | Echo chamber | Trend already started |
| 5 | **HK** | Hegselmann-Krause (2002) | Groups very distant from each other |
| 6 | **Competitive Contagion** | Beutel et al. (2012) | Two active narratives |
| 7 | **Heterogeneous Threshold** | Granovetter (1978) | Social cascades |
| 8 | **Homofily** | Axelrod (1997) | Groups converge by similarity |
| 9 | **Replicator** | Taylor & Jonker (1978) | Evolutionary pressure between group strategies |
| 10 | **Nash Equilibrium** | Nash (1950) | Groups near coordination equilibrium |
| 11 | **Bayesian Network** | Pearl (1988) | Probabilistic belief update with evidence |
| 12 | **SIR Contagion** | Kermack & McKendrick (1927) | Epidemic-like opinion spread |

**Cross-cutting Mechanisms:**
- **Confirmation Bias** — opposing propaganda arrives attenuated based on current position.
- **Bipolar Range [-1,1]** — active rejection has direct and symmetrical expression with support.
- **Narrative B** — enables competitive contagion between two simultaneous narratives.
- **Strategic Layer (Game Theory)** — payoff-based force biases agents toward cooperation or defection.
""",
        "range_guide_content": """
| Situation | Range | Why |
|---|---|---|
| Vaccine, public policy, new product | **[-1,1] bipolar** | Active rejection ≠ indifference |
| Elections, referendum | **[-1,1] bipolar** | Voting against ≠ abstention |
| Technology adoption probability | **[0,1] probabilistic** | Natural adoption rate |
| Information diffusion / contagion | **[0,1] probabilistic** | SIR models in this range |
""",
    },
    "es": {
        "title": "MASSIVE",
        "subtitle": "Simulador híbrido · Dinámica social · LLM + Núcleo numérico",
        "opinion_space": "#### 📐 Espacio de opinión",
        "opinion_range": "Rango de valores",
        "bipolar_label": "[-1 rechazo] ← 0 → [+1 apoyo]",
        "probabilistic_label": "[0] → [0.5 neutro] → [1]",
        "llm_provider": "#### 🤖 Proveedor LLM",
        "provider": "Proveedor",
        "ollama_host": "Host Ollama",
        "model": "Modelo",
        "write_exact_id": "O escribe el ID exacto:",
        "api_key": "API Key",
        "get_api_key": "Obtener API key →",
        "initial_state": "#### 🌍 Estado inicial",
        "initial_opinion": "Opinión inicial",
        "propaganda": "Narrativa principal (A)",
        "institutional_trust": "Confianza institucional",
        "social_groups": "#### 👥 Grupos sociales",
        "opinion_group_a": "Opinión grupo afín",
        "opinion_group_b": "Opinión grupo contrario",
        "group_identity": "Intensidad identidad grupal",
        "advanced_mechanisms": "#### 🔬 Mecanismos avanzados",
        "confirmation_bias": "Sesgo de confirmación",
        "activate_narrative_b": "Activar narrativa competidora (B)",
        "narrativa_b_intensity": "Intensidad narrativa B",
        "hk_epsilon": "Radio de confianza HK (ε)",
        "homophily_rate": "Tasa de homofilia",
        "egt_section": "#### ⚗️ Modelo Replicador (EGT)",
        "activate_replicator": "Activar Replicador (EGT)",
        "payoff_matrix": "Matriz de pagos (JSON 2D)",
        "dt_step": "dt (paso de integración)",
        "strategic_section": "#### 🎮 Capa Estratégica (Teoría de Juegos)",
        "activate_strategic": "Activar Capa Estratégica",
        "strategic_weight": "Peso estratégico (ω)",
        "strategic_preset": "Preset de juego",
        "strategic_preset_options": ["Personalizado", "Dilema del Prisionero", "Caza del Ciervo", "Coordinación"],
        "strategic_cc": "cc — Ambos cooperan (consenso)",
        "strategic_cd": "cd — Yo coopero, otro traiciona (ingenuo)",
        "strategic_dc": "dc — Yo traiciono, otro coopera (tentación)",
        "strategic_dd": "dd — Ambos traicionan (caos)",
        "strategic_help": "La fuerza estratégica sesga a los agentes hacia cooperación o defección según la posición de sus vecinos. Rango [-1, 1].",
        "ews_section": "#### 🚨 Señales de Alerta Temprana",
        "ews_warning": "⚠️ EWS: varianza_alta={hv}, autocorr_alta={ha}, sesgo_alto={hs}",
        "tda_change": "🔺 Cambio topológico detectado (TDA/PH)",
        "simulation_settings": "#### ⚙️ Simulación",
        "time_steps": "Pasos temporales",
        "llm_every_n": "LLM cada N pasos",
        "blend_alpha": "Blend (regla vs base)",
        "probabilistic_mode": "#### 🎲 Modo probabilístico",
        "activate_multi_sim": "Activar simulación múltiple",
        "num_simulations": "Número de simulaciones",
        "run_simulation": "▶  Ejecutar simulación",
        "results": "### Resultados",
        "final_opinion": "Opinión final",
        "vs_start": "vs inicio",
        "avg_polarization": "Polarización media",
        "dist_to_neutral": "distancia al neutro",
        "mean_std": "Media ± σ",
        "dominant_regime": "Régimen dominante",
        "opinion_trajectory": "**Trayectoria de opinión**",
        "rule_distribution": "**Distribución de reglas**",
        "group_identity_evolution": "**Evolución de identidad grupal**",
        "probabilistic_dist": "### Distribución probabilística",
        "final_mean": "Media final",
        "p_over_neutral": "P(opinión > {neutro})",
        "pos_prob": "probabilidad posición positiva",
        "p10_p90_range": "Rango P10–P90",
        "confidence_band": "banda de confianza 80%",
        "log_expander": "🔍 Log de decisiones del selector",
        "export_expander": "⬇️ Exportar",
        "empty_state": "CONFIGURA LOS PARÁMETROS EN EL PANEL IZQUIERDO Y PRESIONA ▶ EJECUTAR SIMULACIÓN",
        "guide_expander": "📖 Guía de modelos disponibles",
        "range_guide_expander": "📖 ¿Qué rango usar?",
        "error_api_key": "⚠️ **{proveedor}** requiere API key.",
        "simulating": "Simulando...",
        "model_guide_content": """
**Reglas de transición:**

| ID | Nombre | Fundamento | Cuándo domina |
|---|---|---|---|
| 0 | Lineal | Friedkin-Johnsen | Condiciones moderadas |
| 1 | Umbral | Granovetter (simple) | Propaganda cruza punto crítico |
| 2 | Memoria | DeGroot con lag | Sistema estable, inercia |
| 3 | Backlash | Literatura persuasión | Rechazo establecido + propaganda |
| 4 | Polarización | Cámara de eco | Tendencia ya iniciada |
| 5 | **HK** | Hegselmann-Krause (2002) | Grupos muy distantes entre sí |
| 6 | **Contagio competitivo** | Beutel et al. (2012) | Dos narrativas activas |
| 7 | **Umbral heterogéneo** | Granovetter (1978) | Cascadas sociales |
| 8 | **Homofilia** | Axelrod (1997) | Grupos convergen por similitud |
| 9 | **Replicador** | Taylor & Jonker (1978) | Presión evolutiva entre estrategias de grupo |
| 10 | **Equilibrio de Nash** | Nash (1950) | Grupos próximos en equilibrio de coordinación |
| 11 | **Red Bayesiana** | Pearl (1988) | Actualización probabilística de creencias |
| 12 | **Contagio SIR** | Kermack & McKendrick (1927) | Difusión de opiniones tipo epidemia |

**Mecanismos transversales:**
- **Sesgo de confirmación** — propaganda contraria llega atenuada según la posición actual
- **Rango bipolar [-1,1]** — rechazo activo tiene expresión directa y simétrica con el apoyo
- **Narrativa B** — habilita el contagio competitivo entre dos narrativas simultáneas
- **Capa Estratégica (Teoría de Juegos)** — fuerza basada en pagos que sesga a los agentes hacia cooperación o defección
""",
        "range_guide_content": """
| Situación | Rango | Por qué |
|---|---|---|
| Vacuna, política pública, producto nuevo | **[-1,1] bipolar** | Rechazo activo ≠ indiferencia |
| Elecciones, referéndum | **[-1,1] bipolar** | Votar en contra ≠ abstención |
| Probabilidad de adopción de tecnología | **[0,1] probabilístico** | Tasa de adopción natural |
| Difusión de información / contagio | **[0,1] probabilístico** | Modelos SIR en este rango |
""",
    }
}

def t(key: str, lang: str = "en", **kwargs) -> str:
    """Translate a key to the given language."""
    text = STRINGS.get(lang, STRINGS["en"]).get(key, STRINGS["en"].get(key, key))
    return text.format(**kwargs)
