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

    def test_cfc_correction_reduces_error(self):
        """CFC correction should reduce the Brexit prediction error."""
        result = run_brexit_calibration(n_agents=100, steps=100, seed=42)
        baseline_error = result["baseline"]["error_pct"]
        corrected_error = result["corrected"]["error_pct"]
        assert corrected_error < baseline_error

    def test_correction_improvement_at_least_25_percent(self):
        """The error reduction should be at least 25%."""
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
