"""
MASSIVE — Interfaz Streamlit
Simulador híbrido con soporte completo de modelos extendidos
"""

import json
import os
from collections import Counter

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from i18n import t
from llm_credentials import persist_provider_api_key
from social_architect import buscar_estrategia_inversa
from visualizations import generate_social_network_viz
from micro_ui import render_micro_tab
from simulator import (
    MASSIVE_EMPIRICAL_MASTER,
    MASSIVE_RUNTIME_PARAMS,
    DEFAULT_CONFIG,
    DEFAULT_PAYOFF_MATRIX,
    DESCRIPCIONES_REGLAS,
    NOMBRES_REGLAS,
    PROVEEDORES,
    RANGOS_DISPONIBLES,
    apply_empirical_profile,
    get_graph_metrics,
    resumen_historial,
    simular,
    simular_multiples,
    simular_multiples_dask,
)

ANALYTICS_ANIMATION_FRAME_MS = 70
ANALYTICS_ANIMATION_PAUSE_MS = 0
# Logo hosted on GitHub CDN — always accessible on Streamlit Cloud / HF Spaces.
# A local copy lives at docs/assets/massive_logo.png for offline reference.
PROJECT_LOGO_URL = "https://github.com/user-attachments/assets/04c5860f-36d4-433c-a142-5761d0f16824"

# EMPIRICAL INTEGRATION — importar indicadores de base empírica si disponibles
try:
    from empirical_config import MASSIVE_RUNTIME_PARAMS as _EMPIRICAL_RUNTIME
    _EMPIRICAL_VALIDATION_FLAGS = _EMPIRICAL_RUNTIME.get("validation_flags", [])
except ImportError:
    _EMPIRICAL_VALIDATION_FLAGS = []

# CfC INTEGRATION — estado del motor neuronal para mostrar en la UI
try:
    from cfc_router import CfCRouter
    _CFC_STATUS = CfCRouter.get().status
except ImportError:
    _CFC_STATUS = {"regime_selector": False, "tau_matrix": False, "architect_policy": False}

# UIL INTEGRATION — Document Intelligence + Interpreter Layer
try:
    from interpreter_layer import InterpreterLayer
    from document_intelligence import DocumentIntelligence

    _UIL_AVAILABLE = True
except ImportError:
    _UIL_AVAILABLE = False

# Load environment variables from .env
load_dotenv()

# ------------------------------------------------------------
# GAME THEORY PRESETS (module-level constant)
# Payoff values are in the [-1, 1] bipolar range.
# ------------------------------------------------------------
# Keys are positional indices matching the i18n preset_options list:
#   0 → Custom / Personalizado
#   1 → Prisoner's Dilemma / Dilema del Prisionero
#   2 → Stag Hunt / Caza del Ciervo
#   3 → Coordination / Coordinación
_STRATEGIC_PRESETS: list[dict] = [
    # 0 — Custom: neutral starting point
    {"cc": 1.0, "cd": -1.0, "dc":  1.0, "dd": -1.0},
    # 1 — Prisoner's Dilemma: defection tempts but mutual defection is costly
    {"cc": 1.0, "cd": -1.0, "dc":  1.0, "dd": -0.5},
    # 2 — Stag Hunt: mutual cooperation pays most; solo defection yields zero
    {"cc": 1.0, "cd": -1.0, "dc":  0.0, "dd":  0.0},
    # 3 — Coordination: matching strategies rewarded, mismatches punished
    {"cc": 1.0, "cd": -1.0, "dc": -1.0, "dd":  1.0},
]

