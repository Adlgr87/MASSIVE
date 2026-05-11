"""
tests/test_cfc_router.py — Tests unitarios para cfc_router.py.

Verifica que el router:
  1. Funciona sin modelos .pt (todos los métodos retornan fallback limpiamente).
  2. El singleton se comporta correctamente.
  3. Con modelos sintéticos en memoria, las predicciones tienen el tipo correcto.
  4. La integración con simulator.py no rompe el flujo existente.
"""

import unittest
import numpy as np


class TestCfCRouterFallback(unittest.TestCase):
    """Sin modelos .pt, el router devuelve siempre fallback limpio."""

    def setUp(self):
        # Forzar instancia nueva sin modelos
        from cfc_router import CfCRouter
        CfCRouter._instance = None
        self.router = CfCRouter()
        # Asegurar que no hay modelos cargados (estado fresh)
        self.router._sel = None
        self.router._tau = None
        self.router._arch = None

    def test_select_regime_fallback(self):
        history = [0.5, 0.52, 0.54, 0.55, 0.53, 0.51]
        state = {"opinion": 0.5, "propaganda": 0.7, "confianza": 0.4}
        rid, source, conf = self.router.select_regime(history, state)
        self.assertEqual(source, "llm_fallback")
        # When source is llm_fallback, regime_id must always be -1
        self.assertEqual(rid, -1)
        self.assertEqual(conf, 0.0)

    def test_compute_tau_matrix_fallback(self):
        attrs = np.random.rand(10, 4).astype(np.float32)
        result = self.router.compute_tau_matrix(attrs)
        self.assertIsNone(result)

    def test_propose_strategy_fallback(self):
        state = {"opinion": 0.5, "propaganda": 0.7}
        goal = [1.0, 0.0, -0.5, 0.0, 0.0]
        result = self.router.propose_strategy(state, goal)
        self.assertIsNone(result)

    def test_status_all_false(self):
        status = self.router.status
        self.assertFalse(status["regime_selector"])
        self.assertFalse(status["tau_matrix"])
        self.assertFalse(status["architect_policy"])

    def test_select_regime_short_history(self):
        """Con historial < 6 y sin modelo, siempre fallback."""
        history = [0.5, 0.52]
        state = {"opinion": 0.5}
        rid, source, conf = self.router.select_regime(history, state)
        self.assertEqual(source, "llm_fallback")

    def tearDown(self):
        # Limpiar singleton para no afectar otros tests
        from cfc_router import CfCRouter
        CfCRouter._instance = None


class TestCfCRouterSingleton(unittest.TestCase):
    """El singleton retorna siempre la misma instancia."""

    def test_singleton_identity(self):
        from cfc_router import CfCRouter
        CfCRouter._instance = None
        a = CfCRouter.get()
        b = CfCRouter.get()
        self.assertIs(a, b)

    def tearDown(self):
        from cfc_router import CfCRouter
        CfCRouter._instance = None


try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

import pytest
skip_no_torch = pytest.mark.skipif(
    not TORCH_AVAILABLE, reason="PyTorch no disponible"
)


