"""
Tests for the Game Theory Layer (Strategic Force).

Covers:
  - GamePayoff and StrategicConfig schemas
  - calculate_strategic_force() logic for both opinion ranges
  - Integration with simular() (end-to-end opinion stays in range)
"""
import sys
import os
import unittest

import numpy as np

# Ensure project root is in path when running directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from massive.core.schemas import GamePayoff, StrategicConfig
from massive.core.utility_logic import calculate_strategic_force


class TestGamePayoff(unittest.TestCase):

    def test_default_values(self):
        gp = GamePayoff()
        self.assertEqual(gp.cc,  1.0)
        self.assertEqual(gp.cd, -1.0)
        self.assertEqual(gp.dc,  1.0)
        self.assertEqual(gp.dd, -1.0)

    def test_custom_values(self):
        gp = GamePayoff(cc=2.0, cd=-0.5, dc=1.5, dd=0.0)
        self.assertEqual(gp.cc, 2.0)
        self.assertEqual(gp.cd, -0.5)
        self.assertEqual(gp.dc, 1.5)
        self.assertEqual(gp.dd, 0.0)


class TestStrategicConfig(unittest.TestCase):

    def test_disabled_by_default(self):
        sc = StrategicConfig()
        self.assertFalse(sc.enabled)

    def test_default_weight(self):
        sc = StrategicConfig()
        self.assertAlmostEqual(sc.strategic_weight, 0.3)

    def test_default_payoff_matrix(self):
        sc = StrategicConfig()
        self.assertIsInstance(sc.payoff_matrix, GamePayoff)

    def test_enable_strategic(self):
        sc = StrategicConfig(enabled=True, strategic_weight=0.5)
        self.assertTrue(sc.enabled)
        self.assertAlmostEqual(sc.strategic_weight, 0.5)


class TestCalculateStrategicForce(unittest.TestCase):
    """
    Test the core Game Theory force function.

    Calibrated for the [-1, 1] bipolar range (neutral = 0).
    The proximity_threshold default of 0.2 means |avg_neighbor| < 0.2
    is "near consensus" — exactly matching the proposal specification.
    """

    def setUp(self):
        self.matrix = GamePayoff(cc=1.0, cd=-1.0, dc=1.0, dd=-1.0)

    # ── Empty neighbours ──────────────────────────────────────────

    def test_empty_neighbors_returns_zero(self):
        force = calculate_strategic_force(0.5, [], self.matrix)
        self.assertEqual(force, 0.0)

    # ── Bipolar range [-1, 1], neutral = 0 ───────────────────────

    def test_neighbors_near_neutral_bipolar(self):
        """Neighbours within |avg| < 0.2 of neutral=0 → cooperation incentive."""
        # avg = 0.1, |0.1 - 0| = 0.1 < 0.2 → return cc - dc = 1.0 - 1.0 = 0.0
        force = calculate_strategic_force(
            0.5, [0.1, 0.1], self.matrix, neutral=0.0
        )
        self.assertAlmostEqual(force, self.matrix.cc - self.matrix.dc)

    def test_neighbors_far_from_neutral_bipolar(self):
        """Neighbours far from neutral (polarised) → fragmentation incentive."""
        # avg = 0.8, |0.8 - 0| = 0.8 > 0.2 → return dd - cd = -1.0 - (-1.0) = 0.0
        force = calculate_strategic_force(
            -0.5, [0.8, 0.8], self.matrix, neutral=0.0
        )
        self.assertAlmostEqual(force, self.matrix.dd - self.matrix.cd)

    # ── Probabilistic range [0, 1], neutral = 0.5 ─────────────────

    def test_neighbors_near_neutral_probabilistic(self):
        """For [0,1] range: |avg - 0.5| < 0.2 means near consensus."""
        # avg = 0.5, |0.5 - 0.5| = 0.0 < 0.2
        force = calculate_strategic_force(
            0.7, [0.5, 0.5], self.matrix, neutral=0.5
        )
        self.assertAlmostEqual(force, self.matrix.cc - self.matrix.dc)

    def test_neighbors_far_from_neutral_probabilistic(self):
        """For [0,1] range: |avg - 0.5| >= 0.2 means polarised."""
        # avg = 0.9, |0.9 - 0.5| = 0.4 > 0.2
        force = calculate_strategic_force(
            0.2, [0.9, 0.9], self.matrix, neutral=0.5
        )
        self.assertAlmostEqual(force, self.matrix.dd - self.matrix.cd)

    # ── Boundary at threshold ──────────────────────────────────────

    def test_exactly_at_threshold_is_far(self):
        """avg exactly at threshold should be treated as NOT near neutral."""
        # avg = 0.2 from neutral=0 → abs(0.2 - 0) = 0.2, NOT < 0.2
        force = calculate_strategic_force(
            0.0, [0.2, 0.2], self.matrix, neutral=0.0
        )
        self.assertAlmostEqual(force, self.matrix.dd - self.matrix.cd)

    # ── Prisoner's Dilemma payoff ──────────────────────────────────

    def test_prisoners_dilemma_consensus_incentive(self):
        """Prisoner's Dilemma: when neighbours near consensus, cc > dc gives negative force."""
        pd_payoff = GamePayoff(cc=1.0, cd=-1.0, dc=1.0, dd=-0.5)
        force = calculate_strategic_force(
            0.0, [0.05, -0.05], pd_payoff, neutral=0.0
        )
        # cc - dc = 1.0 - 1.0 = 0.0
        self.assertAlmostEqual(force, pd_payoff.cc - pd_payoff.dc)

    def test_prisoners_dilemma_fragmentation_incentive(self):
        """Prisoner's Dilemma: polarised neighbours → dd - cd = -0.5 - (-1.0) = 0.5."""
        pd_payoff = GamePayoff(cc=1.0, cd=-1.0, dc=1.0, dd=-0.5)
        force = calculate_strategic_force(
            0.0, [0.9, 0.9], pd_payoff, neutral=0.0
        )
        self.assertAlmostEqual(force, pd_payoff.dd - pd_payoff.cd)


