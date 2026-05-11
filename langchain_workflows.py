"""
langchain_workflows.py — Flujos de trabajo LangChain para MASSIVE
Reemplaza las llamadas HTTP manuales con cadenas LangChain tipadas.
Soporta: groq, openai, openrouter, ollama.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

log = logging.getLogger("massive")

# ── Importaciones opcionales ──────────────────────────────────────────────────
try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
    from langchain_core.language_models.chat_models import BaseChatModel
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    log.warning("[LangChain] langchain-core no instalado.")

try:
    from langchain_openai import ChatOpenAI
    LANGCHAIN_OPENAI_AVAILABLE = True
except ImportError:
    LANGCHAIN_OPENAI_AVAILABLE = False

try:
    from langchain_groq import ChatGroq
    LANGCHAIN_GROQ_AVAILABLE = True
except ImportError:
    LANGCHAIN_GROQ_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPTS
# ─────────────────────────────────────────────────────────────────────────────

_STRATEGY_SYSTEM = """Eres el Arquitecto de Simulación de MASSIVE.
Diseña una secuencia de intervenciones matemáticas para alcanzar el objetivo social.
Modelos permitidos: lineal, umbral, memoria, backlash, polarizacion, hk,
contagio_competitivo, umbral_heterogeneo, homofilia, replicador, nash, bayesiano, sir.

