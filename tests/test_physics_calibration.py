"""
Tests for Layer 2 physics-equation calibration (A4 — Statistical Physicist).

Covers the six required verification cases:
  1. YAML loads and validates against the PhysicsParams schema.
  2. All opinion-range parameters clipped to [-1, 1].
  3. Langevin ∇V pushes opinions toward attractors (gradient-descent direction).
  4. HK epsilon values fall in the [0.20, 0.35] bounded-confidence band.
  5. DeGroot W is row-stochastic (rows sum to 1).
  6. DeGroot W is consistent with authority asymmetry.

Conventions: pytest class-based tests, deterministic seeds, np.clip on every
opinion-domain quantity.
"""

from __future__ import annotations

import os

import numpy as np
import pytest
import yaml

from massive.core.physics_calibration import (
    degroot_weight_matrix,
    get_physics_params,
    hk_epsilon_distribution,
    langevin_drift,
)
from massive.core.schemas import PhysicsParams

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "configs",
    "calibrated",
    "physics_params_v1.0.0.yaml",
)

# Opinion spectrum bounds used throughout MASSIVE.
OPINION_MIN = -1.0
OPINION_MAX = 1.0


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture(scope="module")
def physics_params() -> PhysicsParams:
    """Load + validate the calibration artefact once per module."""
    return get_physics_params("mixed", path=CONFIG_PATH)


@pytest.fixture
def params() -> PhysicsParams:
    """Fresh per-test validated params (mixed segment)."""
    return get_physics_params("mixed", path=CONFIG_PATH)


# ============================================================
# TEST 1 — YAML loads and validates against the schema
# ============================================================


class TestPhysicsParamsYaml:

    def test_yaml_loads_and_validates(self):
        """The YAML artefact loads and passes PhysicsParams validation."""
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        params = PhysicsParams.model_validate(raw)
        assert params.meta.version == "1.0.0"
        assert params.meta.layer == 2

    def test_extra_forbid_rejects_unknown_top_keys(self):
        """extra='forbid' must reject unexpected top-level keys."""
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        raw["bogus_section"] = 1.0
        with pytest.raises(Exception):
            PhysicsParams.model_validate(raw)

    def test_get_physics_params_validates_segment(self):
        """get_physics_params validates that the segment is resolvable."""
        params = get_physics_params("age:old", path=CONFIG_PATH)
        # Resolves without error and carries the active segment.
        assert getattr(params, "_active_segment", None) == "age:old"

    def test_get_physics_params_rejects_unknown_segment(self):
        """An unknown segment label raises KeyError (fail-fast)."""
        with pytest.raises(KeyError):
            get_physics_params("species:alien", path=CONFIG_PATH)

    def test_traceability_fields_present(self, params: PhysicsParams):
        """Every calibrated entry carries the five traceability fields."""

        def check(entry):
            assert hasattr(entry, "value")
            assert hasattr(entry, "sem")
            assert hasattr(entry, "source_dataset") is True
            assert entry.source_dataset in {"A1", "A2", "A3", "A1+A3", "numerical"}
            assert entry.estimation_method in {
                "least_squares_fit",
                "maximum_likelihood",
                "method_of_moments",
                "fixed",
            }
            assert isinstance(entry.empirical_reference, str) and entry.empirical_reference

        # Sample representative leaves across all six parameter groups.
        check(params.langevin.drift.opinion_attractors)
        check(params.langevin.drift.cognitive_rigidity.mixed)
        check(params.langevin.drift.cognitive_rigidity.age["young"])
        check(params.langevin.drift.cognitive_rigidity.education["high_edu"])
        check(params.langevin.drift.cognitive_rigidity.income["low_inc"])
        check(params.langevin.sigma.base)
        check(params.langevin.sigma.context_volatility_sensitivity)
        check(params.langevin.sigma.segment_multiplier.age["old"])
        check(params.lambda_social)
        check(params.temperature)
        check(params.hk.epsilon.base)
        check(params.hk.epsilon.per_segment.age["young"])
        check(params.degroot.authority_exponent)
        check(params.degroot.self_weight)


# ============================================================
# TEST 2 — All opinion-range parameters clipped to [-1, 1]
# ============================================================


