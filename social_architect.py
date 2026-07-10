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
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from pydantic import ValidationError

from schemas import StrategyMatrix
from simulator import run_with_schedule, resumen_historial, DEFAULT_CONFIG
from intervention_optimizer import optimize_interventions
from forecast import TemporalConfig, forecast

log = logging.getLogger("massive")

# CfC INTEGRATION — primer intento sin llamada LLM si el modelo está disponible
try:
    from cfc_router import CfCRouter
    _cfc = CfCRouter.get()
    CFC_AVAILABLE = _cfc.status["architect_policy"]
except ImportError:
    CFC_AVAILABLE, _cfc = False, None


def find_optimal_interventions(evaluate_fn, n_agents, n_phases, max_iter=100):
    """Drop-in replacement for intervention optimization.

    Args:
        evaluate_fn: Objective function that scores intervention matrices.
        n_agents: Number of agents to optimize.
        n_phases: Number of intervention phases.
        max_iter: Maximum optimization iterations.

    Returns:
        Optimization result dictionary with interventions and score.
    """
    return optimize_interventions(
        evaluate_fn=evaluate_fn,
        n_agents=n_agents,
        n_phases=n_phases,
        max_iter=max_iter,
    )


# ============================================================
# TELEMETRY & LOGGING — Architects Attempts
# ============================================================

def _ensure_architect_attempts_dir() -> Path:
    """Ensures reports/architect_attempts/ exists for telemetry."""
    path = Path("reports/architect_attempts")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _log_attempt(
    attempt_num: int,
    estado_5d: dict,
    strategy: dict,
    score: float,
    objetivo: str,
    modo: str,
    timestamp: str | None = None,
) -> None:
    """
    Logs an architect attempt for meta-optimizer training.

    Args:
        attempt_num: Attempt number in the search loop.
        estado_5d: 5D state vector summary (opinion, cooperation, etc.).
        strategy: Generated strategy JSON.
        score: Evaluation score (0-100).
        objetivo: User objective description.
        modo: Simulation mode (macro/corporativo).
        timestamp: ISO datetime string (auto-generated if None).
    """
    try:
        ts = timestamp or datetime.utcnow().isoformat()
        attempt_record = {
            "timestamp": ts,
            "attempt": attempt_num,
            "objetivo": objetivo,
            "modo": modo,
            "estado_5d": estado_5d,
            "strategy": strategy,
            "score": score,
            "_metadata": {
                "cfc_available": CFC_AVAILABLE,
                "version": "1.0",
            },
        }
        
        attempts_dir = _ensure_architect_attempts_dir()
        # Filename: run_{timestamp}.jsonl — append-only for session
        run_id = ts.split("T")[0] + "_" + ts.split("T")[1][:8].replace(":", "")
        logfile = attempts_dir / f"run_{run_id}.jsonl"
        
        with open(logfile, "a", encoding="utf-8") as f:
            f.write(json.dumps(attempt_record, ensure_ascii=False) + "\n")
        
        log.debug(f"[Architect Telemetry] Logged attempt {attempt_num} → {logfile.name}")
    except Exception as e:
        log.warning(f"[Architect Telemetry] Failed to log attempt: {e}")


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


def _build_temporal_forecast(
    historial: list[dict],
    cfg: dict,
    estado_inicial: dict | None = None,
) -> dict:
    """
    Computes an analytical temporal forecast from a simulation history.
    """
    if not historial:
        return {}

    event_type = str(cfg.get("forecast_event_type", "labor_conflict"))
    horizon_days = int(cfg.get("forecast_time_horizon_days", 90))
    step_days = int(cfg.get("forecast_step_duration_days", 7))

    temporal_cfg = TemporalConfig(
        event_type=event_type,
        time_horizon_days=max(1, horizon_days),
        step_duration_days=max(1, step_days),
    )
    state = dict(historial[-1])
    state["historial"] = historial
    state["config"] = cfg

    result_best = forecast(state, temporal_cfg, mode="analytical")

    result_base = None
    if estado_inicial:
        estado_base = dict(estado_inicial)
        estado_base["config"] = cfg
        result_base = forecast(estado_base, temporal_cfg, mode="analytical")

    no_action = result_base.p_event if result_base else result_best.p_event
    min_days = result_best.days_to_event

    return {
        "p_event": result_best.p_event,
        "days_to_event": result_best.days_to_event,
        "confidence": result_best.confidence,
        "p_event_no_intervention": no_action,
        "p_event_best_plan": result_best.p_event,
        "min_effect_time_days": min_days,
        "feasibility_vs_deadline": bool(
            min_days is not None and min_days <= temporal_cfg.time_horizon_days
        ),
        "forecast_best_plan": result_best.model_dump(),
        "forecast_no_intervention": result_base.model_dump() if result_base else None,
    }


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
    temporal_forecast: dict | None = None,
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
Pronóstico temporal: {json.dumps(temporal_forecast or {}, indent=2)}

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
# CfC HELPERS — codificación de objetivo y decodificación de estrategia
# ============================================================

