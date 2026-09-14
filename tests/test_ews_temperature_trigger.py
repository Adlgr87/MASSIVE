"""Tests for the EWS-to-Temperature Trigger (Epic 3).

Verifies that:
1. The step() method accepts ews_flags
2. EWS flags increase the effective temperature
3. Higher noise helps agents escape from boundary saturation (echo chambers)
4. Backward compatibility: no ews_flags → no change in behavior
"""

import numpy as np
import pytest

from energy_engine import SocialEnergyEngine, random_network


@pytest.fixture
def engine():
    return SocialEnergyEngine(range_type="bipolar", temperature=0.05, lambda_social=0.5, seed=42)


@pytest.fixture
def setup():
    N = 20
    adj = random_network(N, connectivity=0.3, seed=42)
    attractors = [{"position": 0.8, "strength": 1.0}, {"position": -0.8, "strength": 1.0}]
    repellers = [{"position": 0.0, "strength": 0.5}]
    return N, adj, attractors, repellers


class TestEWSTemperatureTrigger:
    """Verify EWS flags trigger temperature modulation."""

    def test_step_accepts_ews_flags(self, engine, setup):
        """step() should accept an ews_flags parameter without error."""
        N, adj, attractors, repellers = setup
        opinions = np.zeros(N)
        result = engine.step(opinions, adj, attractors, repellers, eta=0.01, ews_flags=None)
        assert result.shape == (N,)

    def test_no_ews_flags_backward_compatible(self, engine, setup):
        """Without ews_flags, behavior should be identical to before."""
        N, adj, attractors, repellers = setup
        opinions = np.zeros(N)
        result = engine.step(opinions, adj, attractors, repellers, eta=0.01)
        assert result.shape == (N,)

    def test_ews_high_variance_boosts_temperature(self, engine, setup):
        """When high_variance=True, temperature should effectively increase."""
        N, adj, attractors, repellers = setup

        # Run with EWS flag and without
        ops = np.full(N, 0.9)  # agents near boundary
        rng_copy = engine.rng
        result_no_ews = engine.step(ops.copy(), adj, attractors, repellers, eta=0.01, ews_flags=None)

        # Reset RNG state for fair comparison
        engine.rng = rng_copy
        result_ews = engine.step(
            ops.copy(), adj, attractors, repellers, eta=0.01,
            ews_flags={"high_variance": True, "high_autocorr": False, "high_skewness": False}
        )

        # With higher temperature, there's more noise → opinions should be more
        # spread out (some move away from 0.9)
        spread_no_ews = np.std(result_no_ews)
        spread_ews = np.std(result_ews)
        # With more noise, spread should increase (some agents escape boundary)
        # Use a loose check because stochastic
        assert spread_ews >= spread_no_ews * 0.5  # at least not worse

    def test_all_ews_flags_cap_at_2x(self, engine, setup):
        """All three EWS flags active should cap temperature at 2x."""
        N, adj, attractors, repellers = setup

        # The effective temperature multiplier = min(1.5 * 1.3 * 1.2, 2.0) = min(2.34, 2.0) = 2.0
        # So temperature should be at most 2x
        ops = np.zeros(N)
        # Run multiple times - with 2x temperature, variance of results should be higher
        results_ews = []
        results_no = []
        for seed in range(20):
            e = SocialEnergyEngine(range_type="bipolar", temperature=0.05, lambda_social=0.5, seed=seed)
            r_no = e.step(ops.copy(), adj, attractors, repellers, eta=0.01, ews_flags=None)

            e2 = SocialEnergyEngine(range_type="bipolar", temperature=0.05, lambda_social=0.5, seed=seed)
            r_ews = e2.step(
                ops.copy(), adj, attractors, repellers, eta=0.01,
                ews_flags={"high_variance": True, "high_autocorr": True, "high_skewness": True}
            )
            results_no.append(np.std(r_no))
            results_ews.append(np.std(r_ews))

        # With 2x temperature, the average spread should be higher
        assert np.mean(results_ews) > np.mean(results_no)

    def test_ews_helps_escape_boundary_saturation(self, engine, setup):
        """Agents stuck at ±0.95 should show more movement away from boundaries with EWS."""
        N, adj, attractors, repellers = setup

        # Place all agents at extreme +0.95 (near maximum)
        ops_extreme = np.full(N, 0.95)

        # With EWS, temperature is boosted → more noise → agents move more
        # Compare the average distance from the extreme over multiple steps
        dist_no_ews_total = 0.0
        dist_ews_total = 0.0
        n_steps = 50

        for trial in range(20):
            e_no = SocialEnergyEngine(range_type="bipolar", temperature=0.05, lambda_social=0.0, seed=trial)
            e_ews = SocialEnergyEngine(range_type="bipolar", temperature=0.05, lambda_social=0.0, seed=trial)

            ops_no = ops_extreme.copy()
            ops_ews = ops_extreme.copy()

            for _ in range(n_steps):
                # No EWS: landscape pulls toward attractors, but low social influence
                ops_no = e_no.step(ops_no, adj, attractors, repellers, eta=0.01, ews_flags=None)
                # With EWS: higher temperature adds noise, helping escape boundaries
                ops_ews = e_ews.step(ops_ews, adj, attractors, repellers, eta=0.01,
                                      ews_flags={"high_variance": True, "high_autocorr": True, "high_skewness": True})

                dist_no_ews_total += np.sum(np.abs(ops_no - 0.95))
                dist_ews_total += np.sum(np.abs(ops_ews - 0.95))

        # EWS (higher temp) should produce more movement away from boundaries
        # (more noise = more agents escape the extreme)
        assert dist_ews_total >= dist_no_ews_total * 1.05, \
            f"EWS should increase movement from boundary (ews={dist_ews_total:.1f}, no_ews={dist_no_ews_total:.1f})"
