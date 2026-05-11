"""Minimal smoke tests for the PVU-BS benchmark runner.

These tests verify that:
1. Sample cases load correctly.
2. Baselines produce the right output shapes.
3. Metrics compute without errors.
4. Turning-point detection returns valid indices.
5. The runner end-to-end writes metrics.json and report.md.
"""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
CASES_DIR = REPO_ROOT / "datasets" / "pvu_cases"


class TestIO(unittest.TestCase):
    def test_load_cases_returns_list(self):
        from benchmarks.io import load_cases

        cases = load_cases(CASES_DIR)
        self.assertIsInstance(cases, list)
        self.assertGreater(len(cases), 0)

    def test_case_has_required_keys(self):
        from benchmarks.io import load_cases

        cases = load_cases(CASES_DIR)
        for case in cases:
            self.assertIn("name", case)
            self.assertIn("timeseries", case)
            self.assertIn("P", case["timeseries"])
            self.assertIsInstance(case["timeseries"]["P"], np.ndarray)
            self.assertGreater(len(case["timeseries"]["P"]), 0)

    def test_timeseries_values_in_range(self):
        from benchmarks.io import load_cases

        cases = load_cases(CASES_DIR)
        for case in cases:
            P = case["timeseries"]["P"]
            self.assertTrue(np.all(P >= 0.0), f"{case['name']}: P has values < 0")
            self.assertTrue(np.all(P <= 1.0), f"{case['name']}: P has values > 1")

    def test_invalid_dir_raises(self):
        from benchmarks.io import load_cases

        with self.assertRaises(FileNotFoundError):
            load_cases("/nonexistent/path")


class TestBaselines(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(0)
        self.train = 0.3 + 0.05 * self.rng.standard_normal(40)
        self.horizon = 10

    def _check_pred(self, pred):
        self.assertEqual(len(pred), self.horizon)
        self.assertFalse(np.any(np.isnan(pred)))

    def test_naive(self):
        from benchmarks.baselines import NaiveBaseline

        pred = NaiveBaseline().predict(self.train, self.horizon)
        self._check_pred(pred)
        self.assertTrue(np.all(pred == self.train[-1]))

    def test_moving_average(self):
        from benchmarks.baselines import MovingAverageBaseline

        pred = MovingAverageBaseline(window=4).predict(self.train, self.horizon)
        self._check_pred(pred)

    def test_ar1(self):
        from benchmarks.baselines import AR1Baseline

        pred = AR1Baseline().predict(self.train, self.horizon)
        self._check_pred(pred)

    def test_random_regime(self):
        from benchmarks.baselines import RandomRegimeBaseline

        rng = np.random.default_rng(42)
        pred = RandomRegimeBaseline().predict(self.train, self.horizon, rng=rng)
        self._check_pred(pred)


class TestMetrics(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(1)
        self.y_true = 0.5 + 0.1 * rng.standard_normal(30)
        self.y_pred = self.y_true + 0.02 * rng.standard_normal(30)

    def test_mae_non_negative(self):
        from benchmarks.metrics import mae

        result = mae(self.y_true, self.y_pred)
        self.assertGreaterEqual(result, 0.0)

    def test_rmse_non_negative(self):
        from benchmarks.metrics import rmse

        result = rmse(self.y_true, self.y_pred)
        self.assertGreaterEqual(result, 0.0)

    def test_mape_finite(self):
        from benchmarks.metrics import mape

        result = mape(self.y_true, self.y_pred)
        self.assertFalse(np.isnan(result))
        self.assertGreaterEqual(result, 0.0)

    def test_directional_accuracy_in_range(self):
        from benchmarks.metrics import directional_accuracy

        da = directional_accuracy(self.y_true, self.y_pred)
        self.assertGreaterEqual(da, 0.0)
        self.assertLessEqual(da, 1.0)

    def test_holm_bonferroni_length(self):
        from benchmarks.metrics import holm_bonferroni

        p_vals = [0.01, 0.04, 0.20, 0.50]
        adjusted = holm_bonferroni(p_vals)
        self.assertEqual(len(adjusted), len(p_vals))

    def test_holm_bonferroni_monotone(self):
        from benchmarks.metrics import holm_bonferroni

        p_vals = [0.01, 0.04, 0.20, 0.50]
        adjusted = sorted(holm_bonferroni(p_vals))
        self.assertEqual(adjusted, sorted(adjusted))


class TestTurningPoints(unittest.TestCase):
    def _make_series(self):
        # Deterministic series with two known turning points (peaks at 10, 30)
        x = np.zeros(50)
        for i in range(50):
            x[i] = np.sin(i * np.pi / 20) * 0.3 + 0.5
        return x

    def test_detect_returns_array(self):
        from benchmarks.turning_points import detect

        s = self._make_series()
        idx = detect(s)
        self.assertIsInstance(idx, np.ndarray)

    def test_detect_finds_turning_points(self):
        from benchmarks.turning_points import detect

        s = self._make_series()
        idx = detect(s, order=2, min_prominence=0.01)
        self.assertGreater(len(idx), 0)

    def test_score_perfect_prediction(self):
        from benchmarks.turning_points import detect, score_turning_points

        s = self._make_series()
        tp = detect(s, order=2, min_prominence=0.01)
        self.assertGreater(len(tp), 0, "Need at least one turning point for this test")
        result = score_turning_points(tp, tp, n=len(s))
        self.assertAlmostEqual(result["precision"], 1.0)
        self.assertAlmostEqual(result["recall"], 1.0)
        self.assertAlmostEqual(result["f1"], 1.0)

    def test_score_empty_predictions(self):
        from benchmarks.turning_points import detect, score_turning_points

        s = self._make_series()
        tp = detect(s, order=2, min_prominence=0.01)
        result = score_turning_points(tp, np.array([], dtype=int), n=len(s))
        self.assertTrue(np.isnan(result["precision"]))
        # recall is 0 when there are true positives but no predictions match
        self.assertAlmostEqual(result["recall"], 0.0)


class TestRunnerEndToEnd(unittest.TestCase):
    def test_runner_produces_outputs(self):
        """Runner writes metrics.json and report.md for sample cases."""
        from benchmarks.runner import main

        with tempfile.TemporaryDirectory() as tmpdir:
            exit_code = main(
                [
                    "--cases",
                    str(CASES_DIR),
                    "--offline",
                    "--out",
                    tmpdir,
                    "--seed",
                    "0",
                ]
            )
            self.assertEqual(exit_code, 0)

            metrics_path = Path(tmpdir) / "metrics.json"
            report_path = Path(tmpdir) / "report.md"
            self.assertTrue(metrics_path.exists(), "metrics.json not created")
            self.assertTrue(report_path.exists(), "report.md not created")

            with open(metrics_path, encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertIsInstance(data, list)
            self.assertGreater(len(data), 0)

    def test_runner_metrics_have_expected_keys(self):
        from benchmarks.runner import main

        with tempfile.TemporaryDirectory() as tmpdir:
            main(
                [
                    "--cases",
                    str(CASES_DIR),
                    "--offline",
                    "--out",
                    tmpdir,
                    "--seed",
                    "0",
                ]
            )
            with open(Path(tmpdir) / "metrics.json", encoding="utf-8") as fh:
                data = json.load(fh)

            for result in data:
                if result.get("skipped"):
                    continue
                self.assertIn("baselines", result)
                self.assertIn("massive", result)
                self.assertIn("turning_points", result)
                for bl_metrics in result["baselines"].values():
                    self.assertIn("mae", bl_metrics)
                    self.assertIn("rmse", bl_metrics)


if __name__ == "__main__":
    unittest.main()
