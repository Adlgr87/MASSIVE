"""
LLM Integration Module for MASSIVE Simulator.

Provides LLM-based and heuristic rule selection for social dynamics simulation.
"""

from simulator_core.llm_integration.prompt_builder import construir_prompt
from simulator_core.llm_integration.providers import (
    extraer_json,
    llamar_openai_compatible,
    llamar_ollama,
    resolve_provider_api_key,
)
from simulator_core.llm_integration.heuristic_selector import llamar_llm_heuristico
from simulator_core.llm_integration.llm_dispatcher import llamar_llm

__all__ = [
    "construir_prompt",
    "extraer_json",
    "llamar_openai_compatible",
    "llamar_ollama",
    "resolve_provider_api_key",
    "llamar_llm_heuristico",
    "llamar_llm",
]
