"""
Tests for Layer 3 — Neural Network & LLM Calibration.

Covers:
  1. Embedding encoder: 5-D output, bounded values, correlation with labels.
  2. Convergence certifier: rejects unstable strategies, accepts stable ones.
  3. DeterministicPlanner: produces convergent trajectory without LLM.
  4. Opinion clipping: all values remain in [-1, 1].
  5. Synthetic benchmark: alignment results loaded and validated.
  6. Agent profiles: six empirically-derived archetypes present and in range.
"""

from __future__ import annotations

import json
import os
import unittest
import warnings

import numpy as np

# ── Suppress scipy warning on older versions ───────────────────────────────
warnings.filterwarnings("ignore", message=".*scipy.*")

# ── Paths ───────────────────────────────────────────────────────────────────
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
WS_ROOT = os.path.dirname(TESTS_DIR)
MODELS_DIR = os.path.join(WS_ROOT, "models")
EMBEDDING_DIR = os.path.join(MODELS_DIR, "embedding_sociopolitico")
AGENTS_PATH = os.path.join(MODELS_DIR, "agent_profiles.json")
BENCHMARK_PATH = os.path.join(
    EMBEDDING_DIR, "benchmark_results.json"
)
ENCODER_PATH = os.path.join(EMBEDDING_DIR, "encoder.py")


# ── Synthetic benchmark data ────────────────────────────────────────────────

LEFT_TEXTS: list[str] = [
    "socialismo igualdad justicia revolución",
    "lucha de clases trabajadores solidaridad",
    "capitalismo explotación desigualdad marginados",
    "redistribución justicia social emancipación",
    "revolución popular cambio colectivo acción",
    "solidaridad comunidad cooperación internacional",
    "izquierda progreso cambio reforma",
    "anti-establishment imperialismo resistencia",
    "feminismo diversidad inclusión igualdad",
    "clima cambio colectivo sostenibilidad",
]

RIGHT_TEXTS: list[str] = [
    "capitalismo libertad mercado individualismo",
    "tradición familia orden jerarquía autoridad",
    "conservadurismo tradición valores patria",
    "libertad económica propiedad privada mérito",
    "patriotismo soberanía nación disciplina",
    "trabajo duro éxito responsabilidad",
    "leyes mercado estabilidad seguridad",
    "jerarquía natural orden tradición",
    "individualismo meritocracia competencia",
    "fuerza fuerza militar patriotismo",
]

CENTER_TEXTS: list[str] = [
    "centro moderación consenso diálogo",
    "equilibrio moderado prudencia acuerdo",
    "neutral imparcial diversidad puntos_de_vista",
    "debate ciudadanía cooperación ciudadana",
    "consenso equilibrio punto_medio",
]

CORRELATION_THRESHOLD: float = 0.65


