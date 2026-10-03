"""Correlation-invariant tests: direction & magnitude of cross-variable effects.

These tests lock the *sign and scale* of the relationships between
environment variables (Gini, budget balance, social pressure, …) and the
engine parameters they drive, so a regression that inverts or doubles a
correlation fails loudly.

Covered invariants:
  1. Range label → metric magnitude (bipolar half_range = 1.0, unipolar 0.5)
  2. Gini → income dispersion (monotonic ↑; mean income decoupled from Gini)
  3. Budget balance → fiscal feasibility (deficit ↓, surplus ↑)
  4. Gini → landscape sharpness σ (Gini ↑ → σ ↓, anchored at default)
  5. Inequality factor → lambda_social (network weight ↑ with inequality)
  6. Social pressure (homogeneity) → conformist coupling (↑)
"""

from __future__ import annotations

import numpy as np
import pytest

from energy_engine import SocialEnergyEngine, effective_sigma
from massive.core.factbook.context import CountryData
from massive_engine import MassiveEngine, MassiveSimEngine
from simulator import DEFAULT_CONFIG, resumen_historial

# ── 1. Range label → metric magnitude (was: 2× error in bipolar) ────────────


class TestRangeMetricMagnitude:
    def test_bipolar_partisanship_correct_magnitude(self):
        """In [-1, 1] with neutral 0, opinions [0.2, 0.4, 0.6] → 0.4 (not 0.8)."""
        cfg = {**DEFAULT_CONFIG, "rango": "[-1, 1] — Bipolar"}
        hist = [{"opinion": v, "_regla_nombre": "lineal"} for v in [0.2, 0.4, 0.6]]
        assert resumen_historial(hist, cfg)["polarizacion_media"] == pytest.approx(0.4)

    def test_unipolar_partisanship_correct_magnitude(self):
        """In [0, 1] with neutral 0.5, opinions [0.2, 0.4, 0.6] → 1/3."""
        cfg = {**DEFAULT_CONFIG, "rango": "[0, 1] — Probabilístico"}
        hist = [{"opinion": v, "_regla_nombre": "lineal"} for v in [0.2, 0.4, 0.6]]
        assert resumen_historial(hist, cfg)["polarizacion_media"] == pytest.approx(1 / 3)

    def test_same_dispersion_same_polarization_across_ranges(self):
        """std-based polarization must be range-normalized (URCC contract)."""
        from metrics.unified_metrics import calculate_polarization

        bi = calculate_polarization(np.array([-0.4, 0.0, 0.4]), "bipolar")
        uni = calculate_polarization(np.array([0.3, 0.5, 0.7]), "unipolar")
        assert bi == pytest.approx(uni, abs=1e-12)


# ── 2. Gini → income dispersion ──────────────────────────────────────────────


class TestGiniIncomeDispersion:
    @pytest.mark.parametrize("g_lo,g_hi", [(0.1, 0.4), (0.4, 0.7), (0.7, 0.95)])
    def test_dispersion_monotonic_in_gini(self, g_lo, g_hi):
        inc_lo = MassiveEngine({"n_agents": 3000, "seed": 7, "gini_coefficient": g_lo}).agents[:, 3]
        inc_hi = MassiveEngine({"n_agents": 3000, "seed": 7, "gini_coefficient": g_hi}).agents[:, 3]
        assert inc_hi.std() > inc_lo.std(), f"dispersion must increase with Gini ({g_lo} → {g_hi})"

    def test_mean_income_decoupled_from_gini(self):
        """Gini measures concentration, not poverty: mean stays ~0.5."""
        for g in (0.1, 0.5, 0.9):
            inc = MassiveEngine({"n_agents": 3000, "seed": 7, "gini_coefficient": g}).agents[:, 3]
            assert inc.mean() == pytest.approx(0.5, abs=0.05)

    def test_extreme_gini_bounds(self):
        """g=0 → (near-)degenerate; g=1 → maximal spread (bimodal)."""
        eq = MassiveEngine({"n_agents": 3000, "seed": 7, "gini_coefficient": 0.0}).agents[:, 3]
        mx = MassiveEngine({"n_agents": 3000, "seed": 7, "gini_coefficient": 1.0}).agents[:, 3]
        assert eq.std() < 0.1
        assert mx.std() > 0.4