class TestStrategicIntegration(unittest.TestCase):
    """Integration tests: strategic layer active inside simular()."""

    def setUp(self):
        np.random.seed(42)

    def _estado_bipolar(self):
        return {
            "opinion":           0.0,
            "propaganda":        0.4,
            "confianza":         0.5,
            "opinion_grupo_a":   0.65,
            "opinion_grupo_b":  -0.55,
            "pertenencia_grupo": 0.6,
        }

    def test_simular_strategic_disabled_stays_in_range(self):
        from simulator import simular
        hist = simular(
            self._estado_bipolar(),
            pasos=10,
            cada_n_pasos=5,
            config={"rango": "[-1, 1] — Bipolar"},
            verbose=False,
        )
        self.assertTrue(all(-1.0 <= h["opinion"] <= 1.0 for h in hist))

    def test_simular_strategic_enabled_stays_in_range(self):
        from simulator import simular
        config = {
            "rango": "[-1, 1] — Bipolar",
            "strategic": {
                "enabled": True,
                "payoff_matrix": {"cc": 1.0, "cd": -1.0, "dc": 1.0, "dd": -1.0},
                "strategic_weight": 0.3,
            },
        }
        hist = simular(
            self._estado_bipolar(),
            pasos=20,
            cada_n_pasos=5,
            config=config,
            verbose=False,
        )
        self.assertEqual(len(hist), 21)
        self.assertTrue(all(-1.0 <= h["opinion"] <= 1.0 for h in hist))

    def test_simular_strategic_weight_zero_produces_valid_history(self):
        """With ω=0 the strategic delta is zero; simulation must still stay in range."""
        from simulator import simular
        config = {
            "rango": "[-1, 1] — Bipolar",
            "strategic": {
                "enabled": True,
                "payoff_matrix": {"cc": 1.0, "cd": -1.0, "dc": 1.0, "dd": -1.0},
                "strategic_weight": 0.0,
            },
        }
        hist = simular(
            self._estado_bipolar(), pasos=10, cada_n_pasos=5,
            config=config, verbose=False,
        )
        self.assertEqual(len(hist), 11)
        self.assertTrue(all(-1.0 <= h["opinion"] <= 1.0 for h in hist))


if __name__ == "__main__":
    unittest.main()
