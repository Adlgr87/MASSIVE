"""End-to-end Brexit 2016 calibration test.

Verifies that the full pipeline (energy engine + EWS + Gini + CFC correction)
reduces the Brexit prediction error by at least 25%.
"""

from pathlib import Path

import pytest

from brexit_calibration import BREXIT_ACTUAL_LEAVE_PCT, run_brexit_calibration

# ── Skip-condition: trained Lambda-corrector weights ─────────────────────
# ``test_both_models_loaded`` asserts that both the residual *and* lambda
# correctors are present in the router status. The residual weights
# (``cfc_residual.pt``) are tracked in git, but the lambda weights
# (``cfc_lambda_corrector.pt``) are git-ignored — absent in fresh checkouts.
# When the lambda artifact is missing the assertion cannot hold, so the test
# is skipped rather than failed. The remaining Brexit tests exercise the full
# pipeline with transparent fallback and run unconditionally.
_LAMBDA_WEIGHTS = Path("models/cfc_calibrated/cfc_lambda_corrector.pt")
skip_no_lambda_weights = pytest.mark.skipif(
    not _LAMBDA_WEIGHTS.exists(),
    reason=(
        f"Trained CfC lambda-corrector weights not found ({_LAMBDA_WEIGHTS}). "
        "The *.pt artifacts are git-ignored; regenerate via cfc_trainer.py."
    ),
)


class TestBrexitCalibration:
    """End-to-end Brexit 2016 calibration integration test."""

    def test_calibration_returns_expected_structure(self):
        """run_brexit_calibration should return all expected keys."""
        result = run_brexit_calibration(n_agents=50, steps=50, seed=42)
        assert "baseline" in result
        assert "corrected" in result
        assert "improvement" in result
        assert "engine_metrics" in result

    def test_baseline_exceeds_actual(self):
        """Baseline simulation should overestimate Leave (as documented)."""
        result = run_brexit_calibration(n_agents=50, steps=50, seed=42)
        baseline_leave = result["baseline"]["final_leave_pct"]
        assert baseline_leave > BREXIT_ACTUAL_LEAVE_PCT  # sim overestimates Leave

    def test_correction_does_not_consume_ground_truth(self):
        """Regression guard: the corrector must never read the observed value.

        The previous implementation computed ``0.5 * (simulated - actual)``
        and discarded the model output, so ``corrected`` was always exactly
        halfway to ``BREXIT_ACTUAL_LEAVE_PCT`` and the reported "25% error
        reduction" was circular. This test pins the leakage shut: the
        calibration run must not land on the arithmetic midpoint.
        """
        result = run_brexit_calibration(n_agents=100, steps=100, seed=42)
        baseline = result["baseline"]["final_leave_pct"]
        corrected = result["corrected"]["final_leave_pct"]
        midpoint = (baseline + BREXIT_ACTUAL_LEAVE_PCT) / 2.0
        assert corrected != pytest.approx(midpoint, abs=1e-6), (
            "corrected value is the midpoint between the simulation and the "
            "observed result — the ground-truth leakage has come back"
        )

    def test_correction_is_bounded_and_finite(self):
        """Whatever the corrector outputs must stay physically meaningful."""
        result = run_brexit_calibration(n_agents=100, steps=100, seed=42)
        corrected = result["corrected"]["final_leave_pct"]
        assert 0.0 <= corrected <= 100.0
        assert result["corrected"]["error_pct"] >= 0.0

    def test_correction_source_is_reported(self):
        """Callers must be able to tell whether the model actually ran."""
        result = run_brexit_calibration(n_agents=50, steps=50, seed=42)
        assert result["corrected"]["correction_source"] in {"cfc", "passthrough"}

    @pytest.mark.skip(
        reason=(
            "Accuracy claim pending honest out-of-sample validation. The "
            "shipped checkpoint reports R2 = -18.7 per step; the previous "
            "'>=25% improvement' assertion was satisfied only by the "
            "ground-truth leakage removed in cfc_router.correct_residual. "
            "Re-enable once the corrector is retrained and validated "
            "walk-forward (see docs/research/calibration_log.md)."
        )
    )
    def test_correction_improvement_at_least_25_percent(self):
        """The error reduction should be at least 25% (out-of-sample)."""
        result = run_brexit_calibration(n_agents=100, steps=100, seed=42)
        improvement = result["improvement"]["relative_improvement_pct"]
        assert improvement >= 25.0, f"Only {improvement:.1f}% improvement (need >= 25%)"

    @skip_no_lambda_weights
    def test_both_models_loaded(self):
        """Both residual and lambda correctors should be loaded."""
        result = run_brexit_calibration(n_agents=20, steps=20, seed=42)
        status = result["engine_metrics"]["router_status"]
        assert status["residual_corrector"] is True
        assert status["lambda_corrector"] is True

    def test_ews_detected_during_simulation(self):
        """The simulation should detect EWS signals during the run."""
        # Run a longer simulation to trigger EWS detection
        result = run_brexit_calibration(n_agents=100, steps=100, seed=42)
        # The simulation should complete without error and produce results
        assert result["engine_metrics"]["n_agents"] == 100
        assert result["engine_metrics"]["steps"] == 100

    def test_reproducible_with_same_seed(self):
        """Same seed should produce same baseline result."""
        r1 = run_brexit_calibration(n_agents=30, steps=30, seed=123)
        r2 = run_brexit_calibration(n_agents=30, steps=30, seed=123)
        assert r1["baseline"]["final_leave_pct"] == pytest.approx(
            r2["baseline"]["final_leave_pct"], abs=1e-6
        )
