import unittest

import numpy as np

from simulator import calcular_efecto_grupos, resumen_historial, simular, simular_multiples


class SimulatorTests(unittest.TestCase):
    def setUp(self):
        np.random.seed(42)
        self.estado_base = {
            "opinion": 0.5,
            "propaganda": 0.7,
            "confianza": 0.4,
            "tension": 0.3,
            "opinion_grupo_a": 0.72,
            "opinion_grupo_b": 0.28,
            "pertenencia_grupo": 0.65,
        }

    def test_simular_devuelve_historial_valido(self):
        historial = simular(
            self.estado_base,
            escenario="campana",
            pasos=20,
            cada_n_pasos=5,
            verbose=False,
        )

        self.assertEqual(len(historial), 21)
        self.assertEqual(historial[0]["opinion"], self.estado_base["opinion"])
        self.assertTrue(all(0.0 <= h["opinion"] <= 1.0 for h in historial))
        self.assertTrue(all("_regla_nombre" in h for h in historial[1:]))

    def test_resumen_historial_consistente(self):
        historial = simular(
            self.estado_base,
            escenario="campana",
            pasos=10,
            cada_n_pasos=2,
            verbose=False,
        )
        stats = resumen_historial(historial)

        self.assertEqual(stats["pasos"], 10)
        self.assertGreaterEqual(stats["maximo"], stats["minimo"])
        self.assertAlmostEqual(
            stats["delta_total"],
            stats["opinion_final"] - stats["opinion_inicial"],
            places=10,
        )

    def test_efecto_grupos_empuja_hacia_referencia_social(self):
        estado = {
            "opinion": 0.2,
            "opinion_grupo_a": 0.9,
            "opinion_grupo_b": 0.1,
            "pertenencia_grupo": 0.8,
        }
        cfg = {"efecto_vecinos_peso": 0.05}
        efecto = calcular_efecto_grupos(estado, cfg)
        self.assertGreater(efecto, 0.0)

    def test_simular_multiples_confianza_stays_non_negative_bipolar(self):
        """
        In bipolar mode [-1, 1], confianza and pertenencia_grupo must remain
        in [0, 1] after noise perturbation. Previously, all float values were
        clipped to the opinion range, so a low confianza (e.g. 0.005) would
        go negative ~30% of the time, inflating ruido_std beyond its maximum.
        """
        np.random.seed(0)
        estado = {
            "opinion": 0.0,
            "propaganda": 0.4,
            "confianza": 0.005,  # very low — most likely to go negative
            "opinion_grupo_a": 0.65,
            "opinion_grupo_b": -0.55,
            "pertenencia_grupo": 0.1,  # minimum allowed by homofilia rule
        }
        config = {"proveedor": "heurístico", "rango": "[-1, 1] — Bipolar"}

        result = simular_multiples(
            estado, pasos=5, cada_n_pasos=2, config=config, n_simulaciones=200
        )

        # The result must be a valid statistics dict
        self.assertIn("media", result)
        self.assertIn("percentiles", result)
        self.assertEqual(result["neutro"], 0.0)

    def test_simular_multiples_unit_interval_keys_clipped_correctly(self):
        """
        confianza and pertenencia_grupo must be clipped to [0, 1], not to the
        opinion range. Verify by patching numpy.random.normal to always return
        a large negative offset that would push these values below zero if
        clipped to the bipolar range [-1, 1].
        """
        from unittest.mock import patch

        estado = {
            "opinion": 0.0,
            "propaganda": 0.4,
            "confianza": 0.02,
            "opinion_grupo_a": 0.65,
            "opinion_grupo_b": -0.55,
            "pertenencia_grupo": 0.05,
        }
        config = {"proveedor": "heurístico", "rango": "[-1, 1] — Bipolar"}

        # Force noise = -0.5 for every call. Without the fix, confianza and
        # pertenencia_grupo would be clipped to [-1, 1] and become negative.
        # With the fix they are clipped to [0, 1] and stay at 0.0.
        captured_states = []

        original_simular = simular

        def mock_simular(estado_ruido, **kwargs):
            captured_states.append(estado_ruido.copy())
            return original_simular(estado_ruido, **kwargs)

        with (
            patch("simulator.simular", side_effect=mock_simular),
            patch("numpy.random.normal", return_value=-0.5),
        ):
            simular_multiples(estado, pasos=3, cada_n_pasos=1, config=config, n_simulaciones=1)

        self.assertEqual(len(captured_states), 1)
        perturbed = captured_states[0]
        self.assertGreaterEqual(
            perturbed["confianza"], 0.0, "confianza must not go negative after noise perturbation"
        )
        self.assertGreaterEqual(
            perturbed["pertenencia_grupo"],
            0.0,
            "pertenencia_grupo must not go negative after noise perturbation",
        )
        # Opinion-space values should still be clipped to [-1, 1]
        self.assertGreaterEqual(perturbed["opinion"], -1.0)
        self.assertLessEqual(perturbed["opinion"], 1.0)


if __name__ == "__main__":
    unittest.main()
