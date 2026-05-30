import unittest

import numpy as np

from massive_core import build_scientific_report, trajectory_from_history
from massive_core.diagnostics import ScientificReport


class ScientificReportTests(unittest.TestCase):
    def test_build_report_from_legacy_dict_history_is_serializable(self):
        history = [
            {"opinion": 1.0, "confianza": 0.2},
            {"opinion": 0.5, "confianza": 0.3},
            {"opinion": 0.25, "confianza": 0.4},
            {"opinion": 0.125, "confianza": 0.5},
        ]

        report = build_scientific_report(history, dt=1.0)
        payload = report.to_dict()

        self.assertIsInstance(report, ScientificReport)
        self.assertEqual(payload["n_steps"], 3)
        self.assertEqual(payload["state_dim"], 1)
        self.assertEqual(payload["stability_label"], "stable")
        self.assertLess(payload["spectral_radius"], 1.0)
        self.assertIn("entropy", payload)

    def test_build_report_from_multilayer_arrays_detects_tipping_jump(self):
        history = [
            np.array([[0.0, 0.2], [0.1, 0.3]]),
            np.array([[0.01, 0.2], [0.11, 0.3]]),
            np.array([[0.02, 0.2], [0.12, 0.3]]),
            np.array([[1.0, 0.8], [0.9, 0.7]]),
        ]

        trajectory = trajectory_from_history(history)
        report = build_scientific_report(history, bins=4)

        self.assertEqual(trajectory.shape, (4, 4))
        self.assertEqual(report.n_steps, 3)
        self.assertEqual(report.state_dim, 4)
        self.assertEqual(report.tipping_indices, [3])

    def test_selected_fields_preserve_order(self):
        history = [
            {"opinion": 0.1, "confianza": 0.8},
            {"opinion": 0.2, "confianza": 0.7},
        ]

        trajectory = trajectory_from_history(history, fields=("confianza", "opinion"))

        np.testing.assert_allclose(trajectory, np.array([[0.8, 0.1], [0.7, 0.2]]))


if __name__ == "__main__":
    unittest.main()