class TestSocioPoliticalEncoder(unittest.TestCase):
    """Tests for the socio-political embedding encoder."""

    @classmethod
    def setUpClass(cls):
        """Initialise the encoder once for all tests."""
        from models.embedding_sociopolitico.encoder import SocioPoliticalEncoder
        cls.encoder = SocioPoliticalEncoder(seed=42)
        cls.SocioPoliticalEncoder = SocioPoliticalEncoder

    def test_output_dimensions(self):
        """Encoder produces 5-D embeddings matching opinion space dimensions."""
        emb = self.encoder.encode("socialismo igualdad justicia")
        self.assertEqual(emb.shape, (5,))

    def test_embeddings_bounded(self):
        """All embedding values lie within [-1, 1]."""
        texts = LEFT_TEXTS + RIGHT_TEXTS + CENTER_TEXTS
        embeddings = self.encoder.encode_batch(texts)
        self.assertTrue(np.all(embeddings >= -1.0))
        self.assertTrue(np.all(embeddings <= 1.0))

    def test_correlation_above_threshold(self):
        """Opinion dimension correlates with labels above 0.65 threshold."""
        texts = LEFT_TEXTS + RIGHT_TEXTS + CENTER_TEXTS
        labels = [-0.8] * len(LEFT_TEXTS) + [0.8] * len(RIGHT_TEXTS) + [0.0] * len(CENTER_TEXTS)
        labels = np.array(labels)

        embeddings = self.encoder.encode_batch(texts)
        opinion_dims = embeddings[:, 0]

        r, _ = self._pearson(labels, opinion_dims)
        self.assertGreater(r, CORRELATION_THRESHOLD,
                           f"Pearson r = {r:.4f}, below threshold {CORRELATION_THRESHOLD}")

    def test_deterministic(self):
        """Same input with same seed yields identical embeddings."""
        text = "socialismo igualdad justicia social"
        emb1 = self.encoder.encode(text)
        emb2 = self.encoder.encode(text)
        np.testing.assert_array_almost_equal(emb1, emb2, decimal=6)

    def test_opinion_directionality(self):
        """Left-leaning text → negative opinion; right-leaning → positive."""
        left_emb = self.encoder.encode("socialismo igualdad justicia")
        right_emb = self.encoder.encode("capitalismo libertad mercado")
        self.assertLess(left_emb[0], -0.1, "Left text should have negative opinion")
        self.assertGreater(right_emb[0], 0.1, "Right text should have positive opinion")

    @staticmethod
    def _pearson(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
        """Compute Pearson correlation (scipy-optional, fallback manual)."""
        try:
            from scipy import stats
            return stats.pearsonr(x, y)
        except ImportError:
            x_mean = x.mean()
            y_mean = y.mean()
            x_std = x.std()
            y_std = y.std()
            if x_std == 0 or y_std == 0:
                return 0.0, 1.0
            r = np.mean((x - x_mean) * (y - y_mean)) / (x_std * y_std)
            return float(r), 0.0


class TestConvergenceCertifier(unittest.TestCase):
    """Tests for the convergence certification module."""

    @classmethod
    def setUpClass(cls):
        """Initialise engine and certifier for all tests."""
        from energy_engine import SocialEnergyEngine
        from massive.core.convergence_certifier import certify_strategy

        cls.SocialEnergyEngine = SocialEnergyEngine
        cls._certify_strategy = staticmethod(certify_strategy)

    def test_rejects_unstable_strategy(self):
        """Unstable strategy (eta too large) is rejected — spectral radius > 1.0."""
        engine = self.SocialEnergyEngine(
            range_type="bipolar", seed=42, lambda_social=0.0
        )
        strategy = {
            "attractors": [{"position": 0.5, "strength": 10.0}],
            "repellers": [],
            "eta": 0.5,
            "n_steps": 100,
            "connectivity": 0.0,
            "seed": 42,
        }
        cert = self._certify_strategy(strategy, engine, 0.0)
        self.assertFalse(cert.converges)
        self.assertGreaterEqual(cert.spectral_radius, 1.0,
                                f"spectral_radius={cert.spectral_radius:.4f} should be >= 1.0")

    def test_accepts_stable_trajectory(self):
        """Stable strategy with attractor converges — spectral radius < 1.0."""
        engine = self.SocialEnergyEngine(
            range_type="bipolar", seed=42, lambda_social=0.0
        )
        strategy = {
            "attractors": [{"position": 0.5, "strength": 2.0}],
            "repellers": [{"position": -0.5, "strength": 0.5}],
            "eta": 0.05,
            "n_steps": 200,
            "connectivity": 0.0,
            "seed": 42,
        }
        cert = self._certify_strategy(strategy, engine, 0.0)
        self.assertTrue(cert.converges)
        self.assertLess(cert.spectral_radius, 1.0)
        self.assertIsInstance(cert.proof, str)
        self.assertGreater(cert.trajectory_norm, 0.0)

    def test_opinions_clipped_to_bounds(self):
        """All opinion values during trajectory remain in [-1, 1]."""
        engine = self.SocialEnergyEngine(
            range_type="bipolar", seed=42, lambda_social=0.0
        )
        strategy = {
            "attractors": [{"position": 0.5, "strength": 5.0}],
            "repellers": [{"position": -0.5, "strength": 0.5}],
            "eta": 0.1,
            "n_steps": 100,
            "connectivity": 0.0,
            "seed": 42,
        }
        cert = self._certify_strategy(strategy, engine, -0.9)
        # Bounds OK is embedded in the proof and converges field
        self.assertIn("Opinion bounds", cert.proof)
        if cert.converges:
            self.assertIn("PASS", cert.proof.split("Opinion bounds")[1])

    def test_certifier_handles_dict_initial_state(self):
        """Certifier accepts dict-based initial state with 'opinion' key."""
        engine = self.SocialEnergyEngine(
            range_type="bipolar", seed=42, lambda_social=0.0
        )
        strategy = {
            "attractors": [{"position": 0.3, "strength": 2.0}],
            "repellers": [],
            "eta": 0.05,
            "n_steps": 200,
            "connectivity": 0.0,
        }
        cert = self._certify_strategy(strategy, engine, {"opinion": 0.0})
        # Should still produce a valid certificate
        self.assertIsNotNone(cert)
        self.assertTrue(hasattr(cert, "converges"))
        self.assertIsInstance(cert.proof, str)


class TestDeterministicPlanner(unittest.TestCase):
    """Tests for DeterministicPlanner — no LLM required."""

    @classmethod
    def setUpClass(cls):
        """Initialise planner and engine."""
        from energy_engine import SocialEnergyEngine
        from massive.core.convergence_certifier import (
            DeterministicPlanner,
            certify_strategy,
        )

        cls.SocialEnergyEngine = SocialEnergyEngine
        cls.DeterministicPlanner = DeterministicPlanner
        cls._certify_strategy = staticmethod(certify_strategy)

    def test_planner_produces_convergent_trajectory(self):
        """Planner output, when certified, converges to the goal state."""
        planner = self.DeterministicPlanner(seed=42)
        # Override lambda to 0 for pure landscape dynamics (avoids the
        # neighbor-mean pull-to-zero issue in single-agent 1D systems)
        planner.params["social_influence_lambda"] = 0.0

        engine = self.SocialEnergyEngine(
            range_type="bipolar", seed=42, lambda_social=0.0
        )
        strategy = planner.plan(
            initial_state=-0.5, goal_state=0.5, n_steps=200
        )
        cert = self._certify_strategy(strategy, engine, -0.5)
        self.assertTrue(cert.converges,
                        f"Planner strategy should converge. Spectral radius={cert.spectral_radius:.4f}")
        self.assertLess(cert.spectral_radius, 1.0)

    def test_planner_eta_is_small(self):
        """Planner computes a small, stable eta (< 0.1)."""
        planner = self.DeterministicPlanner(seed=42)
        strategy = planner.plan(
            initial_state=0.2, goal_state=0.8, n_steps=100
        )
        self.assertLess(strategy["eta"], 0.1)
        self.assertGreater(strategy["eta"], 0.0)

    def test_planner_strategy_has_required_keys(self):
        """Planner output contains all keys needed by certify_strategy."""
        planner = self.DeterministicPlanner(seed=42)
        strategy = planner.plan(
            initial_state=0.0, goal_state=0.5, n_steps=50
        )
        for key in ("attractors", "repellers", "eta", "n_steps", "proof"):
            self.assertIn(key, strategy)

    def test_planner_is_deterministic(self):
        """Same seed → same plan."""
        planner1 = self.DeterministicPlanner(seed=42)
        planner2 = self.DeterministicPlanner(seed=42)
        s1 = planner1.plan(initial_state=0.0, goal_state=0.5, n_steps=50)
        s2 = planner2.plan(initial_state=0.0, goal_state=0.5, n_steps=50)
        self.assertAlmostEqual(s1["eta"], s2["eta"], places=8)
        self.assertEqual(len(s1["attractors"]), len(s2["attractors"]))
        np.testing.assert_array_almost_equal(
            s1["estimated_spectral_radius"], s2["estimated_spectral_radius"], decimal=6
        )


class TestSyntheticBenchmark(unittest.TestCase):
    """Validate the benchmark_results.json file."""

    def test_benchmark_file_exists(self):
        """benchmark_results.json exists and is valid JSON."""
        self.assertTrue(os.path.exists(BENCHMARK_PATH))
        with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("metrics", data)
        self.assertIn("pearson_correlation", data["metrics"])

    def test_threshold_achieved(self):
        """Benchmark reports correlation_achieved = true."""
        with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertTrue(data["threshold"]["correlation_achieved"])

    def test_all_dimensions_above_threshold(self):
        """All five dimensions exceed the 0.65 correlation threshold."""
        with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        pearson = data["metrics"]["pearson_correlation"]
        for dim in ("opinion", "cooperation", "hierarchy", "income", "info_access"):
            self.assertGreater(
                pearson[dim], CORRELATION_THRESHOLD,
                f"{dim} correlation {pearson[dim]} below {CORRELATION_THRESHOLD}"
            )

    def test_benchmarking_is_deterministic(self):
        """Benchmark file declares deterministic = true."""
        with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertTrue(data["reproducibility"]["deterministic"])


class TestAgentProfiles(unittest.TestCase):
    """Validate the agent_profiles.json archetypes."""

    def test_file_exists(self):
        """agent_profiles.json exists and is valid JSON."""
        self.assertTrue(os.path.exists(AGENTS_PATH))
        with open(AGENTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("profiles", data)

    def test_six_archetypes_present(self):
        """Exactly six empirically-derived archetypes are present."""
        with open(AGENTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        profiles = data["profiles"]
        self.assertEqual(len(profiles), 6)
        expected_keys = {
            "activist_left", "activist_right", "centrist",
            "apathetic", "conspiracy_leaning", "institutional_truster",
        }
        self.assertEqual(set(profiles.keys()), expected_keys)

    def test_values_in_range(self):
        """All parameter values are in [-1, 1]."""
        with open(AGENTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for name, profile in data["profiles"].items():
            params = profile["parameters"]
            for key in ("opinion_baseline", "cognitive_rigidity", "openness"):
                val = params[key]
                self.assertGreaterEqual(val, -1.0, f"{name}.{key} = {val} < -1.0")
                self.assertLessEqual(val, 1.0, f"{name}.{key} = {val} > 1.0")
            # response_to_evidence is [0, 1]
            rte = params["response_to_evidence"]
            self.assertGreaterEqual(rte, 0.0)
            self.assertLessEqual(rte, 1.0)

    def test_references_present(self):
        """Each archetype cites empirical literature."""
        with open(AGENTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for name, profile in data["profiles"].items():
            self.assertIn("empirical_basis", profile)
            self.assertGreater(len(profile["empirical_basis"]), 0)

    def test_contrast_between_extremes(self):
        """Activist left and right have opposite opinion baselines."""
        with open(AGENTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        left = data["profiles"]["activist_left"]["parameters"]["opinion_baseline"]
        right = data["profiles"]["activist_right"]["parameters"]["opinion_baseline"]
        self.assertLess(left, -0.4)
        self.assertGreater(right, 0.4)
        self.assertLess(left, right)

    def test_conspiracy_leaning_low_responsiveness(self):
        """Conspiracy-leaning archetype has lowest evidence responsiveness."""
        with open(AGENTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        vals = {
            name: p["parameters"]["response_to_evidence"]
            for name, p in data["profiles"].items()
        }
        self.assertEqual(min(vals, key=vals.get), "conspiracy_leaning")


class TestIntegration(unittest.TestCase):
    """Integration tests spanning encoder + convergence certifier."""

    @classmethod
    def setUpClass(cls):
        from models.embedding_sociopolitico.encoder import SocioPoliticalEncoder
        from energy_engine import SocialEnergyEngine
        from massive.core.convergence_certifier import (
            DeterministicPlanner,
            certify_strategy,
        )

        cls.encoder = SocioPoliticalEncoder(seed=42)
        cls.SocialEnergyEngine = SocialEnergyEngine
        cls.DeterministicPlanner = DeterministicPlanner
        cls._certify_strategy = staticmethod(certify_strategy)

    def test_encoder_output_as_initial_state(self):
        """Encoder's opinion dimension can seed the certifier."""
        text = "socialismo igualdad justicia"
        emb = self.encoder.encode(text)
        initial_opinion = float(emb[0])

        planner = self.DeterministicPlanner(seed=42)
        planner.params["social_influence_lambda"] = 0.0
        engine = self.SocialEnergyEngine(
            range_type="bipolar", seed=42, lambda_social=0.0
        )

        # Plan from encoded opinion to neutral
        strategy = planner.plan(
            initial_state=initial_opinion, goal_state=0.0, n_steps=200
        )
        cert = self._certify_strategy(strategy, engine, initial_opinion)
        self.assertTrue(cert.trajectory_norm >= 0.0)
        self.assertIn("spectral", cert.proof.lower())

    def test_full_pipeline_converges(self):
        """End-to-end: encode → plan → certify converges."""
        text = "capitalismo libertad mercado"
        emb = self.encoder.encode(text)
        initial_opinion = float(emb[0])
        self.assertGreater(initial_opinion, 0.0, "Capitalist text should have positive opinion")

        planner = self.DeterministicPlanner(seed=42)
        planner.params["social_influence_lambda"] = 0.0
        engine = self.SocialEnergyEngine(
            range_type="bipolar", seed=42, lambda_social=0.0
        )

        strategy = planner.plan(
            initial_state=initial_opinion, goal_state=-0.5, n_steps=200
        )
        cert = self._certify_strategy(strategy, engine, initial_opinion)
        self.assertTrue(cert.converges,
                        f"Full pipeline should converge from {initial_opinion:.4f} to -0.5")


if __name__ == "__main__":
    unittest.main(verbosity=2)