# ------------------------------------------------------------
# PÁGINA
# ------------------------------------------------------------
st.set_page_config(
    page_title="MASSIVE",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------
# ANALYTICS & SESSION STATE
# ------------------------------------------------------------
import streamlit.components.v1 as components
components.html("""
<script>
  // Google Analytics / PostHog script placeholder
  console.log('MASSIVE Analytics loaded');
</script>
""", width=0, height=0)

if "lead_captured" not in st.session_state:
    st.session_state["lead_captured"] = False
if "estr_inversa" not in st.session_state:
    st.session_state["estr_inversa"] = None
if "objetivo_inverso" not in st.session_state:
    st.session_state["objetivo_inverso"] = ""
if "corporate_graph" not in st.session_state:
    # Almacena el grafo NetworkX si se sube un CSV corporativo
    st.session_state["corporate_graph"] = None
if "last_simulation" not in st.session_state:
    st.session_state["last_simulation"] = None

# ------------------------------------------------------------
# ESTILOS
# ------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');
html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background-color: #0a0e14; color: #c5cdd9;
}
.stApp { background-color: #0a0e14; }
.bs-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 2.2rem; font-weight: 600;
    color: #5ccfe6; letter-spacing: -0.5px; line-height: 1.1;
}
.bs-subtitle {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem; color: #3d5166;
    letter-spacing: 2px; text-transform: uppercase;
    margin-top: 4px; margin-bottom: 2rem;
}
.metric-card {
    background: #0d1520; border: 1px solid #1a2535;
    border-left: 3px solid #5ccfe6; border-radius: 4px;
    padding: 14px 18px; margin-bottom: 10px;
}
.metric-label {
    font-family: 'IBM Plex Mono', monospace; font-size: 0.65rem;
    color: #3d5166; text-transform: uppercase; letter-spacing: 1.5px;
}
.metric-value {
    font-family: 'IBM Plex Mono', monospace; font-size: 1.6rem;
    font-weight: 600; color: #5ccfe6; line-height: 1.2;
}
.metric-delta-pos { color: #bae67e; font-size: 0.85rem; }
.metric-delta-neg { color: #ff8f40; font-size: 0.85rem; }
.metric-delta-neu { color: #3d5166; font-size: 0.85rem; }
.badge {
    display: inline-block; font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem; padding: 3px 10px; border-radius: 3px; margin: 2px;
}
.log-entry {
    font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem;
    color: #4d6680; padding: 3px 0; border-bottom: 1px solid #111820;
}
.log-entry:hover { color: #8ba7c0; }
section[data-testid="stSidebar"] {
    background-color: #0d1520; border-right: 1px solid #1a2535;
}
.stButton > button {
    font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem;
    background: #0d1520; color: #5ccfe6; border: 1px solid #5ccfe6;
    border-radius: 3px; padding: 10px 28px; letter-spacing: 1px;
    text-transform: uppercase; transition: all 0.15s ease; width: 100%;
}
.stButton > button:hover { background: #5ccfe6; color: #0a0e14; }
.streamlit-expanderHeader {
    font-family: 'IBM Plex Mono', monospace; font-size: 0.75rem;
    color: #3d5166 !important; text-transform: uppercase; letter-spacing: 1px;
}
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# HEADER
# ------------------------------------------------------------
# Streamlit renders image URLs directly in the browser; the local asset in
# docs/assets/massive_logo.png serves as an offline reference copy.
st.image(PROJECT_LOGO_URL, width=170)
st.markdown('<div class="bs-header">MASSIVE</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="bs-subtitle">Mathematical Architecture for Scalable Social Interaction &amp; Virtual Engine &nbsp;·&nbsp; Many behaving as One</div>',
    unsafe_allow_html=True,
)

# EMPIRICAL INTEGRATION — mostrar aviso si hay parámetros sin datos empíricos
if _EMPIRICAL_VALIDATION_FLAGS:
    n_pending = len(_EMPIRICAL_VALIDATION_FLAGS)
    st.warning(
        f"⚠️ **{n_pending} parámetro{'s' if n_pending != 1 else ''} sin datos empíricos** "
        f"— usando lógica del motor",
        icon="🔬",
    )

# ------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------
with st.sidebar:

    st.markdown("### MASSIVE Open")
    st.markdown("Proyecto de código abierto bajo licencia Apache 2.0. Libre para uso personal, académico y comercial con atribución al autor.")
    st.link_button("💼 Consultoría & Servicios", "mailto:MASSIVE@ejemplo.com")
    st.link_button("🤝 Contribuir al Proyecto", "https://github.com/Adlgr87/MASSIVE")
    st.markdown("---")

    # ── CfC ENGINE STATUS ──────────────────────────────────
    _any_cfc = any(_CFC_STATUS.values())
    if _any_cfc:
        _cfc_parts = []
        if _CFC_STATUS["regime_selector"]:
            _cfc_parts.append("selector")
        if _CFC_STATUS["tau_matrix"]:
            _cfc_parts.append("τ-matrix")
        if _CFC_STATUS["architect_policy"]:
            _cfc_parts.append("architect")
        st.markdown(
            f'<div class="badge" style="background:#0a1a0a;color:#bae67e;border:1px solid #bae67e">'
            f'⚡ CfC activo: {", ".join(_cfc_parts)}</div>',
            unsafe_allow_html=True,
        )
        st.caption("Motor neuronal CfC activo — menor latencia, sin API key.")
    else:
        st.markdown(
            '<div class="badge" style="background:#0d1520;color:#3d5166;border:1px solid #3d5166">'
            '◇ CfC: sin modelos (modo LLM/heurístico)</div>',
            unsafe_allow_html=True,
        )
        st.caption("Entrena los modelos con `python cfc_trainer.py` para activar CfC.")
    st.markdown("---")

    # ── LANGUAGE ───────────────────────────────────────────
    lang = st.radio("Language / Idioma", ["en", "es"], index=0, horizontal=True)

    st.markdown("---")

    # ── OPINION SPACE ──────────────────────────────────────
    st.markdown(t("opinion_space", lang))
    nombre_rango = st.radio(t("opinion_range", lang), list(RANGOS_DISPONIBLES.keys()), index=0)
    rango   = RANGOS_DISPONIBLES[nombre_rango]
    r_min, r_max, neutro = rango["min"], rango["max"], rango["neutro"]
    es_bipolar = r_min < 0
    defaults   = rango["defaults"]

    color_rango = "#c3a6ff" if es_bipolar else "#5ccfe6"
    etiqueta    = t("bipolar_label", lang) if es_bipolar else t("probabilistic_label", lang)
    st.markdown(
        f'<div class="badge" style="background:#0d1520;color:{color_rango};border:1px solid {color_rango}">'
        f'{etiqueta}</div>',
        unsafe_allow_html=True,
    )
    st.caption(rango["descripcion"])

    st.markdown("---")

    # ── LLM PROVIDER ──────────────────────────────────────
    st.markdown(t("llm_provider", lang))
    proveedor = st.selectbox(t("provider", lang), list(PROVEEDORES.keys()), index=0)
    st.caption(f"ℹ️ {PROVEEDORES[proveedor]['descripcion']}")

    api_key, modelo, ollama_host = "", "", DEFAULT_CONFIG["ollama_host"]

    # Try to get API Key from environment or st.secrets
    env_keys = {
        "groq": os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY"),
        "openai": os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY"),
        "openrouter": os.getenv("OPENROUTER_API_KEY") or st.secrets.get("OPENROUTER_API_KEY")
    }

    if proveedor == "ollama":
        ollama_host = st.text_input(t("ollama_host", lang), value=os.getenv("OLLAMA_HOST") or "http://localhost:11434")
        modelo = st.selectbox(t("model", lang), PROVEEDORES[proveedor]["modelos_sugeridos"])
        mc = st.text_input(t("write_exact_id", lang), placeholder="ej. deepseek-r1:7b")
        if mc.strip():
            modelo = mc.strip()
    elif proveedor in ("groq", "openai", "openrouter"):
        links = {"groq": "https://console.groq.com/keys",
                 "openai": "https://platform.openai.com/api-keys",
                 "openrouter": "https://openrouter.ai/keys"}
        st.markdown(f"[{t('get_api_key', lang)}]({links[proveedor]})")
        
        default_key = env_keys.get(proveedor) or ""
        api_key = st.text_input(t("api_key", lang), value=default_key, type="password")
        
        modelo  = st.selectbox(t("model", lang), PROVEEDORES[proveedor]["modelos_sugeridos"])
        mc = st.text_input(t("write_exact_id", lang))
        if mc.strip():
            modelo = mc.strip()

    usar_langchain = st.toggle("⛓️ Usar LangChain", value=False,
        help="Usa LangChain en lugar de llamadas HTTP directas al LLM. Requiere langchain instalado.")

    st.markdown("---")

    # ── INITIAL STATE ──────────────────────────────────────
    st.markdown(t("initial_state", lang))

    opinion0   = st.slider(t("initial_opinion", lang), r_min, r_max, float(defaults["opinion_inicial"]), 0.01)
    propaganda = st.slider(t("propaganda", lang),      r_min, r_max, float(defaults["propaganda"]),      0.01)
    confianza  = st.slider(t("institutional_trust", lang),  0.0, 1.0, float(defaults["confianza"]), 0.01)

    st.markdown("---")
    st.markdown(t("social_groups", lang))

    op_grupo_a  = st.slider(t("opinion_group_a", lang),      r_min, r_max, float(defaults["opinion_grupo_a"]), 0.01)
    op_grupo_b  = st.slider(t("opinion_group_b", lang), r_min, r_max, float(defaults["opinion_grupo_b"]), 0.01)
    pertenencia = st.slider(t("group_identity", lang), 0.0, 1.0, 0.65, 0.01)

    st.markdown("---")
    st.markdown(t("advanced_mechanisms", lang))

    sesgo_conf = st.slider(
        t("confirmation_bias", lang),
        0.0, 1.0, 0.3, 0.05
    )

    activar_narrativa_b = st.toggle(
        t("activate_narrative_b", lang),
        value=False
    )
    narrativa_b = 0.0
    if activar_narrativa_b:
        narrativa_b = st.slider(
            t("narrativa_b_intensity", lang),
            r_min, r_max,
            -0.3 if es_bipolar else 0.3,
            0.01
        )

    hk_epsilon = st.slider(
        t("hk_epsilon", lang),
        0.1, 0.8, 0.3, 0.05
    )

    homofilia_tasa = st.slider(
        t("homophily_rate", lang),
        0.0, 0.2, 0.05, 0.01
    )

    st.markdown("---")
    st.markdown(t("egt_section", lang))

    activar_replicador = st.toggle(t("activate_replicator", lang), value=False)
    payoff_matrix_cfg: list = list(DEFAULT_PAYOFF_MATRIX)
    dt_cfg: float = 0.1
    if activar_replicador:
        payoff_raw = st.text_area(
            t("payoff_matrix", lang),
            value=json.dumps(DEFAULT_PAYOFF_MATRIX),
            height=80,
            help="Introduce una matriz 2×2 en formato JSON. Ejemplo: [[1,0],[0,1]]",
        )
        try:
            parsed = json.loads(payoff_raw)
            if (
                isinstance(parsed, list)
                and len(parsed) == 2
                and all(isinstance(row, list) and len(row) == 2 for row in parsed)
            ):
                payoff_matrix_cfg = parsed
            else:
                st.error("La matriz debe ser 2×2. Usando identidad como fallback.")
        except json.JSONDecodeError:
            st.error("JSON inválido para la matriz de pagos. Usando identidad como fallback.")
        dt_cfg = st.slider(
            t("dt_step", lang),
            min_value=0.01, max_value=1.0, value=0.1, step=0.01,
        )

    st.markdown("---")
    st.markdown(t("strategic_section", lang))
    st.caption(t("strategic_help", lang))

    activar_strategic = st.toggle(t("activate_strategic", lang), value=False)
    strategic_cfg_ui: dict = {"enabled": False}
    if activar_strategic:
        # Game preset selector
        preset_options = t("strategic_preset_options", lang)
        preset_key = st.selectbox(t("strategic_preset", lang), preset_options)

        # Resolve preset values from module-level constant via index
        preset_idx = preset_options.index(preset_key)
        preset_vals = _STRATEGIC_PRESETS[preset_idx]

        col_cc, col_cd = st.columns(2)
        col_dc, col_dd = st.columns(2)
        with col_cc:
            cc_val = st.slider(t("strategic_cc", lang), -1.0, 1.0, preset_vals["cc"], 0.1)
        with col_cd:
            cd_val = st.slider(t("strategic_cd", lang), -1.0, 1.0, preset_vals["cd"], 0.1)
        with col_dc:
            dc_val = st.slider(t("strategic_dc", lang), -1.0, 1.0, preset_vals["dc"], 0.1)
        with col_dd:
            dd_val = st.slider(t("strategic_dd", lang), -1.0, 1.0, preset_vals["dd"], 0.1)

        omega = st.slider(t("strategic_weight", lang), 0.0, 1.0, 0.3, 0.05)

        strategic_cfg_ui = {
            "enabled": True,
            "payoff_matrix": {"cc": cc_val, "cd": cd_val, "dc": dc_val, "dd": dd_val},
            "strategic_weight": omega,
        }

    st.markdown("---")
    st.markdown(t("simulation_settings", lang))

    pasos       = st.slider(t("time_steps", lang),   20, 300, 60, 5)
    cada_n      = st.slider(t("llm_every_n", lang),    1,  20,  5, 1)
    alpha       = st.slider(t("blend_alpha", lang), 0.0, 1.0, 0.80, 0.05)

    st.markdown("---")
    st.markdown(t("probabilistic_mode", lang))
    modo_prob = st.toggle(t("activate_multi_sim", lang), value=False)
    n_sims = 50
    usar_dask = False
    if modo_prob:
        n_sims = st.slider(t("num_simulations", lang), 10, 200, 50, 10)
        usar_dask = st.toggle("⚡ Paralelizar con Dask", value=False,
            help="Usa Dask para paralelizar las simulaciones. Acelera el cálculo en máquinas con múltiples núcleos.")

    st.markdown("---")
    st.markdown("### 🌐 Datos de Redes Sociales")
    activar_social = st.toggle("Importar datos reales de RRSS", value=False)
    social_opinions = None

    if activar_social:
        red_social = st.radio("Red social", ["Twitter/X", "Reddit"], horizontal=True)
        query_social = st.text_input("Búsqueda / tema", placeholder="ej. climate change, inteligencia artificial")

        if red_social == "Twitter/X":
            bearer_token = st.text_input("Bearer Token", type="password", key="tw_bearer")
            if st.button("🐦 Obtener tweets") and query_social and bearer_token:
                try:
                    from social_connectors import TwitterConnector
                    conn = TwitterConnector(bearer_token=bearer_token)
                    result = conn.fetch_opinions(query_social, max_results=100,
                                                 range_type="bipolar" if es_bipolar else "unipolar")
                    social_opinions = result
                    st.success(f"✅ {result['n_tweets']} tweets analizados | opinión media: {result['mean_opinion']:+.3f}")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:  # Reddit
            reddit_client_id = st.text_input("Client ID", type="password", key="reddit_cid")
            reddit_secret    = st.text_input("Client Secret", type="password", key="reddit_sec")
            subreddit_name   = st.text_input("Subreddit", placeholder="ej. politics, worldnews")
            if st.button("🤖 Obtener posts") and query_social and reddit_client_id and reddit_secret and subreddit_name:
                try:
                    from social_connectors import RedditConnector
                    conn = RedditConnector(client_id=reddit_client_id, client_secret=reddit_secret)
                    result = conn.fetch_opinions(subreddit_name, query_social, limit=100,
                                                  range_type="bipolar" if es_bipolar else "unipolar")
                    social_opinions = result
                    st.success(f"✅ {result['n_posts']} posts de r/{subreddit_name} | opinión media: {result['mean_opinion']:+.3f}")
                except Exception as e:
                    st.error(f"Error: {e}")

        if social_opinions and len(social_opinions.get("opinions", [])) > 0:
            social_mean = float(social_opinions["mean_opinion"])
            st.caption(f"📊 σ={social_opinions['std_opinion']:.3f} | Opinión media de RRSS: {social_mean:+.3f}")
            usar_opinion_social = st.toggle(
                f"Usar {social_mean:+.3f} como opinión inicial (reemplaza el slider)",
                value=True,
                key="usar_opinion_social_toggle",
            )
            if usar_opinion_social:
                opinion0 = social_mean

    st.markdown("---")
    st.markdown("#### 🧪 Perfil Empírico" if lang == "es" else "#### 🧪 Empirical Profile")
    activar_empirico = st.toggle(
        "Aplicar calibración empírica (v{})".format(MASSIVE_EMPIRICAL_MASTER["meta"]["version"])
        if lang == "es"
        else "Apply empirical calibration (v{})".format(MASSIVE_EMPIRICAL_MASTER["meta"]["version"]),
        value=False,
        help=(
            "Aplica los índices de calibración empírica consolidados (redes, temporales, "
            "teoría de juegos) normalizados al rango [-1, 1]."
            if lang == "es"
            else "Applies consolidated empirical calibration indices (network dynamics, "
            "temporal effects, game theory) normalised to [-1, 1]."
        ),
    )
    if activar_empirico:
        rp = MASSIVE_RUNTIME_PARAMS
        st.caption(
            f"λ social={rp['social_influence_lambda']} · "
            f"T caos={rp['temperature']} · "
            f"atractor={rp['attractor_depth']} · "
            f"payoff cc={rp['payoff_coordination']} · "
            f"payoff dd={rp['payoff_defection']}"
        )

    st.markdown("---")
    correr = st.button(t("run_simulation", lang))


# ------------------------------------------------------------
# LÓGICA PRINCIPAL
# ------------------------------------------------------------
if _UIL_AVAILABLE:
    tab1, tab2, tab3, tab4, tab5, tab6, tab_uil = st.tabs([
        '📊 Simulación Tradicional',
        '🧠 Arquitecto Social (Modo Inverso)',
        '🌐 Simulación Multicapa',
        '⚡ Simulación Masiva',
        '🎬 Centro Analítico',
        '🔬 Micro — Familias de Futuros',
        '📄 Document Intelligence',
    ])
else:
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        '📊 Simulación Tradicional',
        '🧠 Arquitecto Social (Modo Inverso)',
        '🌐 Simulación Multicapa',
        '⚡ Simulación Masiva',
        '🎬 Centro Analítico',
        '🔬 Micro — Familias de Futuros',
    ])
    tab_uil = None

with tab1:
    if correr:

        if PROVEEDORES[proveedor]["requiere_key"] and not api_key.strip():
            st.error(f"⚠️ **{proveedor}** requiere API key.")
            st.stop()

        persist_provider_api_key(proveedor, api_key)

        config_run = {
            "rango":              nombre_rango,
            "proveedor":          proveedor,
            "modelo":             modelo,
            "ollama_host":        ollama_host,
            "alpha_blend":        alpha,
            "sesgo_confirmacion": sesgo_conf,
            "hk_epsilon":         hk_epsilon,
            "homofilia_tasa":     homofilia_tasa,
            "usar_langchain":     usar_langchain,
        }
        if activar_replicador:
            config_run["modelo_matematico"] = "Replicator"
            config_run["payoff_matrix"]     = payoff_matrix_cfg
            config_run["dt"]                = dt_cfg
        if activar_strategic:
            config_run["strategic"] = strategic_cfg_ui
        if activar_empirico:
            config_run = apply_empirical_profile(config_run)

        estado_inicial = {
            "opinion":          opinion0,
            "propaganda":       propaganda,
            "confianza":        confianza,
            "opinion_grupo_a":  op_grupo_a,
            "opinion_grupo_b":  op_grupo_b,
            "pertenencia_grupo": pertenencia,
        }
        if activar_narrativa_b:
            estado_inicial["narrativa_b"] = narrativa_b

        with st.spinner(t("simulating", lang)):
            historial = simular(
                estado_inicial, pasos=pasos, cada_n_pasos=cada_n,
                config=config_run, verbose=False,
            )
            resultado_prob = None
            if modo_prob:
                if usar_dask:
                    resultado_prob = simular_multiples_dask(
                        estado_inicial, pasos=pasos, cada_n_pasos=cada_n,
                        config=config_run, n_simulaciones=n_sims,
                    )
                else:
                    resultado_prob = simular_multiples(
                        estado_inicial, pasos=pasos, cada_n_pasos=cada_n,
                        config=config_run, n_simulaciones=n_sims,
                    )

        stats     = resumen_historial(historial, config_run)
        opiniones = [h["opinion"] for h in historial]
        delta     = stats["delta_total"]
        st.session_state["last_simulation"] = {
            "historial": historial,
            "stats": stats,
            "config": config_run,
            "is_bipolar": es_bipolar,
            "neutro": neutro,
            "pasos": pasos,
        }

        # ── BADGES de mecanismos activos ───────────────────────
        badges = []
        if sesgo_conf > 0.1:
            badges.append(f'<span class="badge" style="background:#1a2535;color:#ff8f40;border:1px solid #ff8f40">sesgo={sesgo_conf:.2f}</span>')
        if activar_narrativa_b:
            badges.append(f'<span class="badge" style="background:#1a2535;color:#c3a6ff;border:1px solid #c3a6ff">narrativa B={narrativa_b:+.2f}</span>')
        if hk_epsilon != 0.3:
            badges.append(f'<span class="badge" style="background:#1a2535;color:#bae67e;border:1px solid #bae67e">HK ε={hk_epsilon:.2f}</span>')
        if activar_social and social_opinions and len(social_opinions.get("opinions", [])) > 0:
            src = social_opinions.get("query", "RRSS")
            badges.append(f'<span class="badge" style="background:#1a2535;color:#5ccfe6;border:1px solid #5ccfe6">📡 RRSS: {src[:20]}</span>')
        badges.append(
            f'<span class="badge" style="background:#0d1520;color:{color_rango};border:1px solid {color_rango}">'
            f'rango {nombre_rango.split("—")[0].strip()} · neutro={neutro}</span>'
        )
        st.markdown(" ".join(badges), unsafe_allow_html=True)

        # ── EWS / TDA INDICATORS ───────────────────────────────
        ews_final = historial[-1].get("ews", {})
        ews_flags_final = ews_final.get("flags", {})
        if any(ews_flags_final.values()):
            st.warning(
                t("ews_warning", lang,
                  hv=ews_flags_final.get("high_variance", False),
                  ha=ews_flags_final.get("high_autocorr", False),
                  hs=ews_flags_final.get("high_skewness", False)),
            )

        tda_final = historial[-1].get("tda_change", False)
        if tda_final:
            st.error(t("tda_change", lang))

        # ── MÉTRICAS ───────────────────────────────────────────
        st.markdown(t("results", lang))
        c1, c2, c3, c4 = st.columns(4)

        delta_cls = "metric-delta-pos" if delta > 0 else ("metric-delta-neg" if delta < -0.01 else "metric-delta-neu")
        delta_sym = "▲" if delta > 0.01 else ("▼" if delta < -0.01 else "◆")

        with c1:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-label">{t('final_opinion', lang)}</div>
                <div class="metric-value">{stats['opinion_final']:+.3f}</div>
                <div class="{delta_cls}">{delta_sym} {delta:+.3f} {t('vs_start', lang)}</div>
            </div>""", unsafe_allow_html=True)

        with c2:
            pol     = stats["polarizacion_media"]
            amp     = r_max - r_min
            pol_cls = "metric-delta-neg" if pol > 0.3 * amp else "metric-delta-neu"
            st.markdown(f"""<div class="metric-card">
                <div class="metric-label">{t('avg_polarization', lang)}</div>
                <div class="metric-value">{pol:.3f}</div>
                <div class="{pol_cls}">{t('dist_to_neutral', lang)} ({neutro})</div>
            </div>""", unsafe_allow_html=True)

        with c3:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-label">{t('mean_std', lang)}</div>
                <div class="metric-value">{stats['media']:+.3f}</div>
                <div class="metric-delta-neu">σ = {stats['desviacion']:.3f}</div>
            </div>""", unsafe_allow_html=True)

        with c4:
            regla_dom     = stats.get("regla_dominante", "—")
            reglas_usadas = [h.get("_regla_nombre", "") for h in historial if "_regla_nombre" in h]
            n_dom         = Counter(reglas_usadas).get(regla_dom, 0)
            # Detectar si el selector CfC actuó en algún paso
            razones = [h.get("_razon", "") for h in historial if "_razon" in h]
            n_cfc   = sum(1 for r in razones if r.startswith("cfc"))
            selector_label = (
                f"⚡ CfC ({n_cfc} pasos)" if n_cfc > 0 else
                ("heurístico" if proveedor == "heurístico" else proveedor)
            )
            st.markdown(f"""<div class="metric-card">
                <div class="metric-label">{t('dominant_regime', lang)}</div>
                <div class="metric-value" style="font-size:1.0rem">{regla_dom}</div>
                <div class="metric-delta-neu">{n_dom}/{pasos} · {selector_label}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── GRÁFICO PRINCIPAL ──────────────────────────────────
        col_g, col_s = st.columns([3, 1])

        with col_g:
            df_data = {
                "Opinión":         opiniones,
                "Neutro":          [neutro]     * len(opiniones),
                "Narrativa A":     [propaganda] * len(opiniones),
                "Grupo afín":      [op_grupo_a] * len(opiniones),
                "Grupo contrario": [op_grupo_b] * len(opiniones),
            }
            if activar_narrativa_b:
                df_data["Narrativa B"] = [narrativa_b] * len(opiniones)

            st.markdown("**Trayectoria de opinión**")
            st.line_chart(
                pd.DataFrame(df_data),
                color=["#5ccfe6", "#3d5166", "#ff8f40", "#bae67e", "#f28779"]
                      + (["#c3a6ff"] if activar_narrativa_b else []),
            )
            
            st.markdown("### Topología de Red Social (Física)")
            fig_net = generate_social_network_viz(opiniones[-1], historial[-1]["confianza"], amalgama=not es_bipolar, is_bipolar=es_bipolar)
            st.plotly_chart(fig_net, use_container_width=True)
            
            share_url = "https://github.com/Adlgr87/MASSIVE"
            st.markdown(f"**¿Impresionante?** [Compartir en 𝕏](https://twitter.com/intent/tweet?text=Acabo%20de%20simular%20una%20dinámica%20social%20en%20MASSIVE%20AI!%20&url={share_url}) | [Compartir en LinkedIn](https://www.linkedin.com/sharing/share-offsite/?url={share_url})")

        with col_s:
            st.markdown("**Distribución de reglas**")
            conteo = Counter(reglas_usadas)
            df_r   = pd.DataFrame({
                "Regla": list(conteo.keys()),
                "Pasos": list(conteo.values()),
            }).sort_values("Pasos", ascending=False)
            st.dataframe(df_r, use_container_width=True, hide_index=True)

            # Evolución de pertenencia al grupo (si homofilia cambió algo)
            pertens = [h.get("pertenencia_grupo", pertenencia) for h in historial]
            if max(pertens) - min(pertens) > 0.01:
                st.markdown("**Evolución de identidad grupal**")
                st.line_chart(pd.DataFrame({"Identidad grupal": pertens}))

        # ── MODO PROBABILÍSTICO ────────────────────────────────
        if resultado_prob:
            rp = resultado_prob
            st.markdown("### Distribución probabilística")
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">Media final</div>
                    <div class="metric-value">{rp['media']:+.3f}</div>
                    <div class="metric-delta-neu">σ = {rp['std']:.3f}</div>
                </div>""", unsafe_allow_html=True)
            with cc2:
                prob  = rp["p_sobre_neutro"]
                pcls  = "metric-delta-pos" if prob > 0.6 else ("metric-delta-neg" if prob < 0.4 else "metric-delta-neu")
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">P(opinión > {neutro})</div>
                    <div class="metric-value">{prob:.1%}</div>
                    <div class="{pcls}">probabilidad posición positiva</div>
                </div>""", unsafe_allow_html=True)
            with cc3:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">Rango P10–P90</div>
                    <div class="metric-value">{rp['percentiles']['p10']:+.2f} – {rp['percentiles']['p90']:+.2f}</div>
                    <div class="metric-delta-neu">banda de confianza 80%</div>
                </div>""", unsafe_allow_html=True)

            st.line_chart(pd.DataFrame({
                "Trayectoria": opiniones,
                "Optimista":   [rp["escenarios"]["optimista"]] * len(opiniones),
                "Mediano":     [rp["escenarios"]["mediano"]]   * len(opiniones),
                "Pesimista":   [rp["escenarios"]["pesimista"]] * len(opiniones),
                "Neutro":      [neutro]                        * len(opiniones),
            }), color=["#5ccfe6", "#bae67e", "#ff8f40", "#f28779", "#3d5166"])

        # ── LOG ────────────────────────────────────────────────
        with st.expander("🔍 Log de decisiones del selector"):
            cambios = [h for h in historial[1:] if h.get("_paso", 0) % cada_n == 0]
            for h in cambios:
                extras = ""
                if "_fraccion_adoptantes" in h:
                    extras += f" | adoptantes={h['_fraccion_adoptantes']:.2f}"
                if "_sim_grupo_a" in h:
                    extras += f" | sim_A={h['_sim_grupo_a']:.2f} sim_B={h.get('_sim_grupo_b',0):.2f}"
                if "_nash_sigma_a" in h:
                    extras += f" | Nash σ_A={h['_nash_sigma_a']:.2f}"
                if "_bayes_uncertainty" in h:
                    extras += f" | BN uncertainty={h['_bayes_uncertainty']:.4f}"
                if "_sir_I" in h:
                    extras += f" | SIR I={h['_sir_I']:.3f} R={h['_sir_R']:.3f}"
                st.markdown(
                    f'<div class="log-entry">t={h.get("_paso","?"):3} │ '
                    f'<b>{h.get("_regla_nombre","?")}</b> │ '
                    f'op={h.get("opinion",0):+.3f} │ {h.get("_razon","")}{extras}</div>',
                    unsafe_allow_html=True,
                )

        # ── EXPORTAR ───────────────────────────────────────────
        with st.expander("⬇️ Exportar"):
            df_exp  = pd.DataFrame(historial)
            cols    = ["opinion", "propaganda", "confianza", "pertenencia_grupo",
                       "_paso", "_regla_nombre", "_razon", "_rango",
                       "_fraccion_adoptantes", "_sim_grupo_a", "_sim_grupo_b"]
            cols_ok = [c for c in cols if c in df_exp.columns]
            st.dataframe(df_exp[cols_ok], use_container_width=True)
            ca, cb  = st.columns(2)
            with ca:
                st.download_button("⬇ CSV",
                    data=df_exp[cols_ok].to_csv(index=False),
                    file_name="massive.csv", mime="text/csv")
            with cb:
                st.download_button("⬇ JSON",
                    data=json.dumps(historial, indent=2, default=str),
                    file_name="massive.json", mime="application/json")

    # ------------------------------------------------------------
    # EMPTY STATE
    # ------------------------------------------------------------
    else:
        st.markdown(f"""
        <div style="border:1px dashed #1a2535;border-radius:4px;padding:48px;text-align:center;margin-top:2rem;">
            <div style="font-family:'IBM Plex Mono',monospace;color:#3d5166;font-size:0.8rem;letter-spacing:2px;">
                {t('empty_state', lang)}
            </div>
        </div>""", unsafe_allow_html=True)

        with st.expander(t("guide_expander", lang)):
            st.markdown(t("model_guide_content", lang))

        with st.expander(t("range_guide_expander", lang)):
            st.markdown(t("range_guide_content", lang))


with tab2:
    st.markdown("### Arquitecto Social: Ingeniería Inversa 🧠")
    st.markdown(
        "Describe el **clima social final** que deseas lograr en la red y nuestro Agente LLM "
        "iterará con los modelos matemáticos hasta encontrar la receta sociológica exacta."
    )

    # ── SELECTOR DE MODO ─────────────────────────────────────────
    modo_cols = st.columns([1, 1])
    with modo_cols[0]:
        modo_simulacion = st.radio(
            "**Modo de Simulación**",
            options=["macro", "corporativo"],
            format_func=lambda m: "🌐 Modo Macro (Redes Sociales/Políticas)" if m == "macro" else "🏢 Modo Corporativo (Organizaciones)",
            horizontal=True,
        )

    # ── CARGA DE CSV CORPORATIVO ──────────────────────────────────
    grafo_org = st.session_state.get("corporate_graph", None)
    metricas_red = ""

    if modo_simulacion == "corporativo":
        st.markdown("---")
        st.markdown("#### Red Organizacional")
        csv_col, metrics_col = st.columns([3, 2])
        with csv_col:
            csv_uploaded = st.file_uploader(
                "📂 Sube tu CSV de red (columnas: `source`, `target`)",
                type=["csv"],
                help="Cada fila representa una conexión entre dos personas/departamentos.",
            )
            if csv_uploaded is not None:
                try:
                    import networkx as nx
                    df_csv = pd.read_csv(csv_uploaded)
                    if "source" in df_csv.columns and "target" in df_csv.columns:
                        G = nx.from_pandas_edgelist(df_csv, source="source", target="target")
                        st.session_state["corporate_graph"] = G
                        grafo_org = G
                        st.success(f"✅ Red cargada: **{G.number_of_nodes()}** nodos, **{G.number_of_edges()}** conexiones.")
                    else:
                        st.error("El CSV necesita columnas 'source' y 'target'.")
                except Exception as e:
                    st.error(f"Error al cargar el CSV: {e}")

        with metrics_col:
            if grafo_org is not None:
                metricas_red = get_graph_metrics(grafo_org, modo="corporativo", top_n=5)
                st.markdown("**Métricas de la Red:**")
                st.code(metricas_red, language="text")
            else:
                st.info("Sin CSV cargado. Se usará una red organizacional genérica.")
                # Red sintética de demo para modo corporativo sin CSV
                import networkx as nx
                G_demo = nx.barabasi_albert_graph(20, 2, seed=42)
                G_demo = nx.relabel_nodes(G_demo, {i: f"Nodo_{chr(65+i%26)}{i//26 or ''}" for i in G_demo.nodes()})
                metricas_red = get_graph_metrics(G_demo, modo="corporativo", top_n=5)
                # Mostrar advertencia amigable
                st.caption(f"🔁 Red demo (20 nodos, Barabási-Albert):\n{metricas_red}")

    elif modo_simulacion == "macro":
        metricas_red = ""  # En modo macro no se usan métricas de grafo

    st.markdown("---")

    # ── OBJETIVO Y EJECUCIÓN ──────────────────────────────────────
    placeholder_objetivo = (
        "Ej: 'Quiero alinear al equipo de ventas con la nueva estrategia en 30 días, "
        "empezando por los líderes informales identificados.'"
        if modo_simulacion == "corporativo" else
        "Ej: 'Quiero despolarizar una red dividida en dos bandos radicales y lograr un consenso moderado.'"
    )
    objetivo = st.text_area("✏️ Describe tu objetivo:", placeholder=placeholder_objetivo, height=100)
    usar_langchain_arq = st.toggle("⛓️ Arquitecto con LangChain", value=False,
        help="Usa LangChain chains en lugar de HTTP directo")

    if st.button("⚡ Generar Estrategia Maestra"):
        if objetivo:
            if PROVEEDORES[proveedor]["requiere_key"] and not api_key.strip():
                st.error("⚠️ Se requiere API key para generar estrategias con el LLM.")
                st.stop()

            persist_provider_api_key(proveedor, api_key)

            config_run = {
                "rango":              nombre_rango,
                "proveedor":          proveedor,
                "modelo":             modelo,
                "ollama_host":        ollama_host,
                "alpha_blend":        alpha,
                "sesgo_confirmacion": sesgo_conf,
                "hk_epsilon":         hk_epsilon,
                "homofilia_tasa":     homofilia_tasa,
                # Pasar tamaño del grafo para el cálculo de proporciones target_nodes
                "_n_nodos": grafo_org.number_of_nodes() if grafo_org else 20,
            }
            if activar_replicador:
                config_run["modelo_matematico"] = "Replicator"
                config_run["payoff_matrix"]     = payoff_matrix_cfg
                config_run["dt"]                = dt_cfg
            if activar_strategic:
                config_run["strategic"] = strategic_cfg_ui
            estado_inicial = {
                "opinion": opinion0,
                "propaganda": propaganda,
                "confianza": confianza,
                "opinion_grupo_a": op_grupo_a,
                "opinion_grupo_b": op_grupo_b,
                "pertenencia_grupo": pertenencia,
            }
            if activar_narrativa_b:
                estado_inicial["narrativa_b"] = narrativa_b

            # Badge de modo
            modo_badge_color = "#c3a6ff" if modo_simulacion == "corporativo" else "#5ccfe6"
            modo_label = "🏢 Corporativo" if modo_simulacion == "corporativo" else "🌐 Macro"
            st.markdown(
                f'<span class="badge" style="background:#1a2535;color:{modo_badge_color};'
                f'border:1px solid {modo_badge_color}">{modo_label}</span>',
                unsafe_allow_html=True,
            )

            with st.status(
                f"Arquitecto trabajando en modo **{modo_label}**... esto puede tomar un minuto.",
                expanded=True
            ) as status:
                st.write("Calculando simulaciones hipotéticas y escenarios de convergencia...")
                if metricas_red:
                    st.write(f"🔍 Métricas de red inyectadas en el prompt del LLM.")

                estrategia, narrativa, intentos, hist_inverso = buscar_estrategia_inversa(
                    estado_inicial=estado_inicial,
                    objetivo_usuario=objetivo,
                    max_intentos=3,
                    config=config_run,
                    modo_simulacion=modo_simulacion,
                    metricas_red=metricas_red,
                    use_langchain=usar_langchain_arq,
                )
                st.session_state["estr_inversa"] = {
                    "estrategia": estrategia,
                    "narrativa": narrativa,
                    "hist_inverso": hist_inverso,
                    "modo": modo_simulacion,
                }
                st.session_state["objetivo_inverso"] = objetivo
                status.update(
                    label=f"Estrategia encontrada en {intentos} iteraciones!",
                    state="complete",
                    expanded=False,
                )
                st.rerun()
        else:
            st.warning("Por favor, describe un objetivo.")

    if st.session_state["estr_inversa"]:
        data_inv = st.session_state["estr_inversa"]
        modo_inv = data_inv.get("modo", "macro")

        if not st.session_state["lead_captured"]:
            st.success("¡Estrategia calculada con éxito!")
            st.write("Para desbloquear el **Reporte Estratégico Completo** y la matriz de intervención, ingresa tu email corporativo.")
            with st.form("lead_form"):
                email = st.text_input("Email Corporativo:")
                submit = st.form_submit_button("🔓 Desbloquear Reporte")
                if submit and email:
                    with open("leads.csv", "a") as f:
                        f.write(email + "\n")
                    st.session_state["lead_captured"] = True
                    st.rerun()
        else:
            titulo_narrativa = (
                "📋 Reporte Ejecutivo de Cambio Organizacional"
                if modo_inv == "corporativo" else
                "🌐 Análisis de Clima Social"
            )
            st.subheader(titulo_narrativa)
            st.write(data_inv["narrativa"])

            if data_inv["hist_inverso"]:
                st.markdown("**Trayectoria de opinión (Estrategia Aplicada)** — *MASSIVE AI*")
                opiniones_inv = [h["opinion"] for h in data_inv["hist_inverso"]]
                df_data_inv = {"Opinión": opiniones_inv, "Neutro": [neutro] * len(opiniones_inv)}
                st.line_chart(pd.DataFrame(df_data_inv), color=["#5ccfe6", "#3d5166"])

                st.markdown("### Topología de Red Empírica")
                fig_net2 = generate_social_network_viz(
                    opiniones_inv[-1], 0.5,
                    amalgama=not es_bipolar, is_bipolar=es_bipolar
                )
                st.plotly_chart(fig_net2, use_container_width=True)

            # ── MATRIZ CON TARGET NODES RESALTADOS ───────────────
            st.subheader("Matriz de Intervención (Datos Técnicos)")
            estrategia_display = data_inv["estrategia"]
            # Resaltar fases con target_nodes en modo corporativo
            if modo_inv == "corporativo":
                fases_con_targets = [
                    f for f in estrategia_display.get("interventions", [])
                    if f.get("target_nodes") or (
                        isinstance(f.get("parameters", {}), dict)
                        and f["parameters"].get("target_nodes")
                    )
                ]
                if fases_con_targets:
                    st.markdown(
                        f"🎯 **{len(fases_con_targets)} fase(s) con intervención directa en nodos líderes.**"
                    )
            st.json(estrategia_display)

            report_text = (
                f"REPORTE EJECUTIVO - ARQUITECTO SOCIAL\n"
                f"Modo: {modo_inv.upper()}\n"
                f"Objetivo: {st.session_state['objetivo_inverso']}\n\n"
                f"{data_inv['narrativa']}\n\n"
                "MATRIZ:\n" + json.dumps(data_inv["estrategia"], indent=2) + "\n\n"
                + "-" * 50 + "\n"
                + "Generado con MASSIVE AI - Simulador de Redes Sociales.\n"
                + "Descubre más y obtén tu licencia en: https://github.com/Adlgr87/MASSIVE\n"
                + "-" * 50
            )
            st.download_button(
                "📥 Descargar Reporte Ejecutivo (TXT)",
                data=report_text,
                file_name=f"Reporte_MASSIVE_{modo_inv.capitalize()}.txt",
            )


# ------------------------------------------------------------
# TAB 3 — SIMULACIÓN MULTICAPA SOCIODEMOGRÁFICA
# Dinámica vectorial con capas de red diferenciadas y atributos
# sociodemográficos fijos por agente.
# ------------------------------------------------------------

with tab3:
    import plotly.graph_objects as go

    try:
        from multilayer_engine import (
            MultilayerEngine,
            generate_attributes,
            COL_OPINION,
            COL_COOP,
            K as ML_K,
        )
        _ML_AVAILABLE = True
    except ImportError as _ml_err:
        _ML_AVAILABLE = False
        st.error(f"multilayer_engine no disponible: {_ml_err}")

    if _ML_AVAILABLE:
        st.markdown("### 🌐 Simulador Social Multicapa")
        st.markdown(
            "Cada agente es un **vector de estado 5D** "
            "`(opinión, cooperación, jerarquía, ingreso, acceso_info)` "
            "que evoluciona sobre tres redes superpuestas — social, digital y económica — "
            "moduladas por atributos sociodemográficos fijos."
        )

        # ── Controles en columnas ─────────────────────────────────────────────
        ml_col1, ml_col2, ml_col3 = st.columns(3)

        with ml_col1:
            ml_n = st.slider("👥 Agentes (N)", 20, 500, 100, 10,
                             help="Número total de agentes en la simulación.")
            ml_steps = st.slider("⏱ Pasos", 50, 500, 150, 10)
            ml_dt = st.select_slider("Δt (paso de tiempo)", [0.001, 0.005, 0.01, 0.02, 0.05], value=0.01)

        with ml_col2:
            st.markdown("**Pesos de capa**")
            w_social   = st.slider("🤝 Social (Watts-Strogatz)",   0.0, 1.0, 0.4, 0.05)
            w_digital  = st.slider("📱 Digital (Libre de Escala)", 0.0, 1.0, 0.3, 0.05)
            w_economic = st.slider("💼 Económica (Jerárquica)",    0.0, 1.0, 0.3, 0.05)
            ml_coupling = st.slider("λ Acoplamiento social", 0.05, 1.0, 0.3, 0.05)

        with ml_col3:
            st.markdown("**Distribución de atributos**")
            pct_young = st.slider("% Jóvenes (18-35)",   0, 100, 30, 5)
            pct_mid   = st.slider("% Adultos (36-55)",   0, 100, 40, 5)
            pct_old   = 100 - pct_young - pct_mid
            pct_old   = max(0, pct_old)
            st.caption(f"→ Adultos mayores (56+): {pct_old}%")
            ml_religion  = st.slider("⛪ % Religiosos",  0, 100, 30, 5) / 100.0
            ml_edu_scale = st.slider("🎓 Escala educativa", 0.5, 1.5, 1.0, 0.1)
            ml_seed = st.number_input("🎲 Semilla", value=42, step=1)

        if pct_young + pct_mid > 100:
            st.warning(
                f"⚠️ La suma de jóvenes ({pct_young}%) + adultos ({pct_mid}%) "
                f"supera el 100%. Se ajusta el grupo mayor a 0%."
            )

        age_dist = (pct_young / 100.0, pct_mid / 100.0, pct_old / 100.0)
        total_w  = w_social + w_digital + w_economic
        layer_w  = (
            (w_social / total_w, w_digital / total_w, w_economic / total_w)
            if total_w > 0 else (0.4, 0.3, 0.3)
        )

        ml_run = st.button("🚀 Simular Multicapa", type="primary")

        if ml_run:
            with st.spinner("Simulando dinámica multicapa con Numba..."):
                engine = MultilayerEngine(
                    N=ml_n,
                    layer_weights=layer_w,
                    coupling=ml_coupling,
                    dt=ml_dt,
                    range_type="bipolar",
                    attr_config={
                        "age_dist":       age_dist,
                        "religion_prob":  ml_religion,
                        "education_scale": ml_edu_scale,
                    },
                    seed=int(ml_seed),
                )
                engine.run(steps=ml_steps)

            # ── Métricas finales ──────────────────────────────────────────────
            st.markdown("#### Métricas del paisaje social")
            landscape = engine.get_landscape()
            mc1, mc2, mc3, mc4 = st.columns(4)
            with mc1:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">Opinión media</div>
                    <div class="metric-value">{landscape['mean_opinion']:+.3f}</div>
                </div>""", unsafe_allow_html=True)
            with mc2:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">Polarización</div>
                    <div class="metric-value">{landscape['polarization']:.3f}</div>
                </div>""", unsafe_allow_html=True)
            with mc3:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">Cooperación media</div>
                    <div class="metric-value">{landscape['mean_cooperation']:.3f}</div>
                </div>""", unsafe_allow_html=True)
            with mc4:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">Jerarquía media</div>
                    <div class="metric-value">{landscape['mean_hierarchy']:.3f}</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            plot_c1, plot_c2 = st.columns(2)

            # ── Plot 1: Trayectorias por grupo etario ─────────────────────────
            with plot_c1:
                st.markdown("**Trayectoria de opinión por grupo etario**")
                traj_df = engine.trajectories_by_attribute("age_group")
                age_labels = {0: "Jóvenes (18-35)", 1: "Adultos (36-55)", 2: "Mayores (56+)"}
                age_colors = {0: "#5ccfe6", 1: "#bae67e", 2: "#c3a6ff"}
                fig_traj = go.Figure()
                for age_val in sorted(traj_df["age_group"].unique()):
                    sub = traj_df[traj_df["age_group"] == age_val]
                    fig_traj.add_trace(go.Scatter(
                        x=sub["step"], y=sub["mean_opinion"],
                        name=age_labels.get(int(age_val), str(age_val)),
                        line=dict(color=age_colors.get(int(age_val), "#ffffff"), width=2),
                    ))
                fig_traj.add_hline(y=0, line_dash="dot", line_color="#3d5166",
                                   annotation_text="neutro")
                fig_traj.update_layout(
                    template="plotly_dark", paper_bgcolor="#0a0e14",
                    plot_bgcolor="#0d1520", height=320,
                    xaxis_title="Paso", yaxis_title="Opinión media",
                    legend=dict(orientation="h", y=-0.3),
                    margin=dict(l=10, r=10, t=10, b=10),
                )
                st.plotly_chart(fig_traj, use_container_width=True)

            # ── Plot 2: Heatmap de correlaciones entre comportamientos ─────────
            with plot_c2:
                st.markdown("**Correlaciones entre comportamientos**")
                corr = engine.behavior_correlation_matrix()
                behavior_labels = ["Opinión", "Cooperación", "Jerarquía", "Ingreso", "Info"]
                fig_corr = go.Figure(go.Heatmap(
                    z=corr,
                    x=behavior_labels,
                    y=behavior_labels,
                    colorscale="RdBu",
                    zmid=0, zmin=-1, zmax=1,
                    text=np.round(corr, 2),
                    texttemplate="%{text}",
                    showscale=True,
                ))
                fig_corr.update_layout(
                    template="plotly_dark", paper_bgcolor="#0a0e14",
                    plot_bgcolor="#0d1520", height=320,
                    margin=dict(l=10, r=10, t=10, b=10),
                )
                st.plotly_chart(fig_corr, use_container_width=True)

            # ── Plot 3: Paisaje 2D opinión vs cooperación ─────────────────────
            st.markdown("**Paisaje 2D: Opinión × Cooperación (estado final)**")
            attrs_df = engine.attributes_df
            age_arr  = attrs_df["age_group"].to_numpy()
            rel_arr  = attrs_df["religion"].to_numpy()
            fig_land = go.Figure()

            group_cfg = [
                (age_arr == 0, "#5ccfe6", "Jóvenes"),
                (age_arr == 1, "#bae67e", "Adultos"),
                (age_arr == 2, "#c3a6ff", "Mayores"),
            ]
            for mask, color, label in group_cfg:
                if mask.sum() > 0:
                    fig_land.add_trace(go.Scatter(
                        x=engine.x[mask, COL_OPINION],
                        y=engine.x[mask, COL_COOP],
                        mode="markers",
                        name=label,
                        marker=dict(color=color, size=5, opacity=0.6),
                    ))

            fig_land.update_layout(
                template="plotly_dark", paper_bgcolor="#0a0e14",
                plot_bgcolor="#0d1520", height=380,
                xaxis_title="Opinión", yaxis_title="Cooperación",
                xaxis=dict(range=[-1.05, 1.05]),
                yaxis=dict(range=[-0.05, 1.05]),
                legend=dict(orientation="h", y=-0.2),
                margin=dict(l=10, r=10, t=10, b=10),
            )
            st.plotly_chart(fig_land, use_container_width=True)

            # ── LLM bias dirigido ─────────────────────────────────────────────
            with st.expander("🎯 Narrativa LLM dirigida a segmento demográfico"):
                from multilayer_engine import targeted_llm_bias
                bias_layer = st.selectbox(
                    "Capa objetivo", ["digital", "social", "economic"], key="ml_bias_layer"
                )
                bias_demo  = st.selectbox(
                    "Grupo demográfico", [
                        "religion=1", "religion=0",
                        "age_group=0", "age_group=2",
                        "gender=1", "gender=0",
                    ], key="ml_bias_demo"
                )
                if st.button("Generar narrativa", key="ml_bias_btn"):
                    with st.spinner("Generando argumento..."):
                        narrative = targeted_llm_bias(
                            layer_target=bias_layer,
                            demographic=bias_demo,
                            proveedor=proveedor,
                            modelo=modelo,
                        )
                    st.success(narrative)

            # ── Exportar datos multicapa ──────────────────────────────────────
            with st.expander("⬇️ Exportar datos multicapa"):
                final_df = pd.DataFrame(engine.x, columns=["opinion", "cooperation",
                                                            "hierarchy", "income", "info_access"])
                final_df = pd.concat([final_df, engine.attributes_df.reset_index(drop=True)], axis=1)
                st.dataframe(final_df, use_container_width=True)
                st.download_button("⬇ CSV Estado Final",
                                   data=final_df.to_csv(index=False),
                                   file_name="massive_multilayer.csv",
                                   mime="text/csv")

        else:
            st.markdown("""
            <div style="border:1px dashed #1a2535;border-radius:4px;padding:48px;text-align:center;margin-top:2rem;">
                <div style="font-family:'IBM Plex Mono',monospace;color:#3d5166;font-size:0.8rem;letter-spacing:2px;">
                    CONFIGURA LAS CAPAS Y PULSA · SIMULAR MULTICAPA ·
                </div>
            </div>""", unsafe_allow_html=True)

            with st.expander("📖 ¿Qué es la Simulación Multicapa?"):
                st.markdown("""