@skip_no_torch
class TestCfCRouterWithSyntheticModel(unittest.TestCase):
    """Con un modelo CfC sintético en memoria, las predicciones son válidas."""

    def setUp(self):
        from cfc_router import CfCRouter
        from cfc_engine import CfCRegimeSelector, CfCTauMatrix
        import torch

        CfCRouter._instance = None
        self.router = CfCRouter()

        # Inyectar modelos sintéticos (no entrenados, pesos aleatorios)
        self.router._sel = CfCRegimeSelector(window_size=6, state_dim=8, hidden=64)
        self.router._sel.eval()
        self.router._tau = CfCTauMatrix(attr_dim=4, behavior_dim=5)
        self.router._tau.eval()
        self.router._torch_available = True

    def tearDown(self):
        from cfc_router import CfCRouter
        CfCRouter._instance = None

    def test_select_regime_returns_tuple(self):
        history = [0.5, 0.52, 0.54, 0.55, 0.53, 0.51]
        state = {
            "opinion": 0.5, "propaganda": 0.7, "confianza": 0.4,
            "opinion_grupo_a": 0.72, "opinion_grupo_b": 0.28,
            "trust": 0.4, "ews_variance": 0.0, "ews_autocorr": 0.0,
        }
        rid, source, conf = self.router.select_regime(history, state)
        self.assertIsInstance(rid, int)
        self.assertIn(source, ("cfc", "llm_fallback"))
        self.assertGreaterEqual(conf, 0.0)
        self.assertLessEqual(conf, 1.0)

    def test_select_regime_id_in_range(self):
        history = [0.3, 0.35, 0.4, 0.42, 0.38, 0.36]
        state = {
            "opinion": 0.4, "propaganda": 0.3, "confianza": 0.6,
            "opinion_grupo_a": 0.6, "opinion_grupo_b": 0.2,
            "trust": 0.5, "ews_variance": 0.01, "ews_autocorr": 0.1,
        }
        rid, source, conf = self.router.select_regime(history, state)
        # Si el modelo acepta, el regime debe estar en [0, 12]
        if source == "cfc":
            self.assertGreaterEqual(rid, 0)
            self.assertLess(rid, 13)
        else:
            self.assertEqual(rid, -1)

    def test_compute_tau_matrix_shape(self):
        attrs = np.random.rand(20, 4).astype(np.float32)
        tau = self.router.compute_tau_matrix(attrs)
        self.assertIsNotNone(tau)
        self.assertEqual(tau.shape, (20, 5))

    def test_compute_tau_matrix_positive(self):
        attrs = np.random.rand(10, 4).astype(np.float32)
        tau = self.router.compute_tau_matrix(attrs)
        self.assertIsNotNone(tau)
        self.assertTrue((tau >= 0.1).all())

    def test_compute_tau_no_nan(self):
        attrs = np.random.rand(5, 4).astype(np.float32)
        tau = self.router.compute_tau_matrix(attrs)
        self.assertFalse(np.isnan(tau).any())


class TestCfCSimulatorIntegration(unittest.TestCase):
    """
    Verifica que simulator.py funciona correctamente con CFC_AVAILABLE=False
    (comportamiento idéntico al de antes de la integración).
    """

    def test_simular_works_without_cfc_models(self):
        """La simulación completa no debe romperse sin modelos CfC."""
        from simulator import simular
        np.random.seed(0)
        estado = {
            "opinion": 0.5,
            "propaganda": 0.7,
            "confianza": 0.4,
            "opinion_grupo_a": 0.72,
            "opinion_grupo_b": 0.28,
            "pertenencia_grupo": 0.65,
        }
        historial = simular(estado, pasos=10, cada_n_pasos=5, verbose=False)
        self.assertEqual(len(historial), 11)
        self.assertTrue(all(0.0 <= h["opinion"] <= 1.0 for h in historial))

    def test_cfc_available_is_boolean(self):
        """CFC_AVAILABLE debe ser siempre un bool (True o False, nunca None)."""
        import simulator
        self.assertIsInstance(simulator.CFC_AVAILABLE, bool)

    def test_cfc_fast_path_does_not_change_output_format(self):
        """El fast path CfC no altera el formato de historial devuelto."""
        from simulator import simular
        np.random.seed(42)
        estado = {
            "opinion": 0.6,
            "propaganda": 0.5,
            "confianza": 0.5,
            "opinion_grupo_a": 0.7,
            "opinion_grupo_b": 0.3,
        }
        historial = simular(estado, pasos=15, cada_n_pasos=3, verbose=False)
        # Verificar que los campos clave existen en todos los pasos desde t=1
        for h in historial[1:]:
            self.assertIn("_regla", h)
            self.assertIn("_regla_nombre", h)
            self.assertIn("opinion", h)


if __name__ == "__main__":
    unittest.main()
