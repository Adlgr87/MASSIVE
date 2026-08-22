"""
Targeted coverage for uncovered scientific paths in energy_engine.py.

Covers: helper functions (_gaussian, _landscape_gradient, _landscape_energy),
SocialEnergyEngine economic/landscape setters, gini-adjusted and economic
landscape construction, full system_metrics branch (n_clusters via gap
threshold), random_network validation, and the scientific stepper path.
"""

import numpy as np
import pytest

from energy_engine import (
    SocialEnergyEngine,
    _gaussian,
    _landscape_energy,
    _landscape_gradient,
    random_network,
)

# ── Helper function coverage ───────────────────────────────────────────────

class TestEnergyHelpers:

    def test_gaussian_peak_at_center(self):
        assert _gaussian(0.0, 0.0) == pytest.approx(1.0)

    def test_gaussian_symmetric(self):
        assert _gaussian(0.3, 0.0) == pytest.approx(_gaussian(-0.3, 0.0))

    def test_gaussian_decays(self):
        assert _gaussian(0.5, 0.0) < _gaussian(0.1, 0.0)

    def test_landscape_gradient_zero_at_center_of_symmetric(self):
        attractors = [{"position": -0.5, "strength": 1.0}, {"position": 0.5, "strength": 1.0}]
        repellers = []
        grad = _landscape_gradient(0.0, attractors, repellers)
        assert grad == pytest.approx(0.0, abs=1e-12)

    def test_landscape_gradient_nonzero_offcenter(self):
        attractors = [{"position": 0.8, "strength": 2.0}]
        grad = _landscape_gradient(0.0, attractors, [])
        assert grad != 0.0

    def test_landscape_energy_at_attractor_minimum_is_negative(self):
        attractors = [{"position": 0.0, "strength": 3.0}]
        repellers = []
        e = _landscape_energy(0.0, attractors, repellers)
        assert e < 0.0

    def test_landscape_energy_at_repeller_is_positive(self):
        attractors = []
        repellers = [{"position": 0.0, "strength": 2.0}]
        e = _landscape_energy(0.0, attractors, repellers)
        assert e > 0.0

    def test_landscape_energy_empty_lists_zero(self):
        assert _landscape_energy(0.0, [], []) == 0.0


# ── Setters and economic landscapes ────────────────────────────────────────

class TestEnergySettersAndLandscapes:

    def test_set_gini_coefficient_clamps_high(self):
        eng = SocialEnergyEngine(gini_coefficient=0.3)
        eng.set_gini_coefficient(1.5)
        assert eng.gini_coefficient == 1.0

    def test_set_gini_coefficient_clamps_low(self):
        eng = SocialEnergyEngine(gini_coefficient=0.3)
        eng.set_gini_coefficient(-0.4)
        assert eng.gini_coefficient == 0.0

    def test_set_inequality_factor_min_one(self):
        eng = SocialEnergyEngine(inequality_factor=1.2, lambda_social=0.4)
        eng.set_inequality_factor(0.5)
        assert eng.inequality_factor == 1.0

    def test_set_inequality_factor_adjusts_lambda(self):
        eng = SocialEnergyEngine(inequality_factor=1.0, lambda_social=0.4)
        eng.set_inequality_factor(2.0)
        assert eng.lambda_social == pytest.approx(0.4 + 0.1)

    def test_set_economic_potential(self):
        eng = SocialEnergyEngine()
        eng.set_economic_potential({"polarization_factor": 0.6, "income_scale": 2.0})
        assert eng.economic_potential["polarization_factor"] == 0.6

    def test_set_economic_potential_none_uses_empty(self):
        eng = SocialEnergyEngine()
        eng.set_economic_potential(None)
        assert eng.economic_potential == {}

    def test_create_gini_adjusted_landscape_scales_strengths(self):
        eng = SocialEnergyEngine(gini_coefficient=0.4, inequality_factor=1.3)
        base_a = [{"position": 0.5, "strength": 1.0}]
        base_r = [{"position": -0.5, "strength": 1.0}]
        a, r = eng.create_gini_adjusted_landscape(base_a, base_r)
        factor = 1.3 * 1.35
        assert a[0]["strength"] == pytest.approx(1.0 * factor)
        assert r[0]["strength"] == pytest.approx(1.0 * 1.3 * 0.75)

    def test_create_gini_adjusted_landscape_uses_economic_potential(self):
        eng = SocialEnergyEngine()
        eng.set_economic_potential({
            "polarization_factor": 0.5,
            "attractor_strength": 2.0,
            "repeller_strength": 1.0,
        })
        base_a = [{"position": 0.0, "strength": 1.0}]
        base_r = [{"position": 1.0, "strength": 1.0}]
        a, r = eng.create_gini_adjusted_landscape(base_a, base_r)
        assert a[0]["strength"] == pytest.approx(eng.inequality_factor * 2.0)
        assert r[0]["strength"] == pytest.approx(eng.inequality_factor * 1.0)

    def test_create_economic_landscape_single_attractor(self):
        eng = SocialEnergyEngine(gini_coefficient=0.4)
        attractors, repellers = eng.create_economic_landscape(
            mean_income=30000.0, n_attractors=1, n_repellers=1)
        assert len(attractors) == 1
        assert len(repellers) == 1
        assert attractors[0]["position"] == pytest.approx(0.0)

    def test_create_economic_landscape_strengths_grow_with_gini(self):
        eng_low = SocialEnergyEngine(gini_coefficient=0.1)
        eng_high = SocialEnergyEngine(gini_coefficient=0.8)
        attrs_low, _ = eng_low.create_economic_landscape(n_attractors=2, n_repellers=2)
        attrs_high, _ = eng_high.create_economic_landscape(n_attractors=2, n_repellers=2)
        assert attrs_high[0]["strength"] > attrs_low[0]["strength"]


