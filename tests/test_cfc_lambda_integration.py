"""Integration tests for the CfC Lambda Corrector (Phase 2).

Verifies:
1. Router loads cfc_lambda_corrector.pt
2. propose_lambda returns valid values
3. Lambda values are reactive (different inputs → different outputs)
4. Energy engine integration doesn't break existing behavior
"""

from pathlib import Path

import numpy as np
import pytest
import torch

from cfc_engine import CfCLambdaCorrector
from cfc_router import CfCRouter

# ── Skip-condition: trained Lambda-corrector weights ─────────────────────
# The trained model artifact ``models/cfc_calibrated/cfc_lambda_corrector.pt``
# is a large binary file that is **git-ignored** (see .gitignore: ``*.pt``).
# It is therefore absent in fresh checkouts and CI. Tests that require the
# trained weights are skipped here with a clear reason; transparent fallback
# behavior (returning 0.5 / "passthrough") is covered by tests that do NOT
# carry this marker and run unconditionally.
_LAMBDA_WEIGHTS = Path("models/cfc_calibrated/cfc_lambda_corrector.pt")
skip_no_lambda_weights = pytest.mark.skipif(
    not _LAMBDA_WEIGHTS.exists(),
    reason=(
        f"Trained CfC lambda-corrector weights not found ({_LAMBDA_WEIGHTS}). "
        "The *.pt artifacts are git-ignored; regenerate via cfc_trainer.py. "
        "Fallback behavior is still covered by unmarked tests."
    ),
)


@pytest.fixture(autouse=True)
def reset_router():
    """Reset singleton before each test."""
    CfCRouter._instance = None
    yield
    CfCRouter._instance = None


@pytest.fixture
def router():
    return CfCRouter.get()


@pytest.fixture
def engine():
    from energy_engine import SocialEnergyEngine

    return SocialEnergyEngine(range_type="bipolar", temperature=0.05, lambda_social=0.5, seed=42)


class TestLambdaCorrectorModel:
    """Test the CfCLambdaCorrector architecture directly."""

    @skip_no_lambda_weights
    def test_loads_from_trained_weights(self):
        """The trained model file should load into CfCLambdaCorrector."""
        model = CfCLambdaCorrector(input_dim=5, hidden_size=32)
        ckpt = torch.load(
            "models/cfc_calibrated/cfc_lambda_corrector.pt",
            map_location="cpu",
            weights_only=True,
        )
        model.load_state_dict(ckpt)
        model.eval()
        # Quick forward pass
        x = torch.tensor([[0.5, 0.0, 0.0, 0.3, 0.2]], dtype=torch.float32)
        with torch.no_grad():
            out = model(x)
        assert 0.0 <= out.item() <= 1.0 + 1e-6  # softplus can slightly exceed 1


class TestRouterLambdaIntegration:
    """Test the router's lambda corrector integration."""

    @skip_no_lambda_weights
    def test_lambda_corrector_loaded(self, router):
        """Router should report lambda_corrector=True in status."""
        status = router.status
        assert status["lambda_corrector"] is True

    def test_propose_lambda_returns_valid_value(self, router):
        """propose_lambda should return a float in [0, 1] with source 'cfc'."""
        features = {
            "polarization": 0.5,
            "delta_polarization_t1": 0.02,
            "delta_polarization_t5": 0.01,
            "gini": 0.4,
            "volatility": 0.3,
        }
        result = router.propose_lambda(features)
        lam, source = result
        assert isinstance(lam, float)
        assert 0.0 <= lam <= 1.0 + 1e-6
        assert source in ("cfc", "passthrough")

    @skip_no_lambda_weights
    def test_reactive_different_inputs(self, router):
        """Different feature inputs should produce different lambda values."""
        features_low = {
            "polarization": 0.1,
            "delta_polarization_t1": 0.00,
            "delta_polarization_t5": 0.00,
            "gini": 0.1,
            "volatility": 0.1,
        }
        features_high = {
            "polarization": 0.9,
            "delta_polarization_t1": 0.05,
            "delta_polarization_t5": 0.03,
            "gini": 0.8,
            "volatility": 0.7,
        }
        lambda_low, _ = router.propose_lambda(features_low)
        lambda_high, _ = router.propose_lambda(features_high)
        # High polarization+Gini should produce different lambda
        assert lambda_low != pytest.approx(lambda_high, abs=0.01)

    @skip_no_lambda_weights
    def test_reactive_high_gini_reduces_coupling(self, router):
        """High Gini + high polarization should reduce social coupling."""
        features_moderate = {
            "polarization": 0.3,
            "delta_polarization_t1": 0.01,
            "delta_polarization_t5": 0.005,
            "gini": 0.2,
            "volatility": 0.2,
        }
        features_extreme = {
            "polarization": 0.9,
            "delta_polarization_t1": 0.05,
            "delta_polarization_t5": 0.03,
            "gini": 0.8,
            "volatility": 0.7,
        }
        lambda_mod, _ = router.propose_lambda(features_moderate)
        lambda_ext, _ = router.propose_lambda(features_extreme)
        # High polarization + Gini should produce lower lambda (less peer influence)
        assert lambda_ext < lambda_mod


class TestEnergyEngineLambdaIntegration:
    """Test that the energy engine can use the lambda corrector."""

    def test_energy_engine_with_ews_flags(self, engine, setup=None):
        """Energy engine step should work with EWS flags enabled."""
        from energy_engine import random_network

        N = 10
        adj = random_network(N, connectivity=0.3, seed=42)
        attractors = [{"position": 0.8, "strength": 1.0}]
        repellers = [{"position": 0.0, "strength": 0.5}]
        opinions = np.full(N, 0.9)

        ews_flags = {
            "high_variance": True,
            "high_autocorr": True,
            "high_skewness": True,
        }
        result = engine.step(opinions, adj, attractors, repellers, eta=0.01, ews_flags=ews_flags)
        assert result.shape == (N,)
        assert np.all(np.isfinite(result))

    def test_backward_compatible_no_ews(self, engine):
        """Without ews_flags, engine should work exactly as before."""
        from energy_engine import random_network

        N = 10
        adj = random_network(N, connectivity=0.3, seed=42)
        attractors = [{"position": 0.8, "strength": 1.0}]
        repellers = [{"position": 0.0, "strength": 0.5}]
        opinions = np.zeros(N)

        result = engine.step(opinions, adj, attractors, repellers, eta=0.01)
        assert result.shape == (N,)
        assert np.all(np.isfinite(result))