# ── 3. Budget balance → fiscal feasibility ───────────────────────────────────


class TestFiscalFeasibility:
    def _feasibility(self, surplus: float, revenues: float = 1e12) -> float:
        c = CountryData(budget_surplus_deficit=surplus, budget_revenues=revenues)
        return c.massive_params["fiscal_constraint"]

    def test_deficit_below_balanced_below_surplus(self):
        d = self._feasibility(-1e11)
        b = self._feasibility(0.0)
        s = self._feasibility(1e11)
        assert d < b < s

    def test_more_deficit_less_feasibility(self):
        assert self._feasibility(-4e11) < self._feasibility(-1e11)

    def test_more_surplus_more_feasibility(self):
        assert self._feasibility(4e11) > self._feasibility(1e11)

    def test_default_country_is_moderate_deficit(self):
        """Default data (−10% revenues) → feasibility below 0.5."""
        assert self._feasibility(-0.1e12) == pytest.approx(0.30)


# ── 4. Gini → landscape sharpness ────────────────────────────────────────────


class TestGiniLandscapeSharpness:
    def test_sigma_decreases_monotonically_with_gini(self):
        sigmas = [effective_sigma(g) for g in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)]
        assert all(a > b for a, b in zip(sigmas, sigmas[1:], strict=False))

    def test_sigma_anchored_at_default_gini(self):
        """gini = 0.35 (default) keeps the historical σ = 0.3."""
        assert effective_sigma(0.35) == pytest.approx(0.3)

    def test_engine_constructor_accepts_gini(self):
        eng = SocialEnergyEngine(gini_coefficient=0.6, seed=1)
        assert eng.gini_coefficient == 0.6

    def test_sharper_well_pulls_harder_near_center(self):
        """Closer to a well center, a sharper (high-Gini) landscape pulls more."""
        base = {"position": 0.5, "strength": 2.0}
        opinions = np.array([0.42])  # near the attractor center
        adj = np.array([[0.0]])
        pulls = {}
        for g in (0.1, 0.9):
            eng = SocialEnergyEngine(gini_coefficient=g, temperature=0.0, seed=3)
            nxt = eng.step(opinions.copy(), adj, [dict(base)], [], eta=0.05)
            pulls[g] = abs(nxt[0] - 0.42)
        assert pulls[0.9] > pulls[0.1], "high Gini → sharper well → stronger pull near center"


# ── 5. Inequality factor → lambda_social ─────────────────────────────────────


class TestInequalityLambda:
    def test_higher_inequality_more_network_weight(self):
        lo = SocialEnergyEngine(lambda_social=0.5, inequality_factor=1.1, seed=1)
        hi = SocialEnergyEngine(lambda_social=0.5, inequality_factor=1.9, seed=1)
        assert hi.lambda_social > lo.lambda_social

    def test_inequality_adjustment_scale(self):
        eng = SocialEnergyEngine(lambda_social=0.5, inequality_factor=1.5, seed=1)
        # adjustment = (1.5 - 1.0) * 0.1
        assert eng.lambda_social == pytest.approx(0.55)


# ── 6. Social pressure → conformist coupling ─────────────────────────────────


class TestSocialPressureCoupling:
    def test_neutral_pressure_keeps_coupling(self):
        eng = MassiveSimEngine(N=100, M=20, seed=1, social_pressure=0.5)
        assert eng.coupling == pytest.approx(0.3)

    def test_homogeneous_society_stronger_coupling(self):
        hom = MassiveSimEngine(N=100, M=20, seed=1, social_pressure=1.0)
        plur = MassiveSimEngine(N=100, M=20, seed=1, social_pressure=0.0)
        assert hom.coupling > plur.coupling
        assert hom.coupling == pytest.approx(0.3 * 1.2)
        assert plur.coupling == pytest.approx(0.3 * 0.8)

    def test_massive_engine_derives_pressure_from_weights(self):
        fb = MassiveEngine(
            {
                "n_agents": 50,
                "seed": 1,
                "social_pressure_weights": {"ethnic": 0.9, "religious": 0.7},
            }
        )
        assert fb.social_pressure == pytest.approx(0.8)

    def test_massive_engine_defaults_to_neutral_pressure(self):
        assert MassiveEngine({"n_agents": 50, "seed": 1}).social_pressure == 0.5
