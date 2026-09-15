"""Integration tests for the CfC landscape modulator (Pipeline B).

Verifies:
- Model loads from disk
- propose_landscape returns valid landscape parameters
- Engine can use the landscape model for dynamic modulation
- Graceful fallback when model is unavailable
"""

import pytest

from cfc_router import CfCRouter
from energy_engine import SocialEnergyEngine, _ews_fallback_multiplier


class TestCfCLandscapeModulator:
    """Tests for the CfCLandscapeModulator class and integration."""

    def test_model_file_exists(self):
        """The trained landscape model artifact should exist on disk."""
        from pathlib import Path
        assert Path("models/cfc_calibrated/cfc_landscape.pt").exists()

    def test_model_loads_in_router(self):
        """The router should load the landscape model successfully."""
        CfCRouter._instance = None
        router = CfCRouter.get()
        assert router.status["landscape_corrector"] is True
        assert router._landscape_corrector is not None

    def test_propose_landscape_returns_valid_params(self):
        """propose_landscape should return a dict with 5 keys + 'cfc' source."""
        CfCRouter._instance = None
        router = CfCRouter.get()
        params, source = router.propose_landscape({
            "polarization": 0.5,
            "delta_p1": 0.02,
            "delta_p5": 0.01,
            "skewness": 0.3,
            "gini": 0.4,
        })
        assert source == "cfc"
        assert params is not None
        assert set(params.keys()) == {
            "sigma_p", "attractor_strength", "repeller_strength",
            "attractor_position", "repeller_position"
        }

    def test_landscape_output_ranges(self):
        """Model output values should be within physically valid ranges."""
        CfCRouter._instance = None
        router = CfCRouter.get()
        for pol in [0.0, 0.25, 0.5, 0.75, 1.0]:
            params, _ = router.propose_landscape({
                "polarization": pol,
                "delta_p1": 0.02,
                "delta_p5": 0.01,
                "skewness": 0.3,
                "gini": 0.35,
            })
            assert params is not None
            # Strengths and sigma must be positive
            assert params["sigma_p"] > 0
            assert params["attractor_strength"] > 0
            assert params["repeller_strength"] > 0
            # Positions must be in [-1, 1]
            assert -1.0 <= params["attractor_position"] <= 1.0
            assert -1.0 <= params["repeller_position"] <= 1.0

    def test_engine_loads_landscape_model(self):
        """SocialEnergyEngine should load the landscape model."""
        engine = SocialEnergyEngine(
            range_type="bipolar", temperature=0.05, lambda_social=0.5,
            gini_coefficient=0.35, seed=42,
        )
        assert engine._landscape_model is not None

    def test_engine_propose_landscape(self):
        """Engine should be able to propose landscape parameters."""
        engine = SocialEnergyEngine(
            range_type="bipolar", temperature=0.05, lambda_social=0.5,
            gini_coefficient=0.35, seed=42,
        )
        result = engine.propose_landscape({
            "polarization": 0.4,
            "delta_p1": 0.01,
            "delta_p5": 0.005,
            "skewness": 0.2,
            "gini": 0.35,
        })
        assert result is not None
        new_attractors, new_repellers = result
        assert len(new_attractors) == 1
        assert len(new_repellers) == 1
        assert "position" in new_attractors[0]
        assert "strength" in new_attractors[0]
        assert "position" in new_repellers[0]
        assert "strength" in new_repellers[0]

    def test_engine_fallback_without_model(self):
        """Engine should fall back to None when landscape model unavailable."""
        engine = SocialEnergyEngine(
            range_type="bipolar", temperature=0.05, lambda_social=0.5,
            gini_coefficient=0.35, seed=42,
        )
        engine._landscape_model = None
        result = engine.propose_landscape({
            "polarization": 0.4, "delta_p1": 0.01, "delta_p5": 0.005,
            "skewness": 0.2, "gini": 0.35,
        })
        assert result is None

    def test_router_status_includes_landscape(self):
        """Router status should include landscape_corrector."""
        CfCRouter._instance = None
        router = CfCRouter.get()
        status = router.status
        assert "landscape_corrector" in status
        assert status["landscape_corrector"] is True

    def test_ewx_fallback_multiplier(self):
        """Rule-based fallback multiplier should be computed from boolean flags."""
        # Only one flag
        flags = {"high_variance": True}
        assert _ews_fallback_multiplier(flags) == pytest.approx(1.5)

        flags = {"high_autocorr": True}
        assert _ews_fallback_multiplier(flags) == pytest.approx(1.3)

        flags = {"high_skewness": True}
        assert _ews_fallback_multiplier(flags) == pytest.approx(1.2)

        # No flags
        flags = {}
        assert _ews_fallback_multiplier(flags) == pytest.approx(1.0)

        # All three flags: 1.5 * 1.3 * 1.2 = 2.34, capped at 2.0
        flags = {"high_variance": True, "high_autocorr": True, "high_skewness": True}
        assert _ews_fallback_multiplier(flags) == pytest.approx(2.0)