def _encode_goal(objetivo: str) -> list:
    """
    Codifica un objetivo en texto libre en un vector de 5 floats
    para CfCArchitectPolicy.

    Args:
        objetivo: Descripción del objetivo en lenguaje natural.

    Returns:
        Lista de 5 floats normalizada al rango [-1, 1].
    """
    kw = {
        "consenso":     [ 1.0,  0.0, -0.5,  0.0,  0.0],
        "polarizacion": [ 0.0,  1.0,  0.5,  0.0,  0.0],
        "moderado":     [ 0.5,  0.0, -0.3,  0.0,  0.0],
        "cambio":       [ 0.0,  0.0,  0.0,  1.0,  0.5],
        "resistencia":  [ 0.0,  0.0,  0.0, -1.0,  0.5],
        "despolarizar": [ 1.0, -0.5,  0.0,  0.0,  0.0],
        "radicalizar":  [-0.5,  1.0,  0.5,  0.0,  0.0],
        "alinear":      [ 0.8,  0.0, -0.2,  0.5,  0.0],
        "cohesion":     [ 0.7,  0.0, -0.3,  0.3,  0.0],
    }
    v = [0.0] * 5
    obj_lower = objetivo.lower()
    for k, e in kw.items():
        if k in obj_lower:
            v = [a + b for a, b in zip(v, e)]
    norm = max(abs(x) for x in v) or 1.0
    return [x / norm for x in v]


