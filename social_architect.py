"""
MASSIVE — Social Architect Agent (Inverse Mode)
LLM iterativo que busca la secuencia de intervenciones matemáticas
que lleva la red a un estado objetivo.

Soporta dos modos:
  - "macro"       → política, redes sociales masivas, polarización pública
  - "corporativo" → RRHH, cambio organizacional, líderes formales/informales
"""
import json
import logging
import os
from openai import OpenAI
from pydantic import ValidationError

from schemas import StrategyMatrix
from simulator import run_with_schedule, resumen_historial, DEFAULT_CONFIG
from quantum.integration import quantum_optimize_interventions

log = logging.getLogger("massive")


def find_optimal_interventions(evaluate_fn, n_agents, n_phases, max_iter=100):
    """Drop-in replacement para optimización de intervenciones."""
    return quantum_optimize_interventions(
        evaluate_fn=evaluate_fn,
        n_agents=n_agents,
        n_phases=n_phases,
        max_iter=max_iter,
    )


# ============================================================
# CLIENTE LLM
# ============================================================

def setup_client():
    """Inicializa el cliente OpenAI-compatible con la key disponible."""
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    if not api_key:
        api_key = os.getenv("GROQ_API_KEY")
        base_url = "https://api.groq.com/openai/v1"
    if not api_key:
        api_key = os.getenv("OPENROUTER_API_KEY")
        base_url = "https://openrouter.ai/api/v1"

    if not api_key:
        return OpenAI()  # Variables de entorno por defecto del usuario
    return OpenAI(api_key=api_key, base_url=base_url)


# ============================================================
# EVALUADOR DE RESULTADOS
# ============================================================

def evaluar_resultado(historial, objetivo_usuario, config):
    """
    Calcula un score (0 a 100) y genera texto de feedback para el LLM.

    Args:
        historial: Lista de estados de la simulación.
        objetivo_usuario: Texto del objetivo ingresado.
        config: Configuración global.

    Returns:
        Tupla (score: float, feedback: str).
    """
    stats = resumen_historial(historial, config)
    polarizacion = stats["polarizacion_media"]
    delta = stats["delta_total"]

    estado_final = (
        f"Opinión Inicial={stats['opinion_inicial']:.3f}, "
        f"Opinión Final={stats['opinion_final']:.3f}, Delta={delta:+.3f}, "
        f"Polarización Media={polarizacion:.3f}, Varianza={stats['desviacion']:.3f}. "
    )

    obj_lower = objetivo_usuario.lower()
    if any(palabra in obj_lower for palabra in ["consenso", "despolarizar", "apaciguar", "alinear", "cohesión"]):
        score = max(0, min(100, 100 - (polarizacion * 100 * 2)))
        if stats['desviacion'] < 0.15:
            score += 20
    elif any(palabra in obj_lower for palabra in ["polariza", "dividir"]):
        score = min(100, polarizacion * 100 * 2)
    else:
        score = 80 if abs(delta) > 0.05 else 40

    score = min(100, max(0, score))

    feedback = estado_final
    if score >= 90:
        feedback += "¡Éxito! La red convergió según el objetivo buscado."
    else:
        feedback += f"El resultado fue {score:.1f}%. Ajuste insuficiente. "
        if polarizacion > 0.2:
            feedback += (
                "La red sigue muy polarizada "
                "(intenta usar HK con epsilon mayor o memoria para estabilizar). "
            )
        if abs(delta) < 0.05:
            feedback += (
                "La opinión apenas se movió "
                "(aumenta el impacto de umbrales u homofilia o la influencia de la regla)."
            )

    return score, feedback


# ============================================================
# CONSTRUCTORES DE SISTEMA DE PROMPTS — conscientes del modo
# ============================================================

