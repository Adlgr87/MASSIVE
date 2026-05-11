"""
Tests de integración empírica — MASSIVE
Verifica que la base empírica de calibración se cargue correctamente
y que sus valores satisfagan las propiedades esperadas.
"""

import unittest

from empirical_config import (
    BEYONDSIGHT_EMPIRICAL_MASTER,
    BEYONDSIGHT_RUNTIME_PARAMS,
    EMPIRICAL_BASE_LOADED,
    get_param,
    get_runtime_params,
)


class TestEmpiricalIntegration(unittest.TestCase):

    def test_all_runtime_values_in_range(self):
        """Todos los valores numéricos de BEYONDSIGHT_RUNTIME_PARAMS están en [-1.0, 1.0]."""
        numeric_keys = [
            "temperature",
            "social_influence_lambda",
            "attractor_depth",
            "repeller_strength",
            "payoff_coordination",
            "payoff_defection",
            "narrative_decay_rate",
            "saturation_threshold",
        ]
        for key in numeric_keys:
            value = BEYONDSIGHT_RUNTIME_PARAMS[key]
            self.assertIsInstance(value, (int, float), f"{key} debe ser numérico")
            self.assertGreaterEqual(
                value, -1.0,
                f"{key}={value} está por debajo de -1.0",
            )
            self.assertLessEqual(
                value, 1.0,
                f"{key}={value} está por encima de 1.0",
            )

    def test_negative_values_preserved(self):
        """repeller_strength y payoff_defection mantienen su signo negativo."""
        self.assertLess(
            BEYONDSIGHT_RUNTIME_PARAMS["repeller_strength"],
            0.0,
            "repeller_strength debe ser negativo (repelente activo)",
        )
        self.assertLess(
            BEYONDSIGHT_RUNTIME_PARAMS["payoff_defection"],
            0.0,
            "payoff_defection debe ser negativo (costo de disidencia)",
        )

    def test_zero_values_active(self):
        """Los valores 0.0 (neutralidad activa) no son reemplazados por None."""
        self.assertIsNotNone(
            BEYONDSIGHT_RUNTIME_PARAMS["narrative_decay_rate"],
            "narrative_decay_rate no debe ser None — es neutralidad activa",
        )
        self.assertIsNotNone(
            BEYONDSIGHT_RUNTIME_PARAMS["saturation_threshold"],
            "saturation_threshold no debe ser None — es neutralidad activa",
        )
        self.assertEqual(
            BEYONDSIGHT_RUNTIME_PARAMS["narrative_decay_rate"],
            0.0,
            "narrative_decay_rate debe ser 0.0 (neutralidad activa)",
        )
        self.assertEqual(
            BEYONDSIGHT_RUNTIME_PARAMS["saturation_threshold"],
            0.0,
            "saturation_threshold debe ser 0.0 (neutralidad activa)",
        )

    def test_null_params_flagged(self):
        """Los parámetros con value: null aparecen en validation_flags."""
        flags = BEYONDSIGHT_RUNTIME_PARAMS["validation_flags"]
        self.assertIsInstance(flags, list, "validation_flags debe ser una lista")
        self.assertGreater(
            len(flags),
            0,
            "validation_flags debe contener al menos un parámetro pendiente",
        )
        # Verify that all flags contain the expected message suffix
        for flag in flags:
            self.assertIn(
                "pending_empirical_data",
                flag,
                f"Flag '{flag}' debe contener 'pending_empirical_data'",
            )
        # Spot-check: at least one known null param is flagged
        flagged_ids = [f.split(":")[0].strip() for f in flags]
        self.assertTrue(
            any("HOMOFILIA_RED" in fid for fid in flagged_ids),
            "HOMOFILIA_RED (null) debe estar en validation_flags",
        )

    def test_cultural_profile_mixed(self):
        """get_runtime_params('mixed') retorna un dict completo sin errores."""
        params = get_runtime_params("mixed")
        self.assertIsInstance(params, dict, "get_runtime_params debe retornar un dict")
        required_keys = [
            "temperature",
            "social_influence_lambda",
            "attractor_depth",
            "repeller_strength",
            "payoff_coordination",
            "payoff_defection",
            "narrative_decay_rate",
            "saturation_threshold",
            "cultural_profile",
            "validation_flags",
        ]
        for key in required_keys:
            self.assertIn(key, params, f"'{key}' debe estar en get_runtime_params('mixed')")
        self.assertEqual(params["cultural_profile"], "mixed")

    def test_get_param_returns_entry(self):
        """get_param retorna el dict correcto dado una categoría y un ID válidos."""
        entry = get_param("network_dynamics", "DERIVA_ALGORITMICA")
        self.assertIsInstance(entry, dict)
        self.assertIn("value", entry)
        self.assertEqual(entry["value"], 0.45)

    def test_get_param_raises_on_bad_category(self):
        """get_param lanza KeyError con mensaje descriptivo en categoría inválida."""
        with self.assertRaises(KeyError) as ctx:
            get_param("nonexistent_category", "SOME_PARAM")
        self.assertIn("nonexistent_category", str(ctx.exception))

    def test_get_param_raises_on_bad_param(self):
        """get_param lanza KeyError con mensaje descriptivo en param ID inválido."""
        with self.assertRaises(KeyError) as ctx:
            get_param("network_dynamics", "NONEXISTENT_PARAM")
        self.assertIn("NONEXISTENT_PARAM", str(ctx.exception))

    def test_empirical_base_loaded_flag(self):
        """EMPIRICAL_BASE_LOADED es True cuando el módulo se carga correctamente."""
        self.assertTrue(EMPIRICAL_BASE_LOADED)

    def test_cultural_profile_latin(self):
        """get_runtime_params('latin') aplica modificadores culturales sin error."""
        params = get_runtime_params("latin")
        self.assertIsInstance(params, dict)
        self.assertEqual(params["cultural_profile"], "latin")
        # Temperature is modified by DERIVA_ALGORITMICA cultural variance
        # latin=0.40, base=0.45 → delta=-0.05 → temperature=0.45+(-0.05)=0.40
        self.assertAlmostEqual(params["temperature"], 0.40, places=5)

    def test_master_dict_has_required_categories(self):
        """BEYONDSIGHT_EMPIRICAL_MASTER contiene las categorías esperadas."""
        expected_categories = {
            "meta",
            "network_dynamics",
            "temporal",
            "individual_psychology",
            "mass_psychology",
            "cultural_variables",
            "social_status",
            "gender",
            "game_theory",
        }
        for cat in expected_categories:
            self.assertIn(
                cat,
                BEYONDSIGHT_EMPIRICAL_MASTER,
                f"Categoría '{cat}' falta en BEYONDSIGHT_EMPIRICAL_MASTER",
            )


if __name__ == "__main__":
    unittest.main()