def _decode_strategy(propuesta: dict, total_pasos: int = 60) -> dict:
    """
    Convierte la salida de CfCArchitectPolicy en un StrategyMatrix válido.
    
    Versión mejorada que:
    - Soporta tanto regime_logits (n_regimes,) como (n_phases, n_regimes)
    - Extrae parámetros por fase en lugar de descartarlos
    - Mantiene compatibilidad hacia atrás con modelos CfC antiguos
    - Aplica validación defensiva de formas

    Args:
        propuesta:    Diccionario de salida del modelo CfC con keys:
                      - "regime_logits": np.ndarray, forma (n_regimes,) o (n_phases, n_regimes)
                      - "durations": np.ndarray, forma (n_phases,)
                      - "parameters" (opcional): list[dict] o np.ndarray con parámetros por fase
        total_pasos:  Número total de pasos de la simulación.

    Returns:
        Diccionario con estructura {"interventions": [...]} compatible con
        run_with_schedule().

    Example:
        >>> propuesta = {
        ...     "regime_logits": np.array([[1.0, 0.5], [0.2, 0.8]]),  # 2 fases, 2 regímenes
        ...     "durations": np.array([0.5, 0.5]),  # 50% tiempo cada fase
        ...     "parameters": [{"epsilon": 0.3}, {"epsilon": 0.5}],  # params por fase
        ... }
        >>> strategy = _decode_strategy(propuesta, total_pasos=60)
        >>> # Resultado: 2 intervenciones, fases 1-30 y 31-60, con parámetros distintos
    """
    import numpy as np
    from simulator import NOMBRES_REGLAS

    # ── Extraer logits de régimen (manejo robusto de formas) ──────────────────
    regime_logits = np.asarray(propuesta.get("regime_logits", []))
    if regime_logits.size == 0:
        log.warning("[CfC Decode] regime_logits vacío, usando default lineal")
        regime_logits = np.array([1.0])
    
    # Aplanar si es batch (CfC puede retornar [batch, regimes] por error)
    if regime_logits.ndim > 2:
        regime_logits = regime_logits.squeeze()
    
    # ── Extraer duraciones (normalización) ──────────────────────────────────
    durations = np.asarray(propuesta.get("durations", []))
    if durations.size == 0:
        log.warning("[CfC Decode] durations vacío, usando una fase única")
        durations = np.array([1.0])
    
    # Normalizar duraciones para que sumen 1.0
    dur_sum = np.sum(durations)
    if dur_sum > 0:
        durations = durations / dur_sum
    else:
        durations = np.ones_like(durations) / len(durations)
    
    n_phases = len(durations)
    
    # ── Extraer parámetros por fase (nuevo: no descartar) ────────────────────
    params_per_phase = propuesta.get("parameters", None)
    if params_per_phase is not None:
        params_per_phase = np.asarray(params_per_phase)
        # Si es lista de dicts o array, convertir a lista de dicts
        if params_per_phase.dtype == object:
            # Ya es lista de objetos (dicts)
            params_per_phase = list(params_per_phase)
        else:
            # Es array numérico → convertir a lista vacía (sin parámetros numéricos extraíbles)
            params_per_phase = [{} for _ in range(n_phases)]
    else:
        params_per_phase = [{} for _ in range(n_phases)]
    
    # Asegurar que tenemos exactamente n_phases parámetros
    while len(params_per_phase) < n_phases:
        params_per_phase.append({})
    params_per_phase = params_per_phase[:n_phases]

    # ── Construir intervenciones ─────────────────────────────────────────────
    interventions = []
    t = 1
    
    for i in range(n_phases):
        dur = max(1, int(round(float(durations[i]) * total_pasos)))
        end = min(t + dur - 1, total_pasos)
        
        # Seleccionar régimen: por fase si es 2D, global si es 1D
        if regime_logits.ndim == 2 and i < regime_logits.shape[0]:
            rid = int(np.argmax(regime_logits[i, :]))
        else:
            # Fallback: usar argmax global (compatibilidad con CfC 1D)
            rid = int(np.argmax(regime_logits)) if regime_logits.ndim == 1 else 0
        
        regla_nombre = NOMBRES_REGLAS.get(rid, "lineal")
        
        # Extraer parámetros de esta fase
        phase_params = params_per_phase[i] if isinstance(params_per_phase[i], dict) else {}
        
        interventions.append({
            "time_start": t,
            "time_end": end,
            "model_name": regla_nombre,
            "parameters": phase_params,  # ← MEJORADO: ahora contiene datos reales
            "fase_rationale": (
                f"CfC fase {i + 1}/{n_phases}: régimen {regla_nombre}, "
                f"duración {dur:d} pasos, params={phase_params}"
            ),
            "target_nodes": None,
        })
        t = end + 1
        if t > total_pasos:
            break

    log.info(
        f"[CfC Decode] Estrategia generada: {len(interventions)} fases, "
        f"regime_logits shape={regime_logits.shape}, params_extracted={sum(1 for p in params_per_phase if p)}"
    )
    
    return {"interventions": interventions}


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

    Si CfC está disponible, ejecuta un "Intento 0" neuronal antes del
    bucle LLM. Si score ≥ 90, retorna sin invocar ninguna API.

    Args:
        estado_inicial: Estado inicial del simulador.
        objetivo_usuario: Descripción del objetivo deseado.
        max_intentos: Número máximo de iteraciones de refinamiento LLM.
        config: Configuración global del simulador.
        modo_simulacion: 'macro' (redes sociales/políticas) o
                         'corporativo' (redes organizacionales).
        metricas_red: Resumen textual de métricas del grafo (Paso 1).
        use_langchain: Si True, usa LangChainSocialArchitect en lugar de HTTP directo.

    Returns:
        Tupla (estrategia_json, narrativa, intentos_usados, historial).
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}

    # ── CfC Intento 0 — sin llamada LLM ──────────────────────────────────────
    feedback_inicial = ""
    if CFC_AVAILABLE:
        try:
            goal_emb = _encode_goal(objetivo_usuario)
            propuesta = _cfc.propose_strategy(estado_inicial, goal_emb)
            if propuesta is not None:
                pasos_cfg = cfg.get("pasos", 60)
                estrategia_cfc = _decode_strategy(propuesta, total_pasos=pasos_cfg)
                historial_cfc = run_with_schedule(
                    estado_inicial, estrategia_cfc, config=cfg
                )
                score_cfc, fb_cfc = evaluar_resultado(
                    historial_cfc, objetivo_usuario, cfg
                )
                log.info(f"[CfC Architect] Intento 0: score={score_cfc:.1f}")
                
                # ── Telemetría: registrar intento 0 ──────────────────────
                if historial_cfc:
                    estado_5d_summary = {
                        "mean_opinion": float(sum(h.get("opinion", 0.0) for h in historial_cfc) / len(historial_cfc)),
                        "final_opinion": float(historial_cfc[-1].get("opinion", 0.0)),
                        "polarization": float(historial_cfc[-1].get("polarizacion_media", 0.0)),
                    }
                    _log_attempt(
                        attempt_num=0,
                        estado_5d=estado_5d_summary,
                        strategy=estrategia_cfc,
                        score=score_cfc,
                        objetivo=objetivo_usuario,
                        modo=modo_simulacion,
                    )
                
                if score_cfc >= 90:
                    temporal = _build_temporal_forecast(historial_cfc, cfg, estado_inicial)
                    estrategia_cfc = dict(estrategia_cfc)
                    estrategia_cfc["temporal_forecast"] = temporal
                    narrativa = (
                        "Estrategia generada por CfC (sin API LLM). "
                        f"Score: {score_cfc:.1f}/100.\n\n{fb_cfc}\n\n"
                        f"Pronóstico temporal: P(evento)={temporal.get('p_event', 0.0):.2%}, "
                        f"días estimados={temporal.get('days_to_event')}"
                    )
                    return estrategia_cfc, narrativa, 0, historial_cfc
                feedback_inicial = f"[CfC score={score_cfc:.1f}] {fb_cfc} "
        except Exception as exc:
            log.debug(f"[CfC Architect] Intento 0 fallido: {exc}")

    # ── LangChain path ───────────────────────────────────────────────────────
    if use_langchain:
        try:
            from langchain_workflows import build_llm, LangChainSocialArchitect, LANGCHAIN_AVAILABLE
            if LANGCHAIN_AVAILABLE:
                provider = cfg.get("proveedor", "groq")
                modelo   = cfg.get("modelo", "")
                llm = build_llm(provider, model=modelo, temperature=0.0)
                if llm is not None:
                    architect = LangChainSocialArchitect(llm)
                    # Inyectar el feedback del Intento 0 CfC si existe
                    historial_feedback: list = [feedback_inicial] if feedback_inicial else []
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
                            temporal = _build_temporal_forecast(historial_sim, cfg, estado_inicial)
                            estrategia_json = dict(estrategia_json)
                            estrategia_json["temporal_forecast"] = temporal
                            narrativa = architect.generate_narrative(
                                estrategia_json, objetivo_usuario,
                                modo_simulacion, metricas_red,
                            )
                            return estrategia_json, narrativa, intento + 1, historial_sim
                        else:
                            historial_feedback.append(f"Intento {intento+1}: {feedback}")

                    if mejor_score >= 0:
                        temporal = _build_temporal_forecast(mejor_historial or [], cfg, estado_inicial)
                        mejor_estrategia = dict(mejor_estrategia)
                        mejor_estrategia["temporal_forecast"] = temporal
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
    # Inyectar el feedback del Intento 0 CfC si existe
    historial_feedback = [feedback_inicial] if feedback_inicial else []

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

        # ── Telemetría: registrar intento LLM ────────────────────────
        if historial_sim:
            estado_5d_summary = {
                "mean_opinion": float(sum(h.get("opinion", 0.0) for h in historial_sim) / len(historial_sim)),
                "final_opinion": float(historial_sim[-1].get("opinion", 0.0)),
                "polarization": float(historial_sim[-1].get("polarizacion_media", 0.0)),
            }
            _log_attempt(
                attempt_num=intento + 1,
                estado_5d=estado_5d_summary,
                strategy=estrategia_json,
                score=score,
                objetivo=objetivo_usuario,
                modo=modo_simulacion,
            )

        if score >= 90:
            temporal = _build_temporal_forecast(historial_sim, cfg, estado_inicial)
            estrategia_json = dict(estrategia_json)
            estrategia_json["temporal_forecast"] = temporal
            narrativa = generar_narrativa_final(
                estrategia_json, objetivo_usuario, modo_simulacion, metricas_red, temporal
            )
            return estrategia_json, narrativa, intento + 1, historial_sim
        else:
            historial_feedback.append(f"Intento {intento+1}: {feedback}")

    if mejor_score >= 0:
        temporal = _build_temporal_forecast(mejor_historial or [], cfg, estado_inicial)
        mejor_estrategia = dict(mejor_estrategia)
        mejor_estrategia["temporal_forecast"] = temporal
        narrativa = (
            generar_narrativa_final(
                mejor_estrategia,
                objetivo_usuario,
                modo_simulacion,
                metricas_red,
                temporal,
            )
            + "\n\n*(La estrategia es la mejor aproximación, pero puede no haber cumplido todo el objetivo).* "
        )
        return mejor_estrategia, narrativa, max_intentos, mejor_historial

    return {"interventions": []}, "Error total en la simulación.", max_intentos, []
