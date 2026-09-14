"""Tests for the unified metrics module — verifies the URCC contract."""

import numpy as np
import pytest

from metrics.unified_metrics import (
    calculate_polarization,
    calculate_mean_opinion,
    calculate_std_opinion,
    calculate_cooperation,
    polarization_velocity,
    polarization_gradient,
)


class TestUnifiedPolarization:
    """Verify that polarization is now consistent across the URCC definition."""

    def test_perfect_consensus_has_zero_polarization(self):
        """All agents share the same opinion → polarization = 0."""
        opinions = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        pol = calculate_polarization(opinions, range_type="bipolar")
        assert pol == pytest.approx(0.0, abs=1e-10)

    def test_perfect_split_has_max_polarization(self):
        """Agents split at extremes → polarization = 1.0 (bipolar)."""
        opinions = np.array([-1.0, -1.0, 1.0, 1.0])
        pol = calculate_polarization(opinions, range_type="bipolar")
        # std = 1.0, half_range = 1.0
        assert pol == pytest.approx(1.0, abs=1e-10)

    def test_polarization_independent_of_bias(self):
        """Same spread, different mean → same polarization."""
        spread = np.array([-0.4, -0.2, 0.2, 0.4])
        shifted = np.array([0.2, 0.4, 0.8, 1.0])  # same spread, shifted by +0.6
        pol1 = calculate_polarization(spread, range_type="bipolar")
        pol2 = calculate_polarization(shifted, range_type="bipolar")
        assert pol1 == pytest.approx(pol2, abs=1e-10)

    def test_polarization_consistency_bipolar_unipolar(self):
        """Cross-check: std/half_range gives same normalized value."""
        bipolar_op = np.linspace(-1, 1, 100)
        unipolar_op = (bipolar_op + 1) / 2  # map to [0, 1]

        pol_bi = calculate_polarization(bipolar_op, range_type="bipolar")
        pol_uni = calculate_polarization(unipolar_op, range_type="unipolar")
        assert pol_bi == pytest.approx(pol_uni, abs=1e-10)

    def test_polarization_matches_energy_engine_formula(self):
        """Old energy_engine.py:475 formula = std / half_range."""
        opinions = np.array([-0.8, -0.3, 0.1, 0.6, 0.9])
        std = np.std(opinions)
        half_range = 1.0  # bipolar [-1, 1]
        expected = std / half_range
        assert calculate_polarization(opinions, range_type="bipolar") == pytest.approx(expected)

    def test_polarization_bounded(self):
        """Polarization must be in [0, 1]."""
        # Pathological case where std > half_range
        opinions = np.array([-1.0, 1.0])
        pol = calculate_polarization(opinions, range_type="bipolar")
        assert 0.0 <= pol <= 1.0

    def test_polarization_empty(self):
        opinions = np.array([])
        assert calculate_polarization(opinions) == 0.0


class TestPolarizationVelocity:
    def test_accelerating_polarization_positive(self):
        history = [0.1, 0.2, 0.3, 0.5, 0.7, 0.9]
        v = polarization_velocity(history, n_steps=3)
        assert v > 0.0

    def test_stabilizing_polarization_negative(self):
        history = [0.9, 0.7, 0.5, 0.3, 0.2, 0.1]
        v = polarization_velocity(history, n_steps=3)
        assert v < 0.0

    def test_short_history(self):
        assert polarization_velocity([0.5]) == 0.0
        assert polarization_velocity([]) == 0.0


class TestPolarizationGradient:
    def test_gradient_sums_near_zero(self):
        """Per-agent contributions should sum near 0 (relative to mean)."""
        opinions = np.array([-0.8, -0.4, 0.0, 0.4, 0.8])
        grad = polarization_gradient(opinions, range_type="bipolar")
        assert abs(grad.sum()) < 1e-10


class TestOtherMetrics:
    def test_mean_opinion_clipped(self):
        opinions = np.array([-2.0, 3.0])
        # mean = 0.5, already in [-1, 1]
        assert calculate_mean_opinion(opinions, range_type="bipolar") == pytest.approx(0.5)

    def test_mean_opinion_clipped_to_max(self):
        opinions = np.array([2.0, 3.0])
        # mean = 2.5, clips to 1.0
        assert calculate_mean_opinion(opinions, range_type="bipolar") == 1.0

    def test_std_opinion(self):
        opinions = np.array([0.0, 1.0])
        assert calculate_std_opinion(opinions) == pytest.approx(0.5)

    def test_cooperation_mean(self):
        coop = np.array([0.3, 0.5, 0.7, 0.9])
        assert calculate_cooperation(coop) == pytest.approx(0.6)

    def test_cooperation_empty(self):
        assert calculate_cooperation(np.array([])) == 0.0
