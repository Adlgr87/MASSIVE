"""
Smoke tests for root engines that must function without PyTorch.

These exercise the non-torch code paths (SocialEnergyEngine, MassiveSimEngine,
simulator.llamar_llm fallback) so coverage captures the root modules even in
local dev where torch is absent.
"""

import numpy as np
import pytest


def test_social_energy_engine_constructs():
    from energy_engine import SocialEnergyEngine

    eng = SocialEnergyEngine(range_type="bipolar", temperature=0.1, gini_coefficient=0.4)
    assert eng is not None


def test_massive_sim_engine_runs():
    from massive_engine import MassiveSimEngine

    eng = MassiveSimEngine(N=32, K=2)
    result = eng.run(steps=3)
    assert "mean_opinion" in result and "n_agents" in result
    assert result["n_agents"] == 32


def test_simulator_llm_fallback_no_torch():
    """llamar_llm falls back to heuristic when provider unavailable."""
    from unittest.mock import patch
    import requests
    import simulator

    estado = {"opinion": 0.5, "propaganda": 0.02}
    cfg = {**simulator.DEFAULT_CONFIG, "proveedor": "openai", "api_key": "fake"}

    with patch("requests.post", side_effect=requests.exceptions.ConnectionError):
        resultado = simulator.llamar_llm(estado, "campana", [estado], cfg)

    assert isinstance(result := resultado, dict)
    assert "regla" in resultado and "razon" in resultado