class TestOpinionRangeBounds:

    def test_opinion_drift_attractors_in_range(self, params: PhysicsParams):
        """Opinion attractor positions live in [-1, 1]."""
        for pos in params.langevin.drift.opinion_attractors.value:
            assert OPINION_MIN <= pos <= OPINION_MAX

    def test_opinion_repeller_in_range(self, params: PhysicsParams):
        """Opinion repeller (barrier) positions live in [-1, 1]."""
        for pos in params.langevin.drift.opinion_repeller.value:
            assert OPINION_MIN <= pos <= OPINION_MAX

    def test_landscape_positions_in_range(self, params: PhysicsParams):
        """Energy-landscape attractor/repeller positions are in [-1, 1]."""
        for pos in params.langevin.attractors.positions:
            assert OPINION_MIN <= pos <= OPINION_MAX
        for pos in params.langevin.repellers.positions:
            assert OPINION_MIN <= pos <= OPINION_MAX

    def test_hk_band_in_range(self, params: PhysicsParams):
        """The HK epsilon band sits inside [-1, 1] (and within [0.20, 0.35])."""
        band = params.hk.epsilon.band
        for b in band:
            assert OPINION_MIN <= b <= OPINION_MAX
        assert band[0] >= 0.20 and band[1] <= 0.35

    def test_dimension_coupling_in_unit_range(self, params: PhysicsParams):
        """Per-dimension drift coupling scales mirror theta in [0, 1]."""
        for k, v in params.langevin.drift.dimension_coupling.items():
            assert 0.0 <= v <= 1.0, f"{k}={v} not in [0, 1]"

    def test_opinion_domain_fractions_in_unit_range(self, params: PhysicsParams):
        """Opinion-domain fractionals (rigidity, HK epsilon) sit in [0, 1].

        Noise multipliers may legitimately exceed 1.0 (they amplify sigma),
        so only the opinion-domain fractionals are range-checked here.
        """

        def _check(entry):
            v = entry.value
            assert isinstance(v, float), "expected a scalar fraction"
            assert 0.0 <= v <= 1.0, f"opinion-domain fraction {v} outside [0, 1]"

        for segset in (
            params.langevin.drift.cognitive_rigidity,
            params.hk.epsilon.per_segment,
        ):
            _check(segset.mixed)
            for axis in ("age", "education", "income"):
                for entry in getattr(segset, axis).values():
                    _check(entry)

    def test_sigma_multipliers_positive(self, params: PhysicsParams):
        """Noise multipliers are positive (> 0), though they may exceed 1.0."""
        segset = params.langevin.sigma.segment_multiplier

        def _check(entry):
            assert isinstance(entry.value, float)
            assert entry.value > 0.0

        _check(segset.mixed)
        for axis in ("age", "education", "income"):
            for entry in getattr(segset, axis).values():
                _check(entry)


# ============================================================
# TEST 3 — ∇V pushes opinions toward attractors (gradient descent)
# ============================================================


class TestLangevinDrift:

    def test_drift_sign_pushes_toward_positive_attractor(self, params: PhysicsParams):
        """For 0 < x < +0.7, ∇V < 0 so x - eta*∇V moves toward +0.7."""
        x = 0.3
        grad = langevin_drift(x, "mixed", params)
        # Gradient is negative between the barrier (0) and attractor (+0.7).
        assert grad < 0
        eta = 0.05
        x_next = x - eta * grad
        assert x_next > x  # moves up toward +0.7
        assert abs(x_next - 0.7) < abs(x - 0.7)  # closer to attractor

    def test_drift_sign_pushes_toward_negative_attractor(self, params: PhysicsParams):
        """For -0.7 < x < 0, ∇V > 0 so x - eta*∇V moves toward -0.7."""
        x = -0.4
        grad = langevin_drift(x, "mixed", params)
        assert grad > 0
        eta = 0.05
        x_next = x - eta * grad
        assert x_next < x  # moves down toward -0.7
        assert abs(x_next - (-0.7)) < abs(x - (-0.7))

    def test_drift_vanishes_at_barrier(self, params: PhysicsParams):
        """∇V = 0 at the central barrier x = 0 (unstable equilibrium)."""
        grad = langevin_drift(0.0, "mixed", params)
        assert grad == 0.0

    def test_drift_vanishes_at_attractor(self, params: PhysicsParams):
        """∇V = 0 at the attractors x = ±0.7 (stable equilibria)."""
        a = 0.7
        assert abs(langevin_drift(a, "mixed", params)) < 1e-12
        assert abs(langevin_drift(-a, "mixed", params)) < 1e-12

    def test_drift_clipped_to_opinion_range(self, params: PhysicsParams):
        """Out-of-range opinions are clipped to [-1, 1] before evaluation."""
        grad = langevin_drift(5.0, "mixed", params)
        assert np.isfinite(grad)

    def test_rigidity_scales_gradient_magnitude(self, params: PhysicsParams):
        """Older (more rigid) segments produce a stronger |∇V| at the same x."""
        x = 0.3
        g_young = abs(langevin_drift(x, "age:young", params))
        g_old = abs(langevin_drift(x, "age:old", params))
        assert g_old > g_young, "older cohort must be more cognitively rigid"

    def test_drift_direction_independent_of_segment(self, params: PhysicsParams):
        """The descent direction (sign) is segment-invariant for fixed x."""
        for seg in ("mixed", "age:old", "education:high_edu", "income:low_inc"):
            g = langevin_drift(0.3, seg, params)
            assert g < 0, f"segment {seg} produced non-negative gradient at x=0.3"


# ============================================================
# TEST 4 — HK epsilon values in the [0.20, 0.35] band
# ============================================================


