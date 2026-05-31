import json
import unittest

from empirical_calibration import (
    MASSIVE_EMPIRICAL_MASTER,
    MASSIVE_RUNTIME_PARAMS,
    HK_EPSILON_MAX,
    HK_EPSILON_MIN,
    TIPPING_POINT_MEAN,
    TIPPING_POINT_STD,
    apply_empirical_profile,
    build_empirical_engine_config,
    export_to_json,
)


class TestEmpiricalMaster(unittest.TestCase):

    def test_meta_fields_present(self):
        meta = MASSIVE_EMPIRICAL_MASTER["meta"]
        self.assertIn("version", meta)
        self.assertIn("total_params", meta)
        self.assertIn("coverage_pct", meta)
        self.assertIn("generated", meta)

    def test_all_values_in_range(self):
        """Every empirical value must sit within [-1.0, 1.0]."""
        sections = ["network_dynamics", "temporal", "game_theory"]
        for section in sections:
            for key, entry in MASSIVE_EMPIRICAL_MASTER[section].items():
                val = entry.get("value")
                if val is not None:
                    self.assertGreaterEqual(val, -1.0, msg=f"{section}.{key}: {val} < -1.0")
                    self.assertLessEqual(val, 1.0, msg=f"{section}.{key}: {val} > 1.0")

    def test_network_dynamics_keys(self):
        nd = MASSIVE_EMPIRICAL_MASTER["network_dynamics"]
        self.assertIn("DERIVA_ALGORITMICA", nd)
        self.assertIn("INFLUENCIA_PARASOCIAL", nd)
        self.assertIn("HOMOFILIA_RED", nd)
        self.assertIn("AMPLIFICACION_VIRAL", nd)

    def test_temporal_keys(self):
        t = MASSIVE_EMPIRICAL_MASTER["temporal"]
        self.assertIn("MEDIA_VIDA_DIGITAL", t)
        self.assertIn("ELASTICIDAD_CONFIANZA", t)
        self.assertIn("CICLO_ATENCION", t)
        self.assertIn("FATIGA_OUTRAGE", t)

    def test_game_theory_keys(self):
        gt = MASSIVE_EMPIRICAL_MASTER["game_theory"]
        self.assertIn("EQUILIBRIO_NASH_SOCIAL", gt)
        self.assertIn("COSTO_DISIDENCIA", gt)


class TestRuntimeParams(unittest.TestCase):

    def test_required_keys(self):
        required = [
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
        for key in required:
            self.assertIn(key, MASSIVE_RUNTIME_PARAMS, msg=f"Missing key: {key}")

    def test_numeric_params_in_range(self):
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
            val = MASSIVE_RUNTIME_PARAMS[key]
            self.assertGreaterEqual(val, -1.0, msg=f"{key}={val} < -1.0")
            self.assertLessEqual(val, 1.0, msg=f"{key}={val} > 1.0")

    def test_social_lambda_positive(self):
        self.assertGreater(MASSIVE_RUNTIME_PARAMS["social_influence_lambda"], 0.0)

    def test_temperature_positive(self):
        self.assertGreater(MASSIVE_RUNTIME_PARAMS["temperature"], 0.0)


class TestApplyEmpiricalProfile(unittest.TestCase):

    def test_does_not_mutate_input(self):
        original = {"rango": "[-1, 1] — Bipolar", "proveedor": "heurístico"}
        original_copy = dict(original)
        apply_empirical_profile(original)
        self.assertEqual(original, original_copy)

    def test_returns_dict(self):
        result = apply_empirical_profile({})
        self.assertIsInstance(result, dict)

    def test_efecto_vecinos_peso_set(self):
        result = apply_empirical_profile({})
        expected_engine = build_empirical_engine_config()
        self.assertIn("efecto_vecinos_peso", result)
        self.assertAlmostEqual(
            result["efecto_vecinos_peso"],
            expected_engine["efecto_vecinos_peso"],
        )

    def test_ruido_base_within_engine_range(self):
        result = apply_empirical_profile({})
        ruido = result["ruido_base"]
        self.assertGreaterEqual(ruido, 0.01)
        self.assertLessEqual(ruido, 0.20)

    def test_ruido_base_scaling_matches_temperature(self):
        """ruido_base uses the shared engine calibration helper."""
        result = apply_empirical_profile({})
        expected = build_empirical_engine_config()["ruido_base"]
        self.assertAlmostEqual(result["ruido_base"], expected, places=6)

    def test_adds_additional_engine_calibration_keys(self):
        result = apply_empirical_profile({})
        self.assertIn("ruido_desconfianza", result)
        self.assertGreaterEqual(result["ruido_desconfianza"], 0.04)
        self.assertLessEqual(result["ruido_desconfianza"], 0.18)
        self.assertIn("hk_epsilon", result)
        self.assertGreaterEqual(result["hk_epsilon"], HK_EPSILON_MIN)
        self.assertLessEqual(result["hk_epsilon"], HK_EPSILON_MAX)
        self.assertEqual(result["umbral_media"], TIPPING_POINT_MEAN)
        self.assertEqual(result["umbral_std"], TIPPING_POINT_STD)
        self.assertIn("homofilia_tasa", result)
        self.assertGreaterEqual(result["homofilia_tasa"], 0.02)
        self.assertLessEqual(result["homofilia_tasa"], 0.12)

    def test_confirmation_bias_comes_from_empirical_master(self):
        result = apply_empirical_profile({})
        self.assertAlmostEqual(
            result["sesgo_confirmacion"],
            build_empirical_engine_config()["sesgo_confirmacion"],
            places=6,
        )

    def test_payoff_cc_set_from_runtime(self):
        result = apply_empirical_profile({})
        cc = result["strategic"]["payoff_matrix"]["cc"]
        self.assertAlmostEqual(cc, MASSIVE_RUNTIME_PARAMS["payoff_coordination"])

    def test_payoff_dd_set_from_runtime(self):
        result = apply_empirical_profile({})
        dd = result["strategic"]["payoff_matrix"]["dd"]
        self.assertAlmostEqual(dd, MASSIVE_RUNTIME_PARAMS["payoff_defection"])

    def test_profile_version_tag(self):
        result = apply_empirical_profile({})
        self.assertIn("_empirical_profile", result)
        self.assertEqual(
            result["_empirical_profile"],
            MASSIVE_EMPIRICAL_MASTER["meta"]["version"],
        )

    def test_preserves_existing_keys(self):
        cfg = {"rango": "[-1, 1] — Bipolar", "proveedor": "heurístico", "api_key": "xyz"}
        result = apply_empirical_profile(cfg)
        self.assertEqual(result["rango"], "[-1, 1] — Bipolar")
        self.assertEqual(result["proveedor"], "heurístico")
        self.assertEqual(result["api_key"], "xyz")


class TestExportToJson(unittest.TestCase):

    def test_returns_valid_json(self):
        raw = export_to_json()
        parsed = json.loads(raw)
        self.assertIn("master", parsed)
        self.assertIn("runtime_params", parsed)

    def test_master_and_runtime_present(self):
        parsed = json.loads(export_to_json())
        self.assertIn("meta", parsed["master"])
        self.assertIn("temperature", parsed["runtime_params"])
        self.assertIn("engine_defaults", parsed)

    def test_write_to_disk(self):
        import os
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tf:
            tmp_path = tf.name
        try:
            export_to_json(tmp_path)
            self.assertTrue(os.path.exists(tmp_path))
            with open(tmp_path, encoding="utf-8") as fh:
                parsed = json.load(fh)
            self.assertIn("master", parsed)
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()
