"""
Tests de integración empírica — MASSIVE
Verifica que la base empírica de calibración se cargue correctamente
y que sus valores satisfagan las propiedades esperadas.
"""

import unittest

from empirical_config import (
    EMPIRICAL_BASE_LOADED,
    MASSIVE_EMPIRICAL_MASTER,
    MASSIVE_RUNTIME_PARAMS,
    get_param,
    get_runtime_params,
)


class TestEmpiricalIntegration(unittest.TestCase):

    def test_all_runtime_values_in_range(self):
        """Todos los valores numéricos de MASSIVE_RUNTIME_PARAMS están en [-1.0, 1.0]."""
        numeric_keys = [
            "temperature", "social_influence_lambda", "attractor_depth",
            "repeller_strength", "payoff_coordination", "payoff_defection",
            "narrative_decay_rate", "saturation_threshold",
        ]
        for key in numeric_keys:
            value = MASSIVE_RUNTIME_PARAMS[key]
            self.assertIsInstance(value, (int, float), f"{key} debe ser numérico")
            self.assertGreaterEqual(value, -1.0, f"{key}={value} está por debajo de -1.0")
            self.assertLessEqual(value, 1.0, f"{key}={value} está por encima de 1.0")

    def test_negative_values_preserved(self):
        """repeller_strength y payoff_defection mantienen su signo negativo."""
        self.assertLess(
            MASSIVE_RUNTIME_PARAMS["repeller_strength"],
            0.0,
            "repeller_strength debe ser negativo (repelente activo)",
        )
        self.assertLess(
            MASSIVE_RUNTIME_PARAMS["payoff_defection"],
            0.0,
            "payoff_defection debe ser negativo (costo de disidencia)",
        )

    def test_decay_and_saturation_values_active(self):
        """Los parámetros calibrados temporalmente se mantienen numéricos y activos."""
        self.assertIsNotNone(
            MASSIVE_RUNTIME_PARAMS["narrative_decay_rate"],
            "narrative_decay_rate no debe ser None",
        )
        self.assertIsNotNone(
            MASSIVE_RUNTIME_PARAMS["saturation_threshold"],
            "saturation_threshold no debe ser None",
        )
        self.assertGreater(MASSIVE_RUNTIME_PARAMS["narrative_decay_rate"], 0.0)
        self.assertGreater(MASSIVE_RUNTIME_PARAMS["saturation_threshold"], 0.0)

    def test_no_null_params_when_calibrated(self):
        """validation_flags refleja únicamente parámetros realmente pendientes."""
        flags = MASSIVE_RUNTIME_PARAMS["validation_flags"]
        self.assertIsInstance(flags, list, "validation_flags debe ser una lista")
        for flag in flags:
            self.assertIn("pending_empirical_data", flag)
        self.assertEqual(flags, [])

    def test_cultural_profile_mixed(self):
        """get_runtime_params('mixed') retorna un dict completo sin errores."""
        params = get_runtime_params("mixed")
        self.assertIsInstance(params, dict)
        required_keys = [
            "temperature", "social_influence_lambda", "attractor_depth",
            "repeller_strength", "payoff_coordination", "payoff_defection",
            "narrative_decay_rate", "saturation_threshold",
            "cultural_profile", "validation_flags",
        ]
        for key in required_keys:
            self.assertIn(key, params)
        self.assertEqual(params["cultural_profile"], "mixed")

    def test_get_param_returns_entry(self):
        """get_param retorna el dict correcto dado una categoría y un ID válidos."""
        entry = get_param("network_dynamics", "DERIVA_ALGORITMICA")
        self.assertIsInstance(entry, dict)
        self.assertIn("value", entry)
        self.assertEqual(entry["value"], 0.45)

    def test_get_param_raises_on_bad_category(self):
        with self.assertRaises(KeyError):
            get_param("nonexistent_category", "SOME_PARAM")

    def test_get_param_raises_on_bad_param(self):
        with self.assertRaises(KeyError):
            get_param("network_dynamics", "NONEXISTENT_PARAM")

    def test_empirical_base_loaded_flag(self):
        """EMPIRICAL_BASE_LOADED es True cuando el módulo se carga correctamente."""
        self.assertTrue(EMPIRICAL_BASE_LOADED)

    def test_cultural_profile_latin(self):
        """get_runtime_params('latin') aplica modificadores culturales sin error."""
        params = get_runtime_params("latin")
        self.assertIsInstance(params, dict)
        self.assertEqual(params["cultural_profile"], "latin")
        self.assertAlmostEqual(params["temperature"], 0.424, places=3)

    def test_master_dict_has_required_categories(self):
        """MASSIVE_EMPIRICAL_MASTER contiene las categorías esperadas."""
        expected_categories = {
            "meta", "network_dynamics", "temporal", "individual_psychology",
            "mass_psychology", "cultural_variables", "social_status",
            "gender", "game_theory",
        }
        for cat in expected_categories:
            self.assertIn(
                cat,
                MASSIVE_EMPIRICAL_MASTER,
                f"Categoría '{cat}' falta en MASSIVE_EMPIRICAL_MASTER",
            )


if __name__ == "__main__":
    unittest.main()