def _system_prompt_macro() -> str:
    return (
        "Eres el Arquitecto de Simulación: experto en estrategia política, "
        "comunicación pública y dinámica de redes sociales masivas. "
        "Tu misión es diseñar campañas de intervención para mover la opinión pública, "
        "gestionar la polarización y generar o disolver movimientos sociales. "
        "Habla en términos de campañas mediáticas, discurso político, hashtags virales, "
        "cámaras de eco, influencers y polarización electoral."
    )


def _system_prompt_corporativo(metricas_red: str) -> str:
    return (
        "Eres el Arquitecto de Simulación: experto en Recursos Humanos, "
        "gestión del cambio organizacional y comunicación interna corporativa. "
        "Tu misión es diseñar intervenciones precisas para transformar la cultura, "
        "alinear equipos y navegar reestructuraciones dentro de la empresa. "
        "Usa vocabulario de RRHH: líderes informales, reuniones interdepartamentales, "
        "comunicación top-down, resistencia al cambio, cohesión de equipo, "
        "planes de acción 30-60-90 días y alineación con OKRs.\n\n"
        f"Contexto de la red organizacional actual:\n{metricas_red}\n\n"
        "IMPORTANTE: Para las intervenciones donde sea relevante, incluye en 'parameters' "
        "el campo 'target_nodes' con una lista de IDs de los nodos líderes a impactar primero "
        "(máximo 3 nodos). Prioriza los líderes informales (betweenness alto) antes que "
        "los directivos formales (degree alto)."
    )


def _user_prompt_inverso(
    estado_inicial: dict,
    objetivo_usuario: str,
    historial_feedback: list,
    modo_simulacion: str,
    metricas_red: str,
) -> str:
    """
    Construye el prompt de usuario para busqueda de estrategia inversa.
    Adapta el contexto y el vocabulario según el modo.
    """
    contexto_modo = ""
    if modo_simulacion == "corporativo":
        contexto_modo = (
            "\n\nMODO CORPORATIVO ACTIVO: Las intervenciones deben reflejar "
            "acciones organizacionales reales (talleres, 1:1 con líderes, "
            "comunicados internos, rediseño de reuniones). "
            f"\nMétricas actuales de la red: {metricas_red}"
        )
    else:
        contexto_modo = (
            "\n\nMODO MACRO ACTIVO: Las intervenciones deben reflejar "
            "eventos del mundo real (campañas de medios, discursos políticos, "
            "trending topics, regulaciones, referéndums)."
        )

    return f"""
Estado inicial de la red: {json.dumps(estado_inicial)}
Objetivo Deseado: {objetivo_usuario}{contexto_modo}

Debes generar una programación de intervenciones matemáticas en pasos de tiempo progresivos.
Modelos permitidos: 'lineal', 'umbral', 'memoria', 'backlash', 'polarizacion',
'hk', 'contagio_competitivo', 'umbral_heterogeneo', 'homofilia'.

Intentos previos y sus fallos: {json.dumps(historial_feedback)}

Responde extrayendo tus fases estructurales estrictamente en un JSON con esta estructura exacta:
{{
    "interventions": [
        {{
            "time_start": 1,
            "time_end": 10,
            "model_name": "hk",
            "parameters": {{"epsilon": 0.5}},
            "fase_rationale": "Justificación clara y contextualizada",
            "target_nodes": null
        }}
    ]
}}

Nota: En modo corporativo, si la fase debe impactar líderes específicos,
usa "target_nodes": ["NodoA", "NodoC"] en lugar de null.
"""


# ============================================================
# NARRATIVA FINAL — consciente del modo
# ============================================================

