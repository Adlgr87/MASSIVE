import json
import unittest

from empirical_calibration import (
    HK_EPSILON_MAX,
    HK_EPSILON_MIN,
    MASSIVE_EMPIRICAL_MASTER,
    MASSIVE_RUNTIME_PARAMS,
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

    def test_values_in_bipolar_range(self):
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
            "temperature", "social_influence_lambda", "attractor_depth",
            "repeller_strength", "payoff_coordination", "payoff_defection",
            "narrative_decay_rate", "saturation_threshold",
            "cultural_profile", "validation_flags",
        ]
        for key in required:
            self.assertIn(key, MASSIVE_RUNTIME_PARAMS, msg=f"Missing key: {key}")

    def test_numeric_params_in_range(self):
        numeric_keys = [
            "temperature", "social_influence_lambda", "attractor_depth",
            "repeller_strength", "payoff_coordination", "payoff_defection",
            "narrative_decay_rate", "saturation_threshold",
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
        _ = apply_empirical_profile(original)
        self.assertEqual(original, original_copy)

    def test_adds_expected_keys(self):
        result = apply_empirical_profile({})
        expected_keys = [
            "efecto_vecinos_peso", "ruido_base", "ruido_desconfianza",
            "alpha_blend", "sesgo_confirmacion", "hk_epsilon",
            "competencia_peso", "umbral_media", "umbral_std", "homofilia_tasa",
            "strategic", "_empirical_profile",
        ]
        for key in expected_keys:
            self.assertIn(key, result, msg=f"Missing key: {key}")

    def test_strategic_config_structure(self):
        result = apply_empirical_profile({})
        s = result["strategic"]
        self.assertIn("enabled", s)
        self.assertIn("payoff_matrix", s)
        self.assertIn("strategic_weight", s)
        self.assertFalse(s["enabled"])

    def test_ruido_base_in_plausible_range(self):
        result = apply_empirical_profile({})
        self.assertGreaterEqual(result["ruido_base"], 0.01)
        self.assertLessEqual(result["ruido_base"], 0.20)

    def test_hk_epsilon_in_plausible_range(self):
        result = apply_empirical_profile({})
        self.assertGreaterEqual(result["hk_epsilon"], 0.20)
        self.assertLessEqual(result["hk_epsilon"], 0.35)

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
        self.assertEqual(result["_empirical_profile"], MASSIVE_EMPIRICAL_MASTER["meta"]["version"])

    def test_preserves_existing_keys(self):
        cfg = {"rango": "[-1, 1] — Bipolar", "proveedor": "heurístico", "api_key": "xyz"}
        result = apply_empirical_profile(cfg)
        self.assertEqual(result["rango"], "[-1, 1] — Bipolar")
        self.assertEqual(result["proveedor"], "heurístico")


class TestExportToJson(unittest.TestCase):
    def test_returns_valid_json(self):
        raw = export_to_json()
        parsed = json.loads(raw)
        self.assertIn("master", parsed)
        self.assertIn("runtime_params", parsed)
        self.assertIn("engine_defaults", parsed)

    def test_master_matches_module_level(self):
        raw = export_to_json()
        parsed = json.loads(raw)
        self.assertEqual(parsed["master"]["meta"]["version"], "1.1.0")

    def test_write_to_disk(self):
        import os
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tf:
            tmp_path = tf.name
        try:
            export_to_json(tmp_path)
            with open(tmp_path) as fh:
                parsed = json.load(fh)
            self.assertIn("master", parsed)
        finally:
            os.unlink(tmp_path)