**Vector de estado por agente** `x_i ∈ ℝ⁵`:

| Columna | Variable | Rango |
|---------|----------|-------|
| 0 | Opinión (s_i) | [-1, 1] |
| 1 | Cooperación (c_i) | [0, 1] |
| 2 | Jerarquía (h_i) | [0, 1] |
| 3 | Ingreso (y_i) | [0, 1] |
| 4 | Acceso a información (φ_i) | [0, 1] |

**Tres capas de red superpuestas**:
- 🤝 **Social** (Watts-Strogatz): red de mundo pequeño — contactos cara a cara.
- 📱 **Digital** (Barabási-Albert): red libre de escala — redes sociales y medios virales.
- 💼 **Económica** (Jerárquica): flujo de autoridad descendente — mercados y empleo.

**Modulación por atributos**: la matriz θ(a_i) amplifica el ruido de cada agente
según su religiosidad, educación y edad, reproduciendo la heterogeneidad real de
las sociedades complejas.
                """)


# ------------------------------------------------------------
# TAB 4 — SIMULACIÓN MASIVA
# Motor de escala masiva con 4 estrategias de eficiencia:
#   1. LOD (Super-Agentes): N agentes → M clústeres
#   2. Cuantización uint8: ~87.5% menos RAM
#   3. Event-Driven: solo procesa clústeres activos
#   4. GPU offloading (CuPy/PyTorch si disponibles)
# ------------------------------------------------------------

with tab4:
    try:
        from massive_engine import MassiveSimEngine, _GPU_BACKEND
        _MASSIVE_AVAILABLE = True
    except ImportError as _me_err:
        _MASSIVE_AVAILABLE = False
        st.error(f"massive_engine no disponible: {_me_err}")

    if _MASSIVE_AVAILABLE:
        st.markdown("### ⚡ Simulación Masiva — Millones de Agentes")
        st.markdown(
            "Simula desde **10 000 hasta 1 000 000+ agentes** usando cuatro estrategias de "
            "eficiencia combinadas: representación LOD por super-agentes, cuantización uint8, "
            "actualización dirigida por eventos y aceleración GPU opcional."
        )

        # ── Badge GPU ─────────────────────────────────────────────────────────
        gpu_color = "#bae67e" if _GPU_BACKEND != "numpy" else "#3d5166"
        gpu_label = f"GPU: {_GPU_BACKEND}" if _GPU_BACKEND != "numpy" else "CPU (numpy) · GPU no detectada"
        st.markdown(
            f'<span class="badge" style="background:#0d1520;color:{gpu_color};border:1px solid {gpu_color}">'
            f'🖥 {gpu_label}</span>',
            unsafe_allow_html=True,
        )

        # ── Controles ─────────────────────────────────────────────────────────
        ms_col1, ms_col2, ms_col3 = st.columns(3)

        with ms_col1:
            st.markdown("**Escala**")
            ms_N = st.select_slider(
                "👥 Agentes (N)",
                options=[10_000, 25_000, 50_000, 100_000, 250_000, 500_000, 1_000_000],
                value=100_000,
                help="Número de agentes reales representados por los super-agentes.",
            )
            ms_M_auto = st.toggle("Auto M (√N)", value=True,
                                  help="M se calcula como max(50, √N) — recomendado.")
            if ms_M_auto:
                ms_M = max(50, int(ms_N ** 0.5))
                st.caption(f"→ M = {ms_M} super-agentes")
            else:
                ms_M = st.slider("🔵 Super-agentes (M)", 50, 500, 200, 10)
            ms_steps = st.slider("⏱ Pasos", 50, 500, 200, 10)

        with ms_col2:
            st.markdown("**Estrategias de eficiencia**")
            ms_quantize = st.toggle(
                "📦 Cuantización uint8",
                value=True,
                help="Almacena el estado en 1 byte/parámetro. ~87.5% menos RAM que float64.",
            )
            ms_event = st.toggle(
                "⚡ Event-Driven",
                value=True,
                help="Solo procesa super-agentes con cambios significativos. Ahorra CPU.",
            )
            ms_sleep_thr = st.select_slider(
                "Umbral de 'sueño'",
                options=[1e-4, 5e-4, 1e-3, 5e-3, 1e-2],
                value=5e-3,
                format_func=lambda v: f"{v:.0e}",
                help="Cambio mínimo para considerar activo a un super-agente.",
            )
            ms_use_gpu = st.toggle(
                f"🖥 GPU ({_GPU_BACKEND})",
                value=_GPU_BACKEND != "numpy",
                disabled=_GPU_BACKEND == "numpy",
                help="Usa CuPy o PyTorch para operaciones matriciales en GPU.",
            )

        with ms_col3:
            st.markdown("**Parámetros de red**")
            ms_w_s = st.slider("🤝 Peso Social",    0.0, 1.0, 0.4, 0.05)
            ms_w_d = st.slider("📱 Peso Digital",   0.0, 1.0, 0.3, 0.05)
            ms_w_e = st.slider("💼 Peso Económico", 0.0, 1.0, 0.3, 0.05)
            ms_coupling = st.slider("λ Acoplamiento", 0.05, 1.0, 0.3, 0.05)
            ms_dt = st.select_slider("Δt", [0.001, 0.005, 0.01, 0.02, 0.05], value=0.01)
            ms_seed = st.number_input("🎲 Semilla", value=42, step=1)

        ms_run = st.button("🚀 Simular Masiva", type="primary")

        # ── Preview de ahorro de memoria ──────────────────────────────────────
        float64_MB = ms_N * 5 * 8 / 1e6
        lod_MB     = ms_M * 5 * 8 / 1e6
        final_MB   = ms_M * 5 * 1 / 1e6 if ms_quantize else lod_MB
        savings_pct = (1.0 - final_MB / float64_MB) * 100.0

        prev_c1, prev_c2, prev_c3 = st.columns(3)
        with prev_c1:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-label">RAM sin optimizar</div>
                <div class="metric-value">{float64_MB:.1f} MB</div>
                <div class="metric-delta-neu">N={ms_N:,} × 5 dim × float64</div>
            </div>""", unsafe_allow_html=True)
        with prev_c2:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-label">RAM con LOD</div>
                <div class="metric-value">{lod_MB:.2f} MB</div>
                <div class="metric-delta-pos">M={ms_M} clústeres × float64</div>
            </div>""", unsafe_allow_html=True)
        with prev_c3:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-label">RAM final estimada</div>
                <div class="metric-value">{final_MB:.3f} MB</div>
                <div class="metric-delta-pos">▼ {savings_pct:.1f}% vs naive</div>
            </div>""", unsafe_allow_html=True)

        if ms_run:
            total_w = ms_w_s + ms_w_d + ms_w_e
            layer_w = (
                (ms_w_s / total_w, ms_w_d / total_w, ms_w_e / total_w)
                if total_w > 0 else (0.4, 0.3, 0.3)
            )

            with st.spinner(f"Simulando {ms_N:,} agentes en {ms_M} clústeres..."):
                ms_engine = MassiveSimEngine(
                    N=ms_N,
                    M=ms_M,
                    quantize=ms_quantize,
                    event_driven=ms_event,
                    sleep_threshold=float(ms_sleep_thr),
                    use_gpu=ms_use_gpu,
                    layer_weights=layer_w,
                    coupling=ms_coupling,
                    dt=ms_dt,
                    seed=int(ms_seed),
                )
                ms_result = ms_engine.run(steps=ms_steps)

            # ── Métricas de resultado ─────────────────────────────────────────
            st.markdown("#### Resultados de la simulación masiva")
            rc1, rc2, rc3, rc4 = st.columns(4)
            with rc1:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">Opinión media final</div>
                    <div class="metric-value">{ms_result['mean_opinion']:+.3f}</div>
                    <div class="metric-delta-neu">σ = {ms_result['std_opinion']:.3f}</div>
                </div>""", unsafe_allow_html=True)
            with rc2:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">Polarización</div>
                    <div class="metric-value">{ms_result['polarization']:.3f}</div>
                    <div class="metric-delta-neu">|opinión| media</div>
                </div>""", unsafe_allow_html=True)
            with rc3:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">Velocidad</div>
                    <div class="metric-value">{ms_result['steps_per_second']:.0f}</div>
                    <div class="metric-delta-pos">pasos/segundo</div>
                </div>""", unsafe_allow_html=True)
            with rc4:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">Ahorro RAM real</div>
                    <div class="metric-value">{ms_result['memory_savings_pct']:.1f}%</div>
                    <div class="metric-delta-pos">vs float64 naive</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Badges de estrategias activas ─────────────────────────────────
            badge_colors = {
                "LOD (Super-Agentes)": "#5ccfe6",
                "Cuantización uint8":  "#bae67e",
                "Event-Driven":        "#ff8f40",
            }
            badges_ms = []
            for strat in ms_result.get("strategies_active", []):
                color = badge_colors.get(strat, "#c3a6ff")
                badges_ms.append(
                    f'<span class="badge" style="background:#0d1520;color:{color};'
                    f'border:1px solid {color}">{strat}</span>'
                )
            if badges_ms:
                st.markdown(" ".join(badges_ms), unsafe_allow_html=True)

            # ── Gráficos ──────────────────────────────────────────────────────
            plot_m1, plot_m2 = st.columns(2)

            with plot_m1:
                st.markdown("**Trayectoria de opinión media (ponderada por clúster)**")
                opinion_hist = ms_result["opinion_history"]
                fig_ms_op = go.Figure()
                fig_ms_op.add_trace(go.Scatter(
                    y=opinion_hist,
                    name="Opinión media",
                    line=dict(color="#5ccfe6", width=2),
                ))
                fig_ms_op.add_hline(y=0, line_dash="dot", line_color="#3d5166",
                                    annotation_text="neutro")
                fig_ms_op.update_layout(
                    template="plotly_dark", paper_bgcolor="#0a0e14",
                    plot_bgcolor="#0d1520", height=300,
                    xaxis_title="Paso", yaxis_title="Opinión media",
                    margin=dict(l=10, r=10, t=10, b=10),
                )
                st.plotly_chart(fig_ms_op, use_container_width=True)

            with plot_m2:
                if ms_event:
                    st.markdown("**Fracción de super-agentes activos por paso**")
                    active_hist = ms_result["active_history"]
                    fig_ms_act = go.Figure()
                    fig_ms_act.add_trace(go.Scatter(
                        y=active_hist * 100,
                        name="% Activos",
                        fill="tozeroy",
                        line=dict(color="#ff8f40", width=1.5),
                    ))
                    fig_ms_act.update_layout(
                        template="plotly_dark", paper_bgcolor="#0a0e14",
                        plot_bgcolor="#0d1520", height=300,
                        xaxis_title="Paso", yaxis_title="% Super-agentes activos",
                        yaxis=dict(range=[0, 105]),
                        margin=dict(l=10, r=10, t=10, b=10),
                    )
                    st.plotly_chart(fig_ms_act, use_container_width=True)
                else:
                    st.info("Activa Event-Driven para ver la evolución de agentes activos.")

            # ── Distribución final de opinión entre clústeres ─────────────────
            st.markdown("**Distribución de opinión entre super-agentes (estado final)**")
            cluster_ops = ms_result["cluster_opinions"]
            cluster_cnts = ms_result["cluster_counts"]

            fig_hist = go.Figure()
            fig_hist.add_trace(go.Histogram(
                x=cluster_ops,
                nbinsx=30,
                name="Clústeres",
                marker_color="#5ccfe6",
                opacity=0.75,
            ))
            fig_hist.update_layout(
                template="plotly_dark", paper_bgcolor="#0a0e14",
                plot_bgcolor="#0d1520", height=280,
                xaxis_title="Opinión del super-agente",
                yaxis_title="Nº de clústeres",
                xaxis=dict(range=[-1.05, 1.05]),
                margin=dict(l=10, r=10, t=10, b=10),
            )
            st.plotly_chart(fig_hist, use_container_width=True)

            # ── Shock externo ─────────────────────────────────────────────────
            with st.expander("💥 Aplicar Shock Externo (perturbación masiva)"):
                st.markdown(
                    "Simula un evento externo — noticia viral, crisis económica, cambio político — "
                    "que perturba la opinión de una fracción de la red y reactiva clústeres dormidos."
                )
                sc1, sc2 = st.columns(2)
                with sc1:
                    shock_val = st.slider("Intensidad del shock", -1.0, 1.0, 0.3, 0.05)
                    shock_frac = st.slider("Fracción de agentes afectados", 0.05, 1.0, 0.2, 0.05)
                if st.button("⚡ Aplicar shock y re-simular"):
                    ms_engine.apply_shock(shock_value=shock_val, fraction=shock_frac)
                    with st.spinner("Re-simulando tras el shock..."):
                        ms_result2 = ms_engine.run(steps=ms_steps // 2)
                    st.success(
                        f"Shock aplicado. Opinión post-shock: "
                        f"{ms_result2['mean_opinion']:+.3f} "
                        f"(era {ms_result['mean_opinion']:+.3f})"
                    )
                    post_hist = ms_result2["opinion_history"]
                    fig_post = go.Figure()
                    fig_post.add_trace(go.Scatter(
                        y=post_hist, name="Post-shock",
                        line=dict(color="#c3a6ff", width=2),
                    ))
                    fig_post.add_hline(y=0, line_dash="dot", line_color="#3d5166")
                    fig_post.update_layout(
                        template="plotly_dark", paper_bgcolor="#0a0e14",
                        plot_bgcolor="#0d1520", height=250,
                        xaxis_title="Paso", yaxis_title="Opinión media",
                        margin=dict(l=10, r=10, t=10, b=10),
                    )
                    st.plotly_chart(fig_post, use_container_width=True)

            # ── Exportar datos masivos ────────────────────────────────────────
            with st.expander("⬇️ Exportar datos de simulación masiva"):
                df_ms = pd.DataFrame({
                    "cluster_id":      range(ms_M),
                    "opinion_final":   ms_result["cluster_opinions"],
                    "n_agents":        ms_result["cluster_counts"],
                })
                st.dataframe(df_ms, use_container_width=True)
                st.download_button(
                    "⬇ CSV Clústeres",
                    data=df_ms.to_csv(index=False),
                    file_name="massive_masiva.csv",
                    mime="text/csv",
                )

        else:
            st.markdown("""
            <div style="border:1px dashed #1a2535;border-radius:4px;padding:48px;text-align:center;margin-top:2rem;">
                <div style="font-family:'IBM Plex Mono',monospace;color:#3d5166;font-size:0.8rem;letter-spacing:2px;">
                    CONFIGURA LA ESCALA Y LAS ESTRATEGIAS · PULSA ⚡ SIMULAR MASIVA ·
                </div>
            </div>""", unsafe_allow_html=True)

            with st.expander("📖 ¿Cómo funciona la Simulación Masiva?"):
                st.markdown("""