class TestHKBand:

    def test_hk_distribution_within_band(self, params: PhysicsParams):
        """Every sampled HK ε lies in [0.20, 0.35]."""
        eps = hk_epsilon_distribution("mixed", params, n=1000)
        assert eps.ndim == 1
        assert np.all(eps >= 0.20)
        assert np.all(eps <= 0.35)

    def test_hk_distribution_per_segment_in_band(self, params: PhysicsParams):
        """All demographic segments respect the HK band."""
        for seg in (
            "mixed",
            "age:young",
            "age:old",
            "education:low_edu",
            "education:high_edu",
            "income:low_inc",
            "income:high_inc",
        ):
            eps = hk_epsilon_distribution(seg, params, n=500)
            assert np.all(eps >= 0.20), f"{seg} produced epsilon below 0.20"
            assert np.all(eps <= 0.35), f"{seg} produced epsilon above 0.35"

    def test_hk_band_matches_schema(self, params: PhysicsParams):
        """The schema band is exactly [0.20, 0.35]."""
        assert list(params.hk.epsilon.band) == [0.20, 0.35]

    def test_hk_distribution_is_deterministic(self, params: PhysicsParams):
        """Same seed reproduces the same distribution."""
        a = hk_epsilon_distribution("mixed", params, n=200, seed=42)
        b = hk_epsilon_distribution("mixed", params, n=200, seed=42)
        np.testing.assert_array_equal(a, b)


# ============================================================
# TEST 5 — DeGroot W is row-stochastic (rows sum to 1)
# ============================================================


class TestDeGrootsStochastic:

    def test_rows_sum_to_one(self, params: PhysicsParams):
        """Every row of W sums to 1.0 (row-stochastic)."""
        rng = np.random.default_rng(0)
        A = rng.random((20, 20))
        np.fill_diagonal(A, 0.0)
        auth = rng.random(20) * 10.0 + 1.0
        W = degroot_weight_matrix(A, auth, params)
        np.testing.assert_allclose(W.sum(axis=1), 1.0, atol=1e-12)

    def test_rows_sum_to_one_no_params(self):
        """Row-stochasticity holds even without a PhysicsParams object."""
        A = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=float)
        auth = np.array([3.0, 1.0, 2.0])
        W = degroot_weight_matrix(A, auth)
        np.testing.assert_allclose(W.sum(axis=1), 1.0, atol=1e-12)

    def test_weights_non_negative(self, params: PhysicsParams):
        """All weights are non-negative for a non-negative adjacency."""
        A = np.ones((10, 10))
        np.fill_diagonal(A, 0.0)
        auth = np.array([5.0, 4.0, 3.0, 2.0, 1.0, 5.0, 4.0, 3.0, 2.0, 1.0])
        W = degroot_weight_matrix(A, auth, params)
        assert np.all(W >= -1e-15)

    def test_shape_preserved(self, params: PhysicsParams):
        """W has the same shape as A."""
        A = np.zeros((8, 8))
        auth = np.ones(8)
        W = degroot_weight_matrix(A, auth, params)
        assert W.shape == A.shape


# ============================================================
# TEST 6 — DeGroot W is consistent with authority asymmetry
# ============================================================


class TestDeGrootAuthorityAsymmetry:

    def test_column_sums_correlate_with_authority(self, params: PhysicsParams):
        """On an in-degree-uniform graph, higher-authority nodes receive more
        total weight (column sums correlate with authority scores)."""
        N = 6
        A = np.ones((N, N), dtype=float)
        np.fill_diagonal(A, 0.0)  # complete directed graph -> equal in-degree
        auth = np.array([1.0, 2.0, 4.0, 8.0, 16.0, 32.0])
        W = degroot_weight_matrix(A, auth, params)
        colsum = W.sum(axis=0)
        corr = float(np.corrcoef(colsum, auth)[0, 1])
        assert corr > 0.9, f"column sums weakly correlated with authority: {corr}"

    def test_hub_receives_most_weight(self, params: PhysicsParams):
        """A high-authority hub that everyone points to gets the largest column sum."""
        N = 6
        A = np.zeros((N, N), dtype=float)
        # Every other node points to the hub (node 0).
        for j in range(1, N):
            A[j, 0] = 1.0
        auth = np.array([10.0, 1.0, 1.0, 1.0, 1.0, 1.0])
        W = degroot_weight_matrix(A, auth, params)
        colsum = W.sum(axis=0)
        assert colsum[0] == colsum.max(), "hub node must receive the most weight"

    def test_doubling_authority_increases_received_weight(self, params: PhysicsParams):
        """Ceteris paribus, doubling a node's authority increases its column sum."""
        N = 5
        A = np.ones((N, N), dtype=float)
        np.fill_diagonal(A, 0.0)
        base_auth = np.array([1.0, 2.0, 4.0, 8.0, 16.0])
        W1 = degroot_weight_matrix(A, base_auth, params)
        boosted = base_auth.copy()
        boosted[2] *= 2.0  # double node 2's authority
        W2 = degroot_weight_matrix(A, boosted, params)
        assert W2.sum(axis=0)[2] > W1.sum(axis=0)[2]
