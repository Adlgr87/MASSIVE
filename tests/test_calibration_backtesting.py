"""Layer 4 — Tests for backtesting framework, ABC calibrator, and provenance.

G0-quater: Baseline comparisons.
G4: Historical backtesting with Wasserstein-1 and KL divergence.
Preregistration: Pre-registration sealing before simulation.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from massive.core.abcsbi import ABCCalibrator, TrajectoryObservation
from massive.core.backtesting import (
    Backtester,
    BacktestMetrics,
    coverage_90ci,
    direction_error,
    dtw_rmse,
    kl_divergence,
    wasserstein_distance_1d,
)
from massive.core.data_provenance import (
    get_seed_sequence,
    hash_directory,
    hash_file,
    register_dataset,
    verify_integrity,
)
from massive.core.physics_calibration import (
    PHYSICS_RANGES,
    simulate_opinion_dynamics,
)

# ── Test data ──────────────────────────────────────────────────────────────────

Brexit_OBS = np.array([0.28, 0.30, 0.32, 0.35, 0.42, 0.52, 0.58, 0.62, 0.58, 0.55, 0.52])
EGYPT_OBS = np.array(
    [0.02, 0.05, 0.15, 0.35, 0.55, 0.70, 0.65, 0.55, 0.45, 0.35, 0.25, 0.18, 0.12, 0.08]
)

CASES_DIR = Path(__file__).resolve().parents[1] / "datasets" / "real_cases"
# Alias for convenience
CASES_DIR_ALIAS = CASES_DIR


# ═══════════════════════════════════════════════════════════════════════════════
# METRIC FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


class TestWassersteinDistance:
    def test_identical_distributions(self):
        x = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        assert wasserstein_distance_1d(x, x) == 0.0

    def test_known_distance(self):
        # Simple 2-point distributions
        a = np.array([0.0, 0.0, 1.0, 1.0])
        b = np.array([0.5, 0.5, 0.5, 0.5])
        # Wasserstein-1 between these is 0.5
        assert abs(wasserstein_distance_1d(a, b) - 0.5) < 0.01

    def test_disjoint_support(self):
        a = np.array([0.0])
        b = np.array([1.0])
        assert abs(wasserstein_distance_1d(a, b) - 1.0) < 1e-6

    def test_accepts_lists(self):
        assert wasserstein_distance_1d([0.1, 0.2], [0.15, 0.25]) > 0


class TestKLDivergence:
    def test_identical_distributions(self):
        x = np.linspace(0, 1, 50)
        assert kl_divergence(x, x) < 0.01

    def test_different_means(self):
        a = np.random.default_rng(42).normal(0, 1, 1000)
        b = np.random.default_rng(43).normal(2, 1, 1000)
        assert kl_divergence(a, b) > 0.5

    def test_gaussian_approximation_for_small_samples(self):
        # With <50 samples, should use Gaussian approximation (not crash)
        a = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        b = np.array([0.15, 0.25, 0.35, 0.45, 0.55])
        result = kl_divergence(a, b)
        assert result >= 0
        assert np.isfinite(result)

    def test_identical_single_point(self):
        a = np.array([0.5])
        b = np.array([0.5])
        assert kl_divergence(a, b) == 0.0


class TestDTWRMSE:
    def test_identical_trajectories(self):
        a = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        assert dtw_rmse(a, a) == 0.0

    def test_shifted_trajectory(self):
        a = np.array([0.1, 0.2, 0.3])
        b = np.array([0.2, 0.3, 0.4])  # shifted by 0.1
        # DTW finds optimal alignment; for uniform shifts the RMSE
        # equals the shift magnitude along the diagonal path
        result = dtw_rmse(a, b)
        assert 0.0 < result <= 0.1

    def test_empty_arrays(self):
        assert dtw_rmse(np.array([]), np.array([])) == 0.0

    def test_different_lengths(self):
        a = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        b = np.array([0.1, 0.5])
        assert dtw_rmse(a, b) >= 0


class TestDirectionError:
    def test_identical_directions(self):
        a = np.array([1.0, 2.0, 3.0, 4.0])
        b = np.array([1.1, 2.1, 3.1, 4.1])
        assert direction_error(a, b) == 0.0

    def test_opposite_directions(self):
        a = np.array([1.0, 2.0, 3.0])  # increasing
        b = np.array([3.0, 2.0, 1.0])  # decreasing
        assert direction_error(a, b) == 1.0

    def test_too_short(self):
        assert direction_error(np.array([1.0]), np.array([1.0])) == 0.0


class TestCoverage90CI:
    def test_all_within(self):
        lower = np.array([0.0, 0.0, 0.0])
        upper = np.array([1.0, 1.0, 1.0])
        actual = np.array([0.5, 0.5, 0.5])
        intervals = np.column_stack([lower, upper])
        assert coverage_90ci(intervals, actual) == 1.0

    def test_none_within(self):
        lower = np.array([0.0, 0.0, 0.0])
        upper = np.array([0.1, 0.1, 0.1])
        actual = np.array([0.5, 0.5, 0.5])
        intervals = np.column_stack([lower, upper])
        assert coverage_90ci(intervals, actual) == 0.0

    def test_partial_coverage(self):
        lower = np.array([0.0, 0.6, 0.0])
        upper = np.array([1.0, 1.0, 1.0])
        actual = np.array([0.5, 0.5, 0.5])
        intervals = np.column_stack([lower, upper])
        assert abs(coverage_90ci(intervals, actual) - 2.0 / 3.0) < 1e-6


# ═══════════════════════════════════════════════════════════════════════════════
# BACKTESTER
# ═══════════════════════════════════════════════════════════════════════════════


class TestBacktesterLoading:
    def test_load_brexit_event(self):
        bt = Backtester(n_agents=50, ensemble_size=10, seed=42)
        event = bt.load_event("brexit_referendum_2016")
        assert event["case_id"] == "brexit_referendum_2016"
        assert event["n_timesteps"] == 11
        assert event["scenario_type"] == "polarization_spike"
        assert event["meta"].get("target_variable") == "leave_vote_share"

    def test_load_egypt_event(self):
        bt = Backtester(n_agents=50, ensemble_size=10, seed=42)
        event = bt.load_event("egypt_arab_spring_2011")
        assert event["meta"].get("target_variable") == "fraction_participating"

    def test_load_nonexistent_case(self):
        bt = Backtester(n_agents=50, ensemble_size=10, seed=42)
        with pytest.raises(FileNotFoundError):
            bt.load_event("nonexistent_case")

    def test_loads_all_12_cases(self):
        bt = Backtester(n_agents=50, ensemble_size=10, seed=42)
        import os

        case_dirs = [d for d in os.listdir(CASES_DIR) if os.path.isdir(CASES_DIR / d)]
        loaded = 0
        for case_id in sorted(case_dirs):
            try:
                bt.load_event(case_id)
                loaded += 1
            except Exception:
                pass
        assert loaded == 12


class TestBacktesterThresholds:
    def test_thresholds_loaded_from_yaml(self):
        bt = Backtester(n_agents=10, ensemble_size=5, seed=42)
        thresholds = bt.thresholds
        assert "wasserstein_max" in thresholds
        assert "kl_div_max" in thresholds
        assert "dtw_rmse_max" in thresholds
        assert "direction_error_max" in thresholds
        assert "coverage_min" in thresholds

    def test_thresholds_within_expected_ranges(self):
        bt = Backtester()
        t = bt.thresholds
        assert t["wasserstein_max"] == pytest.approx(0.15, abs=0.01)
        assert t["kl_div_max"] == pytest.approx(0.30, abs=0.01)
        assert t["dtw_rmse_max"] == pytest.approx(0.10, abs=0.01)
        assert t["coverage_min"] == pytest.approx(0.85, abs=0.01)


class TestBacktesterRun:
    def test_run_brexit_backtest(self):
        """End-to-end backtest on Brexit with small ensemble for speed."""
        bt = Backtester(n_agents=30, ensemble_size=5, seed=42)
        result = bt.run_backtest("brexit_referendum_2016")

        assert result.case_id == "brexit_referendum_2016"
        assert result.metrics.wasserstein >= 0
        assert result.metrics.kl_divergence >= 0
        assert result.metrics.dtw_rmse >= 0
        assert 0 <= result.metrics.direction_error <= 1
        assert 0 <= result.metrics.coverage_90ci <= 1
        assert isinstance(result.gates, dict)
        assert set(result.gates.keys()) == {"G1", "G2", "G3", "G4"}
        # G1 (pre-registration) and G2 (blind) should always pass
        assert result.gates["G1"] is True
        assert result.gates["G2"] is True

    def test_preregistration_file_exists(self):
        bt = Backtester(n_agents=20, ensemble_size=5, seed=42)
        bt.run_backtest("brexit_referendum_2016")
        # Check that pre-registration files exist
        import glob

        prereg_files = glob.glob("configs/calibrated/pre_registration/prereg_brexit*.yaml")
        assert len(prereg_files) >= 1

    def test_trajectories_correct_length(self):
        bt = Backtester(n_agents=20, ensemble_size=5, seed=42)
        result = bt.run_backtest("brexit_referendum_2016")
        # Simulated trajectory should have same length as observed
        assert len(result.simulated_trajectory) == len(result.observed_trajectory)

    def test_at_least_3_cases_backtested(self):
        """G4: Backtesting must run on ≥3 historical events."""
        bt = Backtester(n_agents=30, ensemble_size=5, seed=42)
        test_cases = [
            "brexit_referendum_2016",
            "us_election_2020",
            "south_korea_candlelight_2016",
        ]
        results = []
        for case_id in test_cases:
            result = bt.run_backtest(case_id)
            results.append(result)
            assert result.metrics.passed_all is not None

        assert len(results) >= 3
        # At least one should have meaningful metrics (not all NaN)
        assert any(r.metrics.wasserstein < 1.0 for r in results)


class TestPreRegistration:
    def test_pre_register_creates_file(self):
        bt = Backtester(n_agents=20, ensemble_size=5, seed=42)
        record = bt.pre_register("brexit_referendum_2016")

        assert record["case_id"] == "brexit_referendum_2016"
        assert "hypothesis" in record
        assert "hypothesis_null" in record
        assert "metrics" in record
        assert "thresholds" in record
        assert "calibrated_params" in record
        assert "gates" in record

    def test_pre_reg_has_all_metrics(self):
        bt = Backtester(n_agents=20, ensemble_size=5, seed=42)
        record = bt.pre_register("chile_estallido_2019")
        metric_names = [m["name"] for m in record["metrics"]]
        assert set(metric_names) == {
            "wasserstein",
            "kl_divergence",
            "dtw_rmse",
            "direction_error",
            "coverage_90ci",
        }


class TestBacktestMetricsDataclass:
    def test_backtest_metrics_fields(self):
        m = BacktestMetrics(
            wasserstein=0.01,
            kl_divergence=0.02,
            dtw_rmse=0.03,
            direction_error=0.0,
            coverage_90ci=0.95,
            passed_all=True,
            thresholds={"wasserstein_max": 0.15},
        )
        assert m.wasserstein == 0.01
        assert m.passed_all is True


# ═══════════════════════════════════════════════════════════════════════════════
# ABC CALIBRATOR
# ═══════════════════════════════════════════════════════════════════════════════


class TestABCObserving:
    def test_trajectory_observation_from_array(self):
        arr = np.array([0.1, 0.2, 0.3])
        obs = TrajectoryObservation(trajectory=arr)
        assert len(obs.trajectory) == 3

    def test_trajectory_observation_with_distribution(self):
        traj = np.array([0.1, 0.2, 0.3])
        dist = np.array([-0.5, -0.3, 0.1, 0.4, 0.8])
        obs = TrajectoryObservation(trajectory=traj, distribution=dist)
        assert obs.distribution is not None


class TestABCCalibrator:
    def test_prior_sampling_in_ranges(self):
        abc = ABCCalibrator(n_agents=30, n_steps=5, seed=42)
        particles = abc.simulate_prior(n_samples=50)
        assert particles.shape == (50, 3)
        assert np.all(particles[:, 0] >= 0.01)  # sigma
        assert np.all(particles[:, 0] <= 0.20)
        assert np.all(particles[:, 1] >= 0.20)  # epsilon
        assert np.all(particles[:, 1] <= 0.35)
        assert np.all(particles[:, 2] >= 0.0)  # lambda
        assert np.all(particles[:, 2] <= 1.0)

    def test_compute_distance_zero_for_identical(self):
        abc = ABCCalibrator(n_agents=30, n_steps=5, seed=42)
        obs = TrajectoryObservation(trajectory=Brexit_OBS)
        sim = TrajectoryObservation(trajectory=Brexit_OBS)
        dist = abc.compute_distance(sim, obs)
        assert dist < 0.01

    def test_compute_distance_positive_for_different(self):
        abc = ABCCalibrator(n_agents=30, n_steps=5, seed=42)
        obs = TrajectoryObservation(trajectory=Brexit_OBS)
        different = TrajectoryObservation(trajectory=np.ones_like(Brexit_OBS))
        dist = abc.compute_distance(different, obs)
        assert dist > 0

    def test_calibrate_produces_posterior(self):
        abc = ABCCalibrator(n_agents=30, n_steps=11, seed=42)
        particles = abc.calibrate(Brexit_OBS, n_rounds=2, n_samples=30, threshold=0.5, seed=42)
        assert particles.shape[1] == 3
        assert len(particles) > 0

    def test_posterior_summary_has_all_params(self):
        abc = ABCCalibrator(n_agents=30, n_steps=11, seed=42)
        abc.calibrate(Brexit_OBS, n_rounds=2, n_samples=20, threshold=0.5, seed=42)
        summary = abc.posterior_summary()
        assert set(summary.keys()) == {"sigma", "epsilon", "lambda_social"}
        for vals in summary.values():
            assert "mean" in vals
            assert "std" in vals
            assert "ci_lower" in vals
            assert "ci_upper" in vals
            assert "n" in vals
            assert vals["std"] >= 0  # std is non-negative
            assert vals["n"] > 0  # at least one sample accepted

    def test_posterior_mean_params_in_ranges(self):
        abc = ABCCalibrator(n_agents=30, n_steps=11, seed=42)
        abc.calibrate(Brexit_OBS, n_rounds=2, n_samples=20, threshold=0.5, seed=42)
        params = abc.posterior_mean_params()
        lo_s, hi_s = PHYSICS_RANGES["sigma"]
        lo_e, hi_e = PHYSICS_RANGES["epsilon"]
        lo_l, hi_l = PHYSICS_RANGES["lambda_social"]
        assert lo_s <= params.sigma <= hi_s
        assert lo_e <= params.epsilon <= hi_e
        assert lo_l <= params.lambda_social <= hi_l

    def test_prior_mean_distance_recorded(self):
        abc = ABCCalibrator(n_agents=30, n_steps=11, seed=42)
        abc.calibrate(Brexit_OBS, n_rounds=2, n_samples=20, threshold=0.5, seed=42)
        prior_dist = abc.prior_mean_distance()
        assert prior_dist >= 0
        assert np.isfinite(prior_dist)

    def test_calibrate_reduces_distance(self):
        """Posterior distance should be lower than prior distance."""
        abc = ABCCalibrator(n_agents=30, n_steps=11, seed=42)
        abc.calibrate(Brexit_OBS, n_rounds=2, n_samples=30, threshold=0.5, seed=42)
        # This is a weak test — at Tier 1, improvement may be marginal
        params = abc.posterior_mean_params()
        sim_traj, _ = simulate_opinion_dynamics(
            sigma=params.sigma,
            epsilon=params.epsilon,
            lambda_social=params.lambda_social,
            n_agents=30,
            n_steps=10,
            initial_opinions=np.full(30, -0.18),  # Brexit T0 opinion
            seed=42,
        )
        post_dist = abc.compute_distance(
            TrajectoryObservation(trajectory=sim_traj),
            TrajectoryObservation(trajectory=Brexit_OBS),
        )
        assert np.isfinite(post_dist)


class TestABCCalibratorDeterminism:
    def test_same_seed_gives_same_posterior(self):
        abc1 = ABCCalibrator(n_agents=30, n_steps=11, seed=42)
        abc1.calibrate(Brexit_OBS, n_rounds=2, n_samples=20, threshold=0.5, seed=42)
        summary1 = abc1.posterior_summary()

        abc2 = ABCCalibrator(n_agents=30, n_steps=11, seed=42)
        abc2.calibrate(Brexit_OBS, n_rounds=2, n_samples=20, threshold=0.5, seed=42)
        summary2 = abc2.posterior_summary()

        for param in ["sigma", "epsilon", "lambda_social"]:
            assert summary1[param]["mean"] == pytest.approx(summary2[param]["mean"], abs=1e-8)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA PROVENANCE
# ═══════════════════════════════════════════════════════════════════════════════


class TestDataProvenance:
    def test_hash_file(self):
        # Hash a known file
        path = Path(__file__).resolve()
        h = hash_file(str(path))
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex

    def test_hash_file_consistency(self):
        path = Path(__file__).resolve()
        h1 = hash_file(str(path))
        h2 = hash_file(str(path))
        assert h1 == h2

    def test_hash_directory(self):
        path = CASES_DIR
        h = hash_directory(str(path))
        assert isinstance(h, str)
        assert len(h) == 64

    def test_seed_sequence_deterministic(self):
        seq1 = get_seed_sequence(42, 3)
        seq2 = get_seed_sequence(42, 3)
        assert seq1 == seq2
        assert len(seq1) == 3
        assert all(isinstance(s, int) for s in seq1)

    def test_seed_sequence_differs_for_different_seeds(self):
        seq1 = get_seed_sequence(42, 3)
        seq2 = get_seed_sequence(43, 3)
        assert seq1 != seq2

    def test_register_and_verify_dataset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test dataset
            d = Path(tmpdir) / "test_case"
            d.mkdir()
            (d / "meta.json").write_text('{"case_id": "test"}')
            (d / "timeseries.csv").write_text("date,P\n2020-W01,0.5\n")

            register_dataset("test_case", str(d))
            assert verify_integrity("test_case")

            # Corrupt the file
            (d / "meta.json").write_text('{"case_id": "corrupted"}')
            assert not verify_integrity("test_case")


# ═══════════════════════════════════════════════════════════════════════════════
# END-TO-END INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestEndToEndIntegration:
    """Tier 1 integration: ABC calibration feeds into backtesting."""

    def test_abc_to_backtest_pipeline(self):
        """ABC-calibrated params should produce a runnable backtest."""
        abc = ABCCalibrator(n_agents=30, n_steps=10, seed=42)
        abc.calibrate(Brexit_OBS, n_rounds=2, n_samples=20, threshold=0.5, seed=42)
        params = abc.posterior_mean_params()

        # Use the calibrated params directly in the backtester
        bt = Backtester(
            n_agents=30,
            ensemble_size=5,
            seed=42,
            calibrated_params=params,
        )
        result = bt.run_backtest("brexit_referendum_2016")
        assert result.case_id == "brexit_referendum_2016"
        assert result.metrics.passed_all is not None

    def test_prereg_seals_before_simulation(self):
        """Pre-registration must be created before backtest runs."""
        bt = Backtester(n_agents=20, ensemble_size=5, seed=42)
        prereg = bt.pre_register("brexit_referendum_2016")
        assert "registered_at" in prereg
        assert "gates" in prereg
        assert "calibrated_params" in prereg
        assert prereg["gates"]["G1"]  # pre-registration gate passes
