"""
UIL Adapter — Integración sinérgica entre Document Intelligence, 
Interpreter Layer, y MASSIVE Simulator.

Este módulo actúa como orquestador de los flujos de entrada:
  1. Natural language → Simulator config (via InterpreterLayer)
  2. Document file → Simulator config (via DocumentIntelligence)
  3. Combined: Document + Interpretation → Simulation result

Siguiendo protocolo CLAUDE.md: surgical changes, goal-driven execution.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

try:
    from interpreter_layer import InterpreterLayer
    from document_intelligence import DocumentIntelligence, MASSIVEExtractedConfig
    from simulator import simular, DEFAULT_CONFIG

    _UIL_AVAILABLE = True
except ImportError as e:
    _UIL_AVAILABLE = False
    logging.warning(f"UIL modules not fully available: {e}")


log = logging.getLogger("massive.uil_adapter")


class UILAdapter:
    """Orquestador de flujos UIL integrados con MASSIVE simulator."""

    def __init__(self, llm_provider: str = "groq", llm_api_key: Optional[str] = None):
        """
        Initialize UIL adapter with document intelligence and interpreter layer.

        Args:
            llm_provider: LLM provider ('groq', 'openai', 'openrouter')
            llm_api_key: API key for LLM provider
        """
        if not _UIL_AVAILABLE:
            raise ImportError("UIL modules (interpreter_layer, document_intelligence) required")

        self.interpreter = InterpreterLayer(
            provider=llm_provider, api_key=llm_api_key, use_langchain=True
        )
        self.doc_intel = self.interpreter.di  # Reuse DI instance

    def from_natural_language(self, description: str) -> dict[str, Any]:
        """
        Scenario Wizard: Natural language → MASSIVE config dict.

        Args:
            description: Colloquial or technical scenario description

        Returns:
            dict ready for simular(**config)
        """
        log.info(f"UIL Wizard: processing '{description[:50]}...'")
        wizard_result = self.interpreter.wizard(description)
        config = wizard_result.to_simular_kwargs()
        log.info(f"UIL Wizard: generated config with {len(config)} parameters")
        return config

    def from_document(self, file_path: str) -> dict[str, Any]:
        """
        Document Extraction: PDF/JSON/CSV/XLSX → MASSIVE config dict.

        Args:
            file_path: Path to document file

        Returns:
            dict ready for simular(**config)
        """
        log.info(f"UIL Document: parsing '{file_path}'")
        ctx = self.doc_intel.parse_file(file_path)
        extracted = self.doc_intel.extract_massive_params(ctx)
        # Prefer explicit to_simular_kwargs (config_dict is a legacy alias).
        config = extracted.to_simular_kwargs()
        log.info(f"UIL Document: extracted {len(config)} parameters")
        return config

    def from_document_and_description(
        self, file_path: str, description: str
    ) -> dict[str, Any]:
        """
        Combined flow: Document + natural language interpretation.

        Document provides base parameters; description refines them.

        Args:
            file_path: Path to document
            description: Additional scenario context

        Returns:
            Merged config dict
        """
        log.info(f"UIL Combined: parsing document + description")

        # Extract from document
        doc_config = self.from_document(file_path)

        # Interpret description
        desc_config = self.from_natural_language(description)

        # Merge: description overrides document where both specify
        merged = {**doc_config, **desc_config}
        log.info(f"UIL Combined: merged configs → {len(merged)} final parameters")

        return merged

    def full_pipeline(
        self,
        file_path: Optional[str] = None,
        description: Optional[str] = None,
        simulation_steps: int = 50,
    ) -> dict[str, Any]:
        """
        Complete end-to-end: Config generation → Simulation → Results.

        Args:
            file_path: Optional path to document
            description: Optional natural language description
            simulation_steps: Number of simulation steps

        Returns:
            {
                'config': final configuration dict,
                'history': simulation history,
                'summary': narrative summary of results
            }
        """
        if not file_path and not description:
            raise ValueError("Provide file_path or description (or both)")

        log.info("UIL Pipeline: full execution")

        # Step 1: Generate config
        if file_path and description:
            config = self.from_document_and_description(file_path, description)
        elif file_path:
            config = self.from_document(file_path)
        else:  # description only
            config = self.from_natural_language(description)

        # Split flat wizard/doc keys into simular(estado, escenario, config=...)
        estado_keys = {
            "opinion", "propaganda", "confianza",
            "opinion_grupo_a", "opinion_grupo_b", "identidad_grupo",
            "pertenencia_grupo",
        }
        estado_inicial = {
            k: config[k] for k in estado_keys if k in config
        }
        # Sensible defaults for required state fields
        if "opinion" not in estado_inicial:
            estado_inicial["opinion"] = 0.0
        if "propaganda" not in estado_inicial:
            estado_inicial["propaganda"] = 0.0

        escenario = str(config.get("escenario", "campana"))
        pasos = int(config.get("pasos", simulation_steps))

        sim_config = {**DEFAULT_CONFIG}
        for key, val in config.items():
            if key in estado_keys or key in {"escenario", "pasos", "regla_sugerida"}:
                continue
            if key in DEFAULT_CONFIG or key in {
                "homofilia_tasa", "sesgo_confirmacion", "cultural_profile",
            }:
                sim_config[key] = val

        log.info(
            "UIL Pipeline: config ready, starting simulation (%s steps, escenario=%s)",
            pasos,
            escenario,
        )

        # Step 2: Simulate with the real simular signature
        history = simular(
            estado_inicial,
            escenario=escenario,
            pasos=pasos,
            config=sim_config,
            verbose=False,
        )

        # Step 3: Narrative summary
        narrative = self.interpreter.narrate(history)

        log.info("UIL Pipeline: complete")

        return {
            "config": {
                "estado_inicial": estado_inicial,
                "escenario": escenario,
                "pasos": pasos,
                "config": sim_config,
                "raw": config,
            },
            "history": history,
            "summary": (
                narrative.narrative
                if hasattr(narrative, "narrative")
                else str(narrative)
            ),
        }


# Convenience factory
def create_uil_adapter(llm_provider: str = "groq", llm_api_key: Optional[str] = None) -> UILAdapter:
    """Factory function to create UIL adapter with error handling."""
    try:
        return UILAdapter(llm_provider=llm_provider, llm_api_key=llm_api_key)
    except ImportError as e:
        log.error(f"Cannot create UIL adapter: {e}")
        raise
