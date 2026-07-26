"""
Main LLM dispatcher for rule selection.
"""

from typing import Dict, List, Optional
import logging

log = logging.getLogger(__name__)


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
    from simulator_core.llm_integration.prompt_builder import construir_prompt
    from simulator_core.llm_integration.providers import (
        PROVEEDORES,
        resolve_provider_api_key,
        llamar_openai_compatible,
        llamar_ollama,
    )
    from simulator_core.llm_integration.heuristic_selector import llamar_llm_heuristico
    from simulator_core.config import REGLAS
    
    proveedor = cfg.get("proveedor", "heurístico")

    if proveedor == "heurístico":
        return llamar_llm_heuristico(estado, escenario, historial_reciente, cfg)

    prompt = construir_prompt(estado, escenario, historial_reciente, cfg)
    data   = None

    if proveedor == "ollama":
        data = llamar_ollama(prompt, cfg)
    elif proveedor in PROVEEDORES:
        info    = PROVEEDORES[proveedor]
        modelo  = cfg.get("modelo", "").strip() or info["modelos_sugeridos"][0]
        if not resolve_provider_api_key(proveedor, fallback=cfg.get("api_key", "")):
            log.error(f"'{proveedor}' requiere API key. → heurístico.")
            return llamar_llm_heuristico(estado, escenario, historial_reciente, cfg)
        data = llamar_openai_compatible(
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
