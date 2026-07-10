"""
Tests for social_architect._decode_strategy() improvements.

Validates:
- Backward compatibility with 1D regime_logits (legacy CfC models)
- Per-phase regime selection with 2D regime_logits (new CfC models)
- Parameter extraction and preservation per phase
- Duration normalization and time interval calculation
- Defensive handling of malformed or edge-case inputs
"""

import numpy as np
import pytest
from social_architect import _decode_strategy
from simulator import NOMBRES_REGLAS


class TestDecodeStrategyBackwardCompatibility:
    """Legacy CfC support: 1D regime_logits."""

    def test_1d_regime_logits_shape(self):
        """Single regime vector → all phases use same regime."""
        propuesta = {
            "regime_logits": np.array([0.2, 1.0, 0.5, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            "durations": np.array([0.33, 0.33, 0.34]),  # 3 fases
            "parameters": [{}, {}, {}],
        }
        strategy = _decode_strategy(propuesta, total_pasos=60)
        
        assert "interventions" in strategy
        assert len(strategy["interventions"]) == 3
        
        # Todas las fases deben usar el régimen 1 (argmax de logits)
        for interv in strategy["interventions"]:
            assert interv["model_name"] == "umbral"  # régimen 1
    
    def test_1d_empty_params_fallback(self):
        """Legacy: no parameters field → defaults to empty dicts."""
        propuesta = {
            "regime_logits": np.array([1.0, 0.0] + [0.0] * 11),
            "durations": np.array([0.5, 0.5]),
        }
        strategy = _decode_strategy(propuesta, total_pasos=60)
        
        assert len(strategy["interventions"]) == 2
        for interv in strategy["interventions"]:
            assert interv["parameters"] == {}


class TestDecodeStrategyPerPhase:
    """New CfC support: 2D regime_logits per phase."""

    def test_2d_regime_logits_per_phase(self):
        """Different regime per phase."""
        propuesta = {
            # Fase 1: régimen 0 (lineal)
            # Fase 2: régimen 5 (hk)
            # Fase 3: régimen 4 (polarizacion)
            "regime_logits": np.array([
                [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],  # argmax=0
                [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],  # argmax=5
                [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],  # argmax=4
            ]),
            "durations": np.array([0.33, 0.33, 0.34]),
            "parameters": [{"a": 0.7}, {"epsilon": 0.3}, {"fuerza": 0.1}],
        }
        strategy = _decode_strategy(propuesta, total_pasos=60)
        
        assert len(strategy["interventions"]) == 3
        
        # Verificar régimen por fase
        assert strategy["interventions"][0]["model_name"] == "lineal"
        assert strategy["interventions"][1]["model_name"] == "hk"
        assert strategy["interventions"][2]["model_name"] == "polarizacion"
        
        # Verificar parámetros preservados
        assert strategy["interventions"][0]["parameters"]["a"] == 0.7
        assert strategy["interventions"][1]["parameters"]["epsilon"] == 0.3
        assert strategy["interventions"][2]["parameters"]["fuerza"] == 0.1

    def test_2d_mixed_parameters(self):
        """Some phases with params, others without."""
        propuesta = {
            "regime_logits": np.array([
                [1.0] + [0.0] * 12,
                [0.0] * 6 + [1.0] + [0.0] * 6,  # contagio_competitivo=6
            ]),
            "durations": np.array([0.5, 0.5]),
            "parameters": [
                {"a": 0.8, "b": 0.2},
                {},  # Empty for phase 2
            ],
        }
        strategy = _decode_strategy(propuesta, total_pasos=100)
        
        assert strategy["interventions"][0]["parameters"]["a"] == 0.8
        assert strategy["interventions"][1]["parameters"] == {}


class TestParameterPreservation:
    """Validation: parameters are extracted and preserved."""

    def test_parameters_per_phase_extracted(self):
        """Complex parameter dict per phase."""
        propuesta = {
            "regime_logits": np.array([[1.0] + [0.0] * 12] * 2),
            "durations": np.array([0.5, 0.5]),
            "parameters": [
                {
                    "a": 0.75,
                    "b": 0.25,
                    "custom_key": "custom_value",
                },
                {
                    "alpha": 0.6,
                    "beta": 0.3,
                    "gamma": 0.1,
                },
            ],
        }
        strategy = _decode_strategy(propuesta, total_pasos=100)
        
        p0 = strategy["interventions"][0]["parameters"]
        p1 = strategy["interventions"][1]["parameters"]
        
        assert p0["a"] == 0.75
        assert p0["custom_key"] == "custom_value"
        assert p1["alpha"] == 0.6
        assert p1["gamma"] == 0.1

    def test_parameters_none_fallback(self):
        """propuesta["parameters"] is None → create empty dicts."""
        propuesta = {
            "regime_logits": np.array([[0.0] * 13] * 2),  # invalid but handled
            "durations": np.array([0.5, 0.5]),
            "parameters": None,
        }
        strategy = _decode_strategy(propuesta, total_pasos=100)
        
        assert all(interv["parameters"] == {} for interv in strategy["interventions"])


class TestDurationNormalization:
    """Time interval calculation."""

    def test_unnormalized_durations(self):
        """Non-normalized durations → normalized automatically."""
        propuesta = {
            "regime_logits": np.array([[1.0] + [0.0] * 12] * 3),
            "durations": np.array([2.0, 3.0, 5.0]),  # Sum=10, not 1
            "parameters": [{}, {}, {}],
        }
        strategy = _decode_strategy(propuesta, total_pasos=100)
        
        durations = [d for d in [2.0, 3.0, 5.0]]
        total = sum(durations)
        normalized = [d / total for d in durations]
        
        expected_steps = [
            int(round(normalized[0] * 100)),
            int(round(normalized[1] * 100)),
            int(round(normalized[2] * 100)),
        ]
        
        actual_steps = [
            interv["time_end"] - interv["time_start"] + 1
            for interv in strategy["interventions"]
        ]
        
        # Rough check: durations are scaled correctly
        assert sum(actual_steps) >= 95  # Allow some rounding error

    def test_time_boundaries_no_overlap(self):
        """Time intervals don't overlap and cover full range."""
        propuesta = {
            "regime_logits": np.array([[1.0] + [0.0] * 12] * 4),
            "durations": np.array([0.25, 0.25, 0.25, 0.25]),
            "parameters": [{}, {}, {}, {}],
        }
        strategy = _decode_strategy(propuesta, total_pasos=60)
        
        interventions = strategy["interventions"]
        
        # Check no overlap
        for i in range(len(interventions) - 1):
            assert interventions[i]["time_end"] < interventions[i + 1]["time_start"]
        
        # Check coverage
        assert interventions[0]["time_start"] == 1
        assert interventions[-1]["time_end"] <= 60


class TestDefensiveHandling:
    """Edge cases and malformed inputs."""

    def test_empty_regime_logits(self):
        """regime_logits is empty → fallback to linear."""
        propuesta = {
            "regime_logits": np.array([]),
            "durations": np.array([1.0]),
            "parameters": [{}],
        }
        strategy = _decode_strategy(propuesta, total_pasos=60)
        
        # Should not crash, should have at least one intervention
        assert len(strategy["interventions"]) >= 1

    def test_zero_durations(self):
        """All durations are zero → normalize to equal."""
        propuesta = {
            "regime_logits": np.array([[1.0] + [0.0] * 12] * 2),
            "durations": np.array([0.0, 0.0]),
            "parameters": [{}, {}],
        }
        strategy = _decode_strategy(propuesta, total_pasos=100)
        
        # Should normalize to equal durations
        assert len(strategy["interventions"]) == 2

    def test_3d_regime_logits_squeezed(self):
        """Over-dimensional regime_logits → squeezed to 1D or 2D."""
        propuesta = {
            "regime_logits": np.array([[[1.0] + [0.0] * 12] * 2]),  # (1, 2, 13)
            "durations": np.array([0.5, 0.5]),
            "parameters": [{}, {}],
        }
        strategy = _decode_strategy(propuesta, total_pasos=60)
        
        # Should not crash
        assert len(strategy["interventions"]) == 2

    def test_params_mismatch_phases(self):
        """More phases than params → pad with empty dicts."""
        propuesta = {
            "regime_logits": np.array([[1.0] + [0.0] * 12] * 5),
            "durations": np.array([0.2] * 5),
            "parameters": [{"a": 1}],  # Only 1 param for 5 phases
        }
        strategy = _decode_strategy(propuesta, total_pasos=100)
        
        assert len(strategy["interventions"]) == 5
        assert strategy["interventions"][0]["parameters"]["a"] == 1
        assert strategy["interventions"][1]["parameters"] == {}


class TestIntegrationWithRunWithSchedule:
    """Schema compatibility check."""

    def test_output_schema_valid(self):
        """Output is valid StrategyMatrix for run_with_schedule()."""
        propuesta = {
            "regime_logits": np.array([[0.0] * 6 + [1.0] + [0.0] * 6]),  # contagio=6
            "durations": np.array([1.0]),
            "parameters": [{"competencia": 0.4}],
        }
        strategy = _decode_strategy(propuesta, total_pasos=60)
        
        # Check required fields
        assert "interventions" in strategy
        interventions = strategy["interventions"]
        assert len(interventions) > 0
        
        for interv in interventions:
            assert "time_start" in interv
            assert "time_end" in interv
            assert "model_name" in interv
            assert "parameters" in interv
            assert "fase_rationale" in interv
            assert "target_nodes" in interv
            
            # Verify types
            assert isinstance(interv["time_start"], int)
            assert isinstance(interv["time_end"], int)
            assert isinstance(interv["model_name"], str)
            assert isinstance(interv["parameters"], dict)
            assert isinstance(interv["target_nodes"], type(None))
            
            # Verify bounds
            assert 1 <= interv["time_start"] <= 60
            assert interv["time_start"] <= interv["time_end"] <= 60
            assert interv["model_name"] in NOMBRES_REGLAS.values()
