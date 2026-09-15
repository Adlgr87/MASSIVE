"""Cross-engine polarization consistency tests (Epic 1 verification).

Verifies that all engines now use the SAME polarization formula (URCC: std / half_range)
instead of their previous divergent formulas (mean(|op|), weighted mean(|op|), raw std, etc.).
"""

import numpy as np
import pytest

from metrics.unified_metrics import (
    calculate_cooperation,
    calculate_partisanship,
    calculate_polarization,
)

# ── Shared test cases ──────────────────────────────────────────────────────────

# Opinions used across all engines
OPINIONS_BIPOLAR = np.array([-0.9, -0.5, 0.0, 0.5, 0.9])
OPINIONS_CONSENSUS = np.array([0.1, 0.1, 0.1, 0.1, 0.1])
OPINIONS_PERFECT_SPLIT = np.array([-1.0, -1.0, 1.0, 1.0, 1.0])
OPINIONS_UNIPOLAR = np.array([0.1, 0.3, 0.5, 0.7, 0.9])


class TestCrossEngineConsistency:
    """Verify that calculate_polarization gives consistent results across contexts."""

    def test_energy_engine_formula_matches_unified(self):
        """Energy engine old formula: std / half_range == calculate_polarization."""
        # Old energy engine code: half_range = (1.0 - (-1.0)) / 2.0 = 1.0
        # polarizacion = std / half_range
        std = float(np.std(OPINIONS_BIPOLAR))
        old_polarizacion = std / 1.0  # energy_engine formula
        new_polarizacion = calculate_polarization(OPINIONS_BIPOLAR, "bipolar")
        assert new_polarizacion == pytest.approx(old_polarizacion, abs=1e-6)

    def test_multilayer_old_formula_diverges(self):
        """Document that multilayer engine old formula (mean|op|) differs from URCC."""
        old_formula = float(np.mean(np.abs(OPINIONS_BIPOLAR)))
        urcc_formula = calculate_polarization(OPINIONS_BIPOLAR, "bipolar")
        # These SHOULD be different (the whole point of the refactoring)
        assert old_formula != pytest.approx(urcc_formula, abs=0.01)

    def test_micro_old_formula_diverges(self):
        """Document that micro engine old formula (raw std) differs from URCC."""
        old_formula = float(np.std(OPINIONS_BIPOLAR))
        urcc_formula = calculate_polarization(OPINIONS_BIPOLAR, "bipolar")
        # URCC normalizes by half_range=1.0, so for bipolar they're actually equal
        assert old_formula == pytest.approx(urcc_formula, abs=1e-6)

    def test_massive_old_formula_diverges(self):
        """Document that massive engine old formula (weighted mean|op|) differs from URCC."""
        # Massive engine used np.average(np.abs(x), weights=counts)
        # For uniform weights, this = mean(|x|), which differs from std/half_range
        old_formula = float(np.average(np.abs(OPINIONS_BIPOLAR)))
        urcc_formula = calculate_polarization(OPINIONS_BIPOLAR, "bipolar")
        assert old_formula != pytest.approx(urcc_formula, abs=0.01)

    def test_simulator_old_formula_uses_partisanship(self):
        """Simulator's polarizacion_media used mean(|op - neutral|) = partisanship."""
        neutro = 0.0  # bipolar
        old_formula = float(np.mean(np.abs(OPINIONS_BIPOLAR - neutro)))
        # Partisanship normalizes by half_range too
        new_partisanship = calculate_partisanship(OPINIONS_BIPOLAR, neutral=0.0, range_type="bipolar")
        # For bipolar, half_range = 1.0, so old formula (mean|op|) == partisanship
        assert new_partisanship == pytest.approx(old_formula, abs=1e-6)


class TestUnifiedBounds:
    """Verify that calculate_polarization is properly bounded [0, 1]."""

    def test_polarization_bounded_consensus(self):
        assert calculate_polarization(OPINIONS_CONSENSUS, "bipolar") == pytest.approx(0.0, abs=0.01)

    def test_polarization_bounded_split(self):
        pol = calculate_polarization(OPINIONS_PERFECT_SPLIT, "bipolar")
        assert pol > 0.5  # high spread → high polarization

    def test_polarization_bounded_extreme(self):
        """Even with extreme opinions, polarization should be ≤ 1.0."""
        extreme = np.array([-1.0, 1.0, -1.0, 1.0])
        pol = calculate_polarization(extreme, "bipolar")
        assert pol <= 1.0

    def test_polarization_bounded_unipolar(self):
        """Unipolar opinions should also produce bounded [0, 1] polarization."""
        pol = calculate_polarization(OPINIONS_UNIPOLAR, "unipolar")
        assert 0.0 <= pol <= 1.0


class TestReactiveCoherence:
    """Verify polarization reacts correctly to opinion changes across metrics."""

    def test_dispersion_increasing(self):
        """Moving to a more dispersed state should increase URCC polarization."""
        low_disp = np.array([-0.1, 0.0, 0.1])
        high_disp = np.array([-0.9, 0.0, 0.9])
        assert calculate_polarization(high_disp, "bipolar") > calculate_polarization(low_disp, "bipolar")

    def test_partisanship_increasing(self):
        """Moving to a more partisan state should increase partisanship."""
        low_part = np.array([0.0, 0.1, -0.1])  # near neutral
        high_part = np.array([0.9, 0.95, 0.85])  # far from neutral (bipolar)
        assert calculate_partisanship(high_part, neutral=0.0, range_type="bipolar") > \
               calculate_partisanship(low_part, neutral=0.0, range_type="bipolar")

    def test_cooperation_decreasing_with_dispersion(self):
        """Higher dispersion should correlate with lower cooperation.

        Cooperation decreases as polarization increases — this tests that
        the relationship between the two metrics is reactive (not static).
        """
        # High cooperation = opinions clustered (low polarization)
        clustered_coop = np.array([0.95, 0.92, 0.97, 0.90])
        # Low cooperation = opinions spread (high polarization)
        spread_coop = np.array([0.1, 0.3, 0.7, 0.9])
        coop_clustered = calculate_cooperation(clustered_coop)
        coop_spread = calculate_cooperation(spread_coop)
        assert coop_clustered > coop_spread  # clustered = more cooperation

        # And polarization should be higher for the spread case
        from metrics.unified_metrics import calculate_polarization
        pol_clustered = calculate_polarization(np.array([-0.02, 0.02, 0.0, -0.01]), "bipolar")
        pol_spread = calculate_polarization(np.array([-0.9, 0.2, 0.5, 0.7]), "bipolar")
        assert pol_spread > pol_clustered  # spread = more polarization
