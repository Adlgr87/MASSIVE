"""Out-of-sample behaviour of the residual corrector (audit finding C-03).

C-03 was label leakage: ``corrected = 0.5*sim + 0.5*actual`` halves the error
arithmetically regardless of model quality, which is why the shipped
``validation.json`` reports ``improvement_pct`` of exactly 50.000 for all ten
stress-test seeds. The leakage is gone; these tests pin down what replaced it,
and keep the honest measurement from quietly drifting back into a claim.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


class TestShippedCheckpointIsHonestlyScored:
    """The published numbers must keep matching reality."""

    @staticmethod
    def _result():
        pytest.importorskip("numpy")
        import sys

        sys.path.insert(0, str(ROOT / "scripts"))
        from validate_cfc_walkforward import evaluate

        return evaluate()

    def test_evaluation_runs_on_the_held_out_split(self):
        result = self._result()
        assert result["n_eval_points"] == 55

    def test_model_is_beaten_by_a_trivial_baseline(self):
        """The finding this whole exercise exists to establish. If a retrain
        ever fixes it, this test fails and the docs must be updated — that is
        the intended behaviour, not a nuisance."""
        result = self._result()
        assert "persistence" in result["baselines_beating_the_model"]
        assert result["verdict"].startswith("NOT FIT FOR PURPOSE")

    def test_model_still_beats_doing_nothing(self):
        """It is wrong to claim the corrector is useless: it does halve RMSE
        versus no correction. Precision about *how* it falls short matters."""
        result = self._result()
        assert result["model_beats_no_correction"] is True

    def test_model_behaves_like_a_biased_constant(self):
        result = self._result()
        actual_std = result["actual_residual"]["std"]
        pred_std = result["model_prediction"]["std"]
        assert pred_std < actual_std / 2
        assert result["model_prediction"]["mean"] > result["actual_residual"]["mean"]

    def test_persistence_explains_most_of_the_variance(self):
        result = self._result()
        persistence = next(s for s in result["scores"] if s["strategy"] == "persistence")
        assert persistence["r2"] > 0.5


class TestLeakageEvidenceIsPreserved:
    def test_shipped_validation_shows_the_arithmetic_fingerprint(self):
        """Every seed improving by *exactly* 50% is not a model working, it is
        ``0.5*sim + 0.5*actual``. Kept as a regression marker so nobody cites
        that file as evidence of accuracy again."""
        path = ROOT / "models" / "cfc_calibrated" / "validation.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        improvements = [s["improvement_pct"] for s in data["stress_test"]]
        assert all(abs(i - 50.0) < 1e-9 for i in improvements)


class TestCorrectionStrategies:
    @staticmethod
    def _router():
        pytest.importorskip("torch")
        from cfc_router import CfCRouter

        return CfCRouter()

    # A clean linear case where the residual is a constant +0.07.
    HIST = [0.30, 0.32, 0.35, 0.38, 0.40, 0.42, 0.45]
    SIM = [0.30, 0.32, 0.35, 0.38, 0.40, 0.42, 0.45]
    ACT = [0.37, 0.39, 0.42, 0.45, 0.47, 0.49, 0.52]

    def test_auto_prefers_persistence_when_ground_truth_exists(self):
        value, source = self._router().correct_residual(self.HIST, self.SIM, actual=self.ACT)
        assert source == "persistence"
        assert value == pytest.approx(0.52, abs=1e-9)

    def test_auto_falls_back_to_the_model_without_ground_truth(self):
        _, source = self._router().correct_residual(self.HIST, self.SIM)
        assert source in {"cfc", "passthrough"}

    def test_off_applies_no_correction(self):
        value, source = self._router().correct_residual(
            self.HIST, self.SIM, actual=self.ACT, strategy="off"
        )
        assert source == "passthrough"
        assert value == pytest.approx(self.SIM[-1])

    def test_source_distinguishes_the_estimators(self):
        """A caller must never mistake one estimator for another: they differ
        by an order of magnitude out-of-sample."""
        router = self._router()
        sources = {
            strategy: router.correct_residual(
                self.HIST, self.SIM, actual=self.ACT, strategy=strategy
            )[1]
            for strategy in ("persistence", "cfc", "off")
        }
        assert sources == {
            "persistence": "persistence",
            "cfc": "cfc",
            "off": "passthrough",
        }

    def test_unknown_strategy_is_rejected(self):
        with pytest.raises(ValueError, match="unknown strategy"):
            self._router().correct_residual(self.HIST, self.SIM, strategy="bogus")

    def test_persistence_never_reads_the_value_it_corrects(self):
        """The leakage guard. Changing only the final observation must not
        change the correction — if it does, the answer is leaking in."""
        router = self._router()
        first, _ = router.correct_residual(self.HIST, self.SIM, actual=self.ACT)
        tampered = list(self.ACT[:-1]) + [9.99]
        second, _ = router.correct_residual(self.HIST, self.SIM, actual=tampered)
        assert first == pytest.approx(second)

    def test_persistence_degrades_to_passthrough_without_ground_truth(self):
        value, source = self._router().correct_residual(self.HIST, self.SIM, strategy="persistence")
        assert source == "passthrough"
        assert value == pytest.approx(self.SIM[-1])


class TestFeatureParityWithTraining:
    def test_router_feature_order_matches_the_trained_config(self):
        """Three mismatches used to sit here (actual/simulated slots swapped
        and the lag window reversed), which alone would stop the model working
        whatever its quality. Pin the declared contract."""
        cfg = json.loads(
            (ROOT / "models" / "cfc_calibrated" / "config.json").read_text(encoding="utf-8")
        )
        assert cfg["input_features"] == [
            "time_normalized",
            "actual_leave_pct",
            "simulated_leave_pct",
        ]
        # Oldest first; the router must fill u[3]=t-6 ... u[8]=t-1.
        assert cfg["context_features"] == [f"residual_t-{k}" for k in range(6, 0, -1)]

        source = (ROOT / "cfc_router.py").read_text(encoding="utf-8")
        assert "lag = 6 - i" in source, "lag window must be written oldest-first"

    def test_short_history_pads_with_the_training_mean_not_zero(self):
        """Zero-padding biases a short window toward a residual the training
        set never contained (its mean is ~0.043)."""
        source = (ROOT / "cfc_router.py").read_text(encoding="utf-8")
        assert "else _TRAINING_RESIDUAL_MEAN" in source


class TestNoRegressionToInterpolation:
    def test_correction_is_not_a_blend_of_simulated_and_actual(self):
        """The exact shape of C-03: corrected == 0.5*sim + 0.5*actual."""
        pytest.importorskip("torch")
        from cfc_router import CfCRouter

        router = CfCRouter()
        hist = [0.1, 0.2, 0.3, 0.4]
        sim = [0.1, 0.2, 0.3, 0.4]
        actual = [0.5, 0.6, 0.7, 0.8]
        for strategy in ("auto", "cfc", "persistence"):
            value, _ = router.correct_residual(hist, sim, actual=actual, strategy=strategy)
            midpoint = 0.5 * sim[-1] + 0.5 * actual[-1]
            assert value != pytest.approx(midpoint, abs=1e-6), strategy


def test_validation_report_is_committed_and_current():
    """The report is a published claim; regenerate it when numbers move."""
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from validate_cfc_walkforward import evaluate

    path = ROOT / "reports" / "cfc_validation.json"
    assert path.exists(), "run: python scripts/validate_cfc_walkforward.py --write"
    committed = json.loads(path.read_text(encoding="utf-8"))
    fresh = evaluate()
    assert committed["verdict"] == fresh["verdict"]
    assert np.isclose(committed["scores"][0]["rmse"], fresh["scores"][0]["rmse"], rtol=1e-9)
