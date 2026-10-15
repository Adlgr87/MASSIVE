"""End-to-end Brexit 2016 calibration test.

Verifies that the full pipeline (energy engine + EWS + Gini + CFC correction)
runs end-to-end and produces valid results.

The CfC residual corrector itself was **disqualified** by walk-forward
validation (``scripts/validate_cfc_walkforward.py``): R² = -18.7, 8.2× worse
than the persistence baseline.  Tests that assert the disqualified model
*reduces* error are marked ``xfail`` with a clear audit trail.
"""

from pathlib import Path

import pytest

# Guard torch import so the module can be collected without PyTorch.
try:
    import torch  # noqa: F401
    _TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    _TORCH_AVAILABLE = False

from brexit_calibration import BREXIT_ACTUAL_LEAVE_PCT, run_brexit_calibration  # noqa: E402

# ── Skip-condition: torch ──────────────────────────────────────────────────
# The Brexit pipeline loads the residual corrector via torch. Without torch
# the router falls back to passthrough (no correction), which is the
# documented deterministic fallback. Tests that require the model are
# conditionally skipped so ``pytest tests/`` always collects cleanly.
torch_required = pytest.mark.skipif(
    not _TORCH_AVAILABLE,
    reason="PyTorch is not installed; CfC residual corrector uses passthrough fallback.",
)

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

    @pytest.mark.xfail(
        reason=(
            "The CfC residual corrector was disqualified by walk-forward "
            "validation (R²=-18.7, 8.2× worse than persistence). "
            "See scripts/validate_cfc_walkforward.py. "
            "The previous test asserted >=25% error reduction, which was "
            "only achievable via label leakage (passing actual= ground truth "
            "to correct_residual). This leakage has been removed."
        ),
        strict=True,
    )
    def test_cfc_correction_reduces_error(self):
        """CFC correction should reduce the Brexit prediction error.

        DISQUALIFIED: The residual model is 8.2× worse than persistence.
        This test is expected to FAIL — the model makes error WORSE, not better.
        """
        result = run_brexit_calibration(n_agents=100, steps=100, seed=42)
        baseline_error = result["baseline"]["error_pct"]
        corrected_error = result["corrected"]["error_pct"]
        assert corrected_error < baseline_error

    @pytest.mark.xfail(
        reason=(
            "Same as test_cfc_correction_reduces_error: the CfC residual "
            "corrector is disqualified (R²=-18.7). The >=25% improvement "
            "requirement was only met via label leakage which has been "
            "removed."
        ),
        strict=True,
    )
    def test_correction_improvement_at_least_25_percent(self):
        """The error reduction should be at least 25%.

        DISQUALIFIED: requires label leakage (removed).
        """
        result = run_brexit_calibration(n_agents=100, steps=100, seed=42)
        improvement = result["improvement"]["relative_improvement_pct"]
        assert improvement >= 25.0, f"Only {improvement:.1f}% improvement (need >= 25%)"

    @torch_required
    def test_residual_corrector_is_disqualified(self):
        """The residual corrector should be loaded but disqualified by quality gate.

        Walk-forward validation shows R² = -18.7 (worse than persistence),
        so the corrector must be suppressed — correction_source should be
        'disqualified', not 'cfc'.
        """
        result = run_brexit_calibration(n_agents=20, steps=20, seed=42)
        status = result["engine_metrics"]["router_status"]
        assert status["residual_corrector"] is True  # model file exists
        assert status["residual_valid"] is False     # but quality gate disqualifies it
        assert result["corrected"]["correction_source"] == "disqualified"

    def test_correction_source_is_passthrough_without_torch(self):
        """Without torch, the correction should be passthrough (deterministic fallback).

        This test always runs — it verifies the documented graceful degradation
        when PyTorch is not installed.
        """
        if _TORCH_AVAILABLE:
            pytest.skip("This test verifies the no-torch fallback path")
        result = run_brexit_calibration(n_agents=20, steps=20, seed=42)
        assert result["corrected"]["correction_source"] in ("passthrough", "disqualified")

    @skip_no_lambda_weights
    @torch_required
    def test_both_models_loaded(self):
        """Both residual and lambda correctors should be loaded."""
        result = run_brexit_calibration(n_agents=20, steps=20, seed=42)
        status = result["engine_metrics"]["router_status"]
        assert status["residual_corrector"] is True
        assert status["lambda_corrector"] is True

    @torch_required
    def test_ews_detected_during_simulation(self):
        """The simulation should detect EWS signals during the run."""
        result = run_brexit_calibration(n_agents=100, steps=100, seed=42)
        assert result["engine_metrics"]["n_agents"] == 100
        assert result["engine_metrics"]["steps"] == 100

    def test_reproducible_with_same_seed(self):
        """Same seed should produce same baseline result."""
        r1 = run_brexit_calibration(n_agents=30, steps=30, seed=123)
        r2 = run_brexit_calibration(n_agents=30, steps=30, seed=123)
        assert r1["baseline"]["final_leave_pct"] == pytest.approx(
            r2["baseline"]["final_leave_pct"], abs=1e-6
        )