**4 estrategias de eficiencia integradas:**

| # | Estrategia | Ahorro | Cómo funciona |
|---|---|---|---|
| 1 | **LOD — Super-Agentes** | O(N²→M²) menos RAM | N agentes → M clústeres representativos. Solo se simula la dinámica de M centros. |
| 2 | **Cuantización uint8** | ~87.5% menos RAM | Estado almacenado en 1 byte/parámetro vs 8 bytes float64. Resolución ≈ 0.008. |
| 3 | **Event-Driven** | Variable en CPU | Solo los super-agentes con cambios significativos se actualizan. Los demás duermen. |
| 4 | **GPU Offloading** | 10-100× en velocidad | Si CuPy o PyTorch+CUDA está disponible, las multiplicaciones matriciales van a GPU. |

**Ejemplo de ahorro combinado:**
- N = 1 000 000 agentes, K = 5 dimensiones, float64
- Sin optimizar: 1M × 5 × 8 bytes = **40 MB**
- Con LOD (M=316) + uint8: 316 × 5 × 1 byte = **~1.6 KB** — ahorro del **99.996%**

**¿Cuándo usar cada modo?**
- Hasta N=10 000: Simulación Multicapa (Tab 3) — precisión completa por agente.
- N=10 000 – 1 000 000: Simulación Masiva — estadísticas de clúster, eficiencia máxima.
- Shock externo: perturba la red en caliente y observa la respuesta de los clústeres dormidos.
                """)


with tab5:
    st.markdown("### 🎬 Centro Analítico de Dinámica Social")
    st.markdown(
        "Panel profesional para analizar contagio, polarización y cambios de régimen "
        "sobre la última simulación tradicional ejecutada."
    )

    sim_data = st.session_state.get("last_simulation")
    if not sim_data:
        st.info("Ejecuta primero una simulación en la pestaña **Simulación Tradicional** para habilitar este panel.")
    else:
        historial = sim_data["historial"]
        neutro = sim_data["neutro"]
        es_bipolar = sim_data["is_bipolar"]

        steps = [int(h.get("_paso", idx)) for idx, h in enumerate(historial)]
        opinions = np.array([float(h.get("opinion", 0.0)) for h in historial], dtype=float)
        polar_proxy = np.abs(opinions - neutro)
        contagion_proxy = np.array([
            float(
                h.get("_sir_I")
                if "_sir_I" in h
                else h.get("_fraccion_adoptantes", 0.0)
            )
            for h in historial
        ], dtype=float)

        selected_idx = st.slider(
            "Selecciona el paso a inspeccionar",
            min_value=0,
            max_value=len(historial) - 1,
            value=len(historial) - 1,
            step=1,
        )
        selected_state = historial[selected_idx]
        selected_step = steps[selected_idx]

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Paso", selected_step)
        with m2:
            st.metric("Opinión", f"{selected_state.get('opinion', 0.0):+.3f}")
        with m3:
            st.metric("Confianza", f"{selected_state.get('confianza', 0.0):.3f}")
        with m4:
            st.metric("Polarización (proxy)", f"{polar_proxy[selected_idx]:.3f}")

        fig_anim = go.Figure(
            data=[
                go.Scatter(x=[steps[0]], y=[opinions[0]], name="Opinión", line=dict(color="#5ccfe6", width=2)),
                go.Scatter(x=[steps[0]], y=[polar_proxy[0]], name="Polarización", line=dict(color="#ff8f40", width=2)),
                go.Scatter(x=[steps[0]], y=[contagion_proxy[0]], name="Contagio", line=dict(color="#bae67e", width=2)),
            ],
            frames=[
                go.Frame(
                    data=[
                        go.Scatter(x=steps[: i + 1], y=opinions[: i + 1]),
                        go.Scatter(x=steps[: i + 1], y=polar_proxy[: i + 1]),
                        go.Scatter(x=steps[: i + 1], y=contagion_proxy[: i + 1]),
                    ],
                    name=str(i),
                )
                for i in range(len(steps))
            ],
        )
        fig_anim.add_hline(y=neutro, line_dash="dot", line_color="#3d5166")
        fig_anim.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0a0e14",
            plot_bgcolor="#0d1520",
            height=420,
            xaxis_title="Paso",
            yaxis_title="Intensidad",
            margin=dict(l=10, r=10, t=10, b=10),
            updatemenus=[{
                "type": "buttons",
                "direction": "left",
                "x": 0,
                "y": 1.12,
                "buttons": [
                    {
                        "label": "▶ Play",
                        "method": "animate",
                        "args": [None, {"frame": {"duration": ANALYTICS_ANIMATION_FRAME_MS, "redraw": True}, "fromcurrent": True}],
                    },
                    {
                        "label": "⏸ Pause",
                        "method": "animate",
                        "args": [[None], {"frame": {"duration": ANALYTICS_ANIMATION_PAUSE_MS, "redraw": False}, "mode": "immediate"}],
                    },
                ],
            }],
            sliders=[{
                "active": selected_idx,
                "steps": [
                    {
                        "label": str(steps[i]),
                        "method": "animate",
                        "args": [[str(i)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
                    }
                    for i in range(len(steps))
                ],
            }],
        )
        st.plotly_chart(fig_anim, use_container_width=True)

        st.markdown("#### Topología de red en el paso seleccionado")
        fig_network = generate_social_network_viz(
            selected_state.get("opinion", 0.0),
            float(selected_state.get("confianza", 0.5)),
            amalgama=not es_bipolar,
            is_bipolar=es_bipolar,
        )
        st.plotly_chart(fig_network, use_container_width=True)

        regime_changes = []
        previous_rule = None
        for item in historial:
            rule = item.get("_regla_nombre", "")
            if rule and rule != previous_rule:
                regime_changes.append(
                    {
                        "paso": int(item.get("_paso", 0)),
                        "regla": rule,
                        "razon": item.get("_razon", "—"),
                    }
                )
            previous_rule = rule or previous_rule

        st.markdown("#### Eventos de cambio de régimen")
        if regime_changes:
            st.dataframe(pd.DataFrame(regime_changes), use_container_width=True, hide_index=True)
        else:
            st.caption("No se detectaron cambios de régimen en la simulación actual.")


with tab6:
    render_micro_tab()


# ────────────────────────────────────────────────────────────────────────────
# UIL INTEGRATION TAB — Document Intelligence + Interpreter Layer
# ────────────────────────────────────────────────────────────────────────────
if _UIL_AVAILABLE and tab_uil is not None:
    with tab_uil:
        st.markdown("### 📄 Inteligencia Documental & Interpretación Natural")
        st.caption(
            "Carga un documento o describe tu escenario en lenguaje natural. "
            "Los módulos extraerán parámetros MASSIVE automáticamente."
        )

        # Input options
        uil_mode = st.radio(
            "Modo de entrada",
            ["📝 Documento", "💬 Descripción natural", "🔀 Ambos"],
            horizontal=True,
        )

        config_from_uil = {}

        # Mode 1: Document only
        if uil_mode in ["📝 Documento", "🔀 Ambos"]:
            st.subheader("📄 Carga de Documento")
            uploaded_file = st.file_uploader(
                "Sube un PDF, JSON, CSV o XLSX",
                type=["pdf", "json", "csv", "xlsx"],
                key="uil_file",
            )
            if uploaded_file:
                # Save to temp
                import tempfile

                with tempfile.NamedTemporaryFile(delete=False, suffix="." + uploaded_file.name.split(".")[-1]) as tmp:
                    tmp.write(uploaded_file.getbuffer())
                    tmp_path = tmp.name

                st.success(f"✓ Archivo cargado: {uploaded_file.name}")
                with st.spinner("Extrayendo parámetros del documento..."):
                    try:
                        from uil_adapter import create_uil_adapter

                        adapter = create_uil_adapter(llm_provider=proveedor, llm_api_key=api_key)
                        config_from_uil = adapter.from_document(tmp_path)
                        st.success(f"✓ Extraídos {len(config_from_uil)} parámetros del documento")
                        with st.expander("Ver parámetros extraídos"):
                            st.json(config_from_uil)
                    except Exception as e:
                        st.error(f"Error extrayendo documento: {e}")

        # Mode 2: Natural language only
        if uil_mode in ["💬 Descripción natural", "🔀 Ambos"]:
            st.subheader("💬 Descripción del Escenario")
            description = st.text_area(
                "Describe tu escenario en lenguaje natural (ej: 'Alta polarización, desconfianza institucional')",
                height=100,
                key="uil_description",
            )
            if description:
                with st.spinner("Interpretando descripción..."):
                    try:
                        from uil_adapter import create_uil_adapter

                        adapter = create_uil_adapter(llm_provider=proveedor, llm_api_key=api_key)
                        config_from_uil = adapter.from_natural_language(description)
                        st.success(f"✓ Interpretados {len(config_from_uil)} parámetros")
                        with st.expander("Ver parámetros interpretados"):
                            st.json(config_from_uil)
                    except Exception as e:
                        st.error(f"Error interpretando: {e}")

        st.markdown("---")

        # Simulate with UIL config
        if st.button("🚀 Simular con parámetros UIL", key="uil_simulate"):
            if not config_from_uil:
                st.warning("Primero carga un documento o describe un escenario")
            else:
                # Merge with defaults, filtering None UIL values
                filtered_uil = {k: v for k, v in config_from_uil.items() if v is not None}
                final_config = {**DEFAULT_CONFIG, **filtered_uil}

                with st.spinner(f"Simulando con parámetros UIL ({n_pasos} pasos)..."):
                    try:
                        historial = simular(pasos=n_pasos, **final_config)
                        st.success(f"✓ Simulación completada ({len(historial)} pasos)")

                        # Show results
                        st.subheader("Resultados de la Simulación UIL")

                        col1, col2 = st.columns(2)
                        with col1:
                            opinion_final = historial[-1].get("opinion", 0)
                            st.metric("Opinión Final", f"{opinion_final:.3f}")

                        with col2:
                            conf_final = historial[-1].get("confianza", 0.5)
                            st.metric("Confianza Final", f"{conf_final:.3f}")

                        # Narrative summary
                        with st.expander("📖 Resumen Narrativo"):
                            try:
                                from uil_adapter import create_uil_adapter

                                adapter = create_uil_adapter(llm_provider=proveedor, llm_api_key=api_key)
                                narrative = adapter.interpreter.narrate(historial)
                                st.write(
                                    narrative.narrative
                                    if hasattr(narrative, "narrative")
                                    else str(narrative)
                                )
                            except Exception as e:
                                st.caption(f"No se pudo generar narrativa: {e}")

                        # Timeline chart
                        st.subheader("Evolución de la Opinión")
                        df = pd.DataFrame(historial)
                        if "opinion" in df.columns:
                            fig = go.Figure()
                            fig.add_trace(
                                go.Scatter(
                                    x=df.index,
                                    y=df["opinion"],
                                    mode="lines+markers",
                                    name="Opinión",
                                    line=dict(color="#5ccfe6", width=2),
                                )
                            )
                            fig.update_layout(
                                template="plotly_dark",
                                paper_bgcolor="#0a0e14",
                                plot_bgcolor="#0d1520",
                                title="Trayectoria de Opinión",
                                xaxis_title="Paso",
                                yaxis_title="Opinión",
                            )
                            st.plotly_chart(fig, use_container_width=True)

                    except Exception as e:
                        st.error(f"Error en la simulación: {e}")
else:
    st.caption("📄 Pestaña Document Intelligence no disponible (módulos UIL no instalados)")