Responde ÚNICAMENTE con JSON válido siguiendo exactamente esta estructura:
{{
    "interventions": [
        {{
            "time_start": <int>,
            "time_end": <int>,
            "model_name": "<string>",
            "parameters": {{}},
            "fase_rationale": "<string>",
            "target_nodes": null
        }}
    ]
}}"""

_LANDSCAPE_SYSTEM = """Eres un Diseñador de Dinámicas Sociales para MASSIVE.
Tu única tarea es generar configuraciones matemáticas en formato JSON.
REGLAS ESTRICTAS:
Responde SOLO con JSON válido. Sin texto adicional, sin explicaciones, sin markdown.
Todos los valores de "position" deben estar en el rango [-1.0, 1.0].
Los "strength" (fuerza) deben estar entre 0.5 y 4.0.
"temperature" entre 0.01 y 0.20. "lambda_social" entre 0.1 y 0.9.
ESQUEMA OBLIGATORIO:
{{
 "metadata": {{"nombre_ui": "string", "descripcion_ui": "string", "icono": "string"}},
 "energy_params": {{
   "attractors": [{{"position": 0.0, "strength": 1.0, "label": "string"}}],
   "repellers":  [{{"position": 0.0, "strength": 1.0, "label": "string"}}],
   "dynamics": {{"temperature": 0.05, "eta": 0.01, "lambda_social": 0.5}}
 }}
}}"""

_NARRATIVE_SYSTEM = """Eres un analista de dinámicas sociales.
Traduce intervenciones matemáticas en narrativas sociológicas o corporativas detalladas.
Sé preciso, usa jerga del campo (política, RRHH, comunicación social según el modo).
Responde con texto narrativo rico, no con JSON."""


def build_llm(
    provider: str,
    api_key: str = "",
    model: str = "",
    temperature: float = 0.0,
) -> "BaseChatModel | None":
    """
    Build a LangChain chat model for the given provider.

    Args:
        provider: "groq", "openai", "openrouter", or "ollama".
        api_key: API key for the provider.
        model: Model identifier.
        temperature: Sampling temperature.

    Returns:
        Configured LangChain chat model, or None if unavailable.
    """
    if not LANGCHAIN_AVAILABLE:
        return None

    p = provider.lower()

    if p == "groq":
        if not LANGCHAIN_GROQ_AVAILABLE:
            log.warning("[LangChain] langchain-groq no instalado.")
            return None
        return ChatGroq(
            api_key=api_key or os.getenv("GROQ_API_KEY", ""),
            model=model or "llama-3.1-8b-instant",
            temperature=temperature,
        )

    if p in ("openai", "openrouter"):
        if not LANGCHAIN_OPENAI_AVAILABLE:
            log.warning("[LangChain] langchain-openai no instalado.")
            return None
        base_url = None
        resolved_api_key = api_key
        if p == "openrouter":
            base_url = "https://openrouter.ai/api/v1"
            resolved_api_key = resolved_api_key or os.getenv("OPENROUTER_API_KEY", "")
        else:
            resolved_api_key = resolved_api_key or os.getenv("OPENAI_API_KEY", "")
        return ChatOpenAI(
            api_key=resolved_api_key,
            model=model or "gpt-4o-mini",
            temperature=temperature,
            base_url=base_url,
            default_headers=(
                {"HTTP-Referer": "https://github.com/Adlgr87/MASSIVE",
                 "X-Title": "MASSIVE"}
                if p == "openrouter" else {}
            ),
        )

    if p == "ollama":
        if not LANGCHAIN_OPENAI_AVAILABLE:
            log.warning("[LangChain] langchain-openai no instalado (required for Ollama).")
            return None
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        return ChatOpenAI(
            # Ollama's local API does not require authentication;
            # langchain-openai requires a non-empty string, so we pass a placeholder.
            api_key="ollama",
            model=model or "llama3:8b",
            temperature=temperature,
            base_url=f"{ollama_host}/v1",
        )

    log.warning(f"[LangChain] Proveedor desconocido: '{provider}'.")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# SOCIAL ARCHITECT CHAIN
# ─────────────────────────────────────────────────────────────────────────────

class LangChainSocialArchitect:
    """
    LangChain-based Social Architect for MASSIVE.

    Replaces raw HTTP calls in social_architect.py with proper LangChain chains:
    1. strategy_chain  — generates a JSON intervention schedule.
    2. narrative_chain — translates the schedule to a natural-language narrative.
    """

    def __init__(self, llm: "BaseChatModel") -> None:
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("langchain-core requerido.")
        self.llm = llm
        self._build_chains()

    def _build_chains(self) -> None:
        strategy_prompt = ChatPromptTemplate.from_messages([
            ("system", _STRATEGY_SYSTEM),
            ("user", "{user_input}"),
        ])
        narrative_prompt = ChatPromptTemplate.from_messages([
            ("system", _NARRATIVE_SYSTEM),
            ("user", "Objetivo: {objetivo}\n\nIntervenciones ejecutadas:\n{interventions}\n\nContexto: {context}"),
        ])
        self.strategy_chain  = strategy_prompt  | self.llm | JsonOutputParser()
        self.narrative_chain = narrative_prompt | self.llm | StrOutputParser()

    def generate_strategy(
        self,
        estado_inicial: dict,
        objetivo: str,
        historial_feedback: list,
        modo: str = "macro",
        metricas_red: str = "",
    ) -> dict:
        """Generate an intervention schedule as a JSON dict."""
        contexto = (
            f"MODO {modo.upper()} ACTIVO. "
            + (f"Métricas de red: {metricas_red}" if metricas_red else "")
        )
        user_input = (
            f"Estado inicial: {json.dumps(estado_inicial)}\n"
            f"Objetivo: {objetivo}\n"
            f"Intentos previos: {json.dumps(historial_feedback)}\n"
            f"{contexto}"
        )
        result = self.strategy_chain.invoke({"user_input": user_input})
        if not isinstance(result, dict) or "interventions" not in result:
            return {"interventions": []}
        return result

    def generate_narrative(
        self,
        estrategia: dict,
        objetivo: str,
        modo: str = "macro",
        metricas_red: str = "",
    ) -> str:
        """Generate a natural-language narrative for the given strategy."""
        context = (
            f"Modo: {modo}. " +
            (f"Red organizacional: {metricas_red}" if metricas_red else "Contexto: redes sociales masivas.")
        )
        return self.narrative_chain.invoke({
            "objetivo": objetivo,
            "interventions": json.dumps(estrategia, indent=2, ensure_ascii=False),
            "context": context,
        })


# ─────────────────────────────────────────────────────────────────────────────
# PROGRAMMATIC ARCHITECT CHAIN
# ─────────────────────────────────────────────────────────────────────────────

class LangChainProgrammaticArchitect:
    """
    LangChain-based Programmatic Architect for MASSIVE Energy Engine.

    Generates EnergyConfig JSON from a natural-language goal using a
    properly structured LangChain chain with JSON output parsing.
    """

    def __init__(self, llm: "BaseChatModel") -> None:
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("langchain-core requerido.")
        self.llm = llm
        landscape_prompt = ChatPromptTemplate.from_messages([
            ("system", _LANDSCAPE_SYSTEM),
            ("user", "Objetivo del usuario: {goal}"),
        ])
        self.chain = landscape_prompt | self.llm | JsonOutputParser()

    def generate_landscape(self, goal: str) -> Optional[dict]:
        """
        Generate an EnergyConfig dict from a user goal description.

        Returns:
            The parsed JSON dict, or None if generation failed.
        """
        try:
            result = self.chain.invoke({"goal": goal})
            if isinstance(result, dict) and "energy_params" in result:
                return result
            return None
        except Exception as exc:
            log.warning(f"[LangChainArchitect] Error: {exc}")
            return None