def generar_narrativa_final(
    estrategia_json: dict,
    objetivo_usuario: str,
    modo_simulacion: str = "macro",
    metricas_red: str = "",
    use_langchain: bool = False,
) -> str:
    """
    Traduce los parámetros matemáticos a narrativa sociológica o corporativa.

    Args:
        estrategia_json: JSON de la estrategia generada.
        objetivo_usuario: Objetivo original del usuario.
        modo_simulacion: 'macro' o 'corporativo'.
        metricas_red: Resumen de métricas del grafo (para modo corporativo).
        use_langchain: Si True, intenta usar LangChainSocialArchitect.

    Returns:
        Reporte narrativo en texto.
    """
    if use_langchain:
        try:
            from langchain_workflows import build_llm, LangChainSocialArchitect, LANGCHAIN_AVAILABLE
            if LANGCHAIN_AVAILABLE:
                llm = build_llm(
                    os.getenv("LLM_PROVIDER", "groq"),
                    os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY", ""),
                    os.getenv("LLM_MODEL", ""),
                )
                if llm is not None:
                    architect = LangChainSocialArchitect(llm)
                    return architect.generate_narrative(
                        estrategia_json, objetivo_usuario, modo_simulacion, metricas_red
                    )
        except Exception as lc_err:
            log.warning(f"[LangChain narrativa] Falló, usando HTTP directo: {lc_err}")

    client = setup_client()

    if modo_simulacion == "corporativo":
        contexto = (
            f"Contexto de la red organizacional: {metricas_red}\n\n"
            "Genera un reporte ejecutivo de RRHH y gestión del cambio que explique "
            "qué acciones concretas representan estas fases matemáticas: reuniones clave, "
            "comunicados internos, workshops, cambios en estructura de reporting, "
            "mentoring a líderes informales. Usa tono consultivo y profesional."
        )
    else:
        contexto = (
            "Genera un reporte sociológico detallado y profesional que explique qué 'clima social', "
            "campañas, o eventos de la vida real representa cada fase de estas variables en la red "
            "para haber logrado el objetivo con éxito. "
            "Usa un tono analítico, de estrategia política o sociológica."
        )

    prompt = f"""
Objetivo original del usuario: {objetivo_usuario}
Secuencia final de intervenciones matemáticas ejecutadas: {json.dumps(estrategia_json, indent=2)}

{contexto}
"""
    try:
        model_llm = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        response = client.chat.completions.create(
            model=model_llm,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        log.error(f"Error generando narrativa: {e}")
        return (
            "El modelo generó la estrategia con éxito, "
            "pero falló la generación de la narrativa final por problemas del proveedor LLM."
        )


# ============================================================
# ÁRQUITECTO SOCIAL — BÚSQUEDA INVERSA PRINCIPAL
# ============================================================

def buscar_estrategia_inversa(
    estado_inicial: dict,
    objetivo_usuario: str,
    max_intentos: int = 3,
    config: dict = None,
    modo_simulacion: str = "macro",
    metricas_red: str = "",
    use_langchain: bool = False,
) -> tuple:
    """
    Ejecuta el bucle de ingeniería inversa para encontrar la estrategia
    que lleva la red al estado objetivo.

    Args:
        estado_inicial: Estado inicial del simulador.
        objetivo_usuario: Descripción del objetivo deseado.
        max_intentos: Número máximo de iteraciones de refinamiento.
        config: Configuración global del simulador.
        modo_simulacion: 'macro' (redes sociales/políticas) o
                         'corporativo' (redes organizacionales).
        metricas_red: Resumen textual de métricas del grafo (Paso 1).
        use_langchain: Si True, usa LangChainSocialArchitect en lugar de HTTP directo.

    Returns:
        Tupla (estrategia_json, narrativa, intentos_usados, historial).
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}

    # ── LangChain path ────────────────────────────────────────────────────────
    if use_langchain:
        try:
            from langchain_workflows import build_llm, LangChainSocialArchitect, LANGCHAIN_AVAILABLE
            if LANGCHAIN_AVAILABLE:
                provider = cfg.get("proveedor", "groq")
                api_key  = cfg.get("api_key", "")
                modelo   = cfg.get("modelo", "")
                llm = build_llm(provider, api_key, modelo, temperature=0.0)
                if llm is not None:
                    architect = LangChainSocialArchitect(llm)
                    historial_feedback: list = []
                    mejor_estrategia = {}
                    mejor_historial = None
                    mejor_score = -1

                    for intento in range(max_intentos):
                        try:
                            estrategia_json = architect.generate_strategy(
                                estado_inicial, objetivo_usuario,
                                historial_feedback, modo_simulacion, metricas_red,
                            )
                        except Exception as e:
                            historial_feedback.append(f"Intento {intento+1}: LangChain error: {e}")
                            continue

                        historial_sim = run_with_schedule(estado_inicial, estrategia_json, config=cfg)
                        score, feedback = evaluar_resultado(historial_sim, objetivo_usuario, cfg)

                        if score > mejor_score:
                            mejor_score = score
                            mejor_estrategia = estrategia_json
                            mejor_historial = historial_sim

                        if score >= 90:
                            narrativa = architect.generate_narrative(
                                estrategia_json, objetivo_usuario,
                                modo_simulacion, metricas_red,
                            )
                            return estrategia_json, narrativa, intento + 1, historial_sim
                        else:
                            historial_feedback.append(f"Intento {intento+1}: {feedback}")

                    if mejor_score >= 0:
                        narrativa = (
                            architect.generate_narrative(
                                mejor_estrategia, objetivo_usuario,
                                modo_simulacion, metricas_red,
                            )
                            + "\n\n*(La estrategia es la mejor aproximación).* "
                        )
                        return mejor_estrategia, narrativa, max_intentos, mejor_historial

                    return {"interventions": []}, "Error en LangChain.", max_intentos, []
        except Exception as lc_err:
            log.warning(f"[LangChain] Falló, usando HTTP directo: {lc_err}")
            # Fall through to standard HTTP path below

    # ── Standard HTTP path ────────────────────────────────────────────────────
    client = setup_client()
    historial_feedback = []

    estrategia_json = {}
    mejor_estrategia = {}
    mejor_historial = None
    mejor_score = -1

    model_llm = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

    # ── Seleccionar system prompt según modo ──────────────────────
    if modo_simulacion == "corporativo":
        system_prompt = _system_prompt_corporativo(metricas_red)
    else:
        system_prompt = _system_prompt_macro()

    for intento in range(max_intentos):
        user_prompt = _user_prompt_inverso(
            estado_inicial=estado_inicial,
            objetivo_usuario=objetivo_usuario,
            historial_feedback=historial_feedback,
            modo_simulacion=modo_simulacion,
            metricas_red=metricas_red,
        )

        try:
            response = client.chat.completions.create(
                model=model_llm,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )

            response_content = response.choices[0].message.content
            if response_content.startswith("```json"):
                response_content = response_content.replace("```json", "", 1).replace("```", "")

            estrategia_json = json.loads(response_content)
        except Exception as e:
            historial_feedback.append(f"Intento {intento+1}: Error dictado/parseo LLM: {e}")
            continue

        historial_sim = run_with_schedule(estado_inicial, estrategia_json, config=cfg)
        score, feedback = evaluar_resultado(historial_sim, objetivo_usuario, cfg)

        if score > mejor_score:
            mejor_score = score
            mejor_estrategia = estrategia_json
            mejor_historial = historial_sim

        if score >= 90:
            narrativa = generar_narrativa_final(
                estrategia_json, objetivo_usuario, modo_simulacion, metricas_red
            )
            return estrategia_json, narrativa, intento + 1, historial_sim
        else:
            historial_feedback.append(f"Intento {intento+1}: {feedback}")

    if mejor_score >= 0:
        narrativa = (
            generar_narrativa_final(mejor_estrategia, objetivo_usuario, modo_simulacion, metricas_red)
            + "\n\n*(La estrategia es la mejor aproximación, pero puede no haber cumplido todo el objetivo).* "
        )
        return mejor_estrategia, narrativa, max_intentos, mejor_historial

    return {"interventions": []}, "Error total en la simulación.", max_intentos, []