# ── System metrics: cluster path ───────────────────────────────────────────

class TestSystemMetrics:

    def test_system_metrics_single_cluster(self):
        eng = SocialEnergyEngine(range_type="bipolar")
        opinions = np.array([0.0, 0.05, -0.05, 0.02, -0.03])
        metrics = eng.system_metrics(opinions, np.eye(5), [], [])
        assert metrics["n_clusters_approx"] == 1

    def test_system_metrics_multi_cluster(self):
        eng = SocialEnergyEngine(range_type="bipolar")
        opinions = np.array([-0.9, 0.9, -0.85, 0.88])
        metrics = eng.system_metrics(opinions, np.eye(4), [], [])
        assert metrics["n_clusters_approx"] >= 2

    def test_system_metrics_with_attractors_and_repellers(self):
        eng = SocialEnergyEngine(range_type="bipolar")
        opinions = np.array([0.0, 0.3, -0.3])
        attractors = [{"position": 0.3, "strength": 2.0}]
        repellers = [{"position": -0.3, "strength": 1.5}]
        metrics = eng.system_metrics(opinions, np.eye(3), attractors, repellers)
        assert metrics["energia_total"] != 0.0
        assert "energia_media" in metrics

    def test_system_metrics_unipolar_range(self):
        eng = SocialEnergyEngine(range_type="unipolar")
        opinions = np.array([0.1, 0.5, 0.9])
        metrics = eng.system_metrics(opinions, np.eye(3), [], [])
        assert 0.0 <= metrics["polarizacion"] <= 2.0


# ── Random network ─────────────────────────────────────────────────────────

class TestRandomNetwork:

    def test_connectivity_extreme_values(self):
        adj = random_network(8, connectivity=0.0, seed=1)
        assert adj.sum() == 0
        adj2 = random_network(8, connectivity=1.0, seed=1)
        assert adj2.sum() > 0


# ── Scientific stepper path ───────────────────────────────────────────────

class TestEnergyScientificStepper:

    def test_step_uses_scientific_stepper_when_configured(self):
        eng = SocialEnergyEngine(scientific_config={"solver": "euler_maruyama"}, seed=0)
        assert eng._stepper is not None
        opinions = np.array([0.0, 0.3, -0.3])
        adj = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=float)
        attractors = [{"position": 0.5, "strength": 2.0}]
        repellers = [{"position": -0.5, "strength": 1.5}]
        result = eng.step(opinions, adj, attractors, repellers, eta=0.01)
        assert result.shape == opinions.shape
        assert eng.last_numerical_diagnostics is not None

    def test_step_stepper_zero_temperature(self):
        eng = SocialEnergyEngine(
            temperature=0.0, scientific_config={"solver": "euler_maruyama"}, seed=1
        )
        opinions = np.array([0.1, 0.2, 0.3])
        adj = np.eye(3)
        result = eng.step(opinions, adj, [], [], eta=0.01)
        assert np.all(np.isfinite(result))

    def test_gini_default_and_clamp_in_init(self):
        eng = SocialEnergyEngine(gini_coefficient=5.0)
        assert eng.gini_coefficient == 1.0

    def test_inequality_factor_default_adjusts_lambda(self):
        eng = SocialEnergyEngine(lambda_social=0.5, inequality_factor=1.5)
        assert eng.lambda_social == pytest.approx(0.5 + 0.05)
