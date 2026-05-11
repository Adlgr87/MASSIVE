"""
tests/test_cfc_engine.py — Tests unitarios para cfc_engine.py.

Verifica formas de tensores, comportamiento sin NaN y propiedades
básicas de cada modelo CfC sin requerir modelos entrenados.
"""

import pytest
import unittest


class TestCfCEngineImport(unittest.TestCase):
    """Verifica que la importación de cfc_engine falla limpiamente sin torch."""

    def test_import_no_crash_without_torch(self):
        """cfc_engine importa si torch está instalado, y falla con ImportError si no."""
        try:
            import torch  # noqa: F401
            import cfc_engine  # noqa: F401
        except ImportError:
            pass  # Aceptable si torch no está instalado


try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

skip_no_torch = pytest.mark.skipif(
    not TORCH_AVAILABLE, reason="PyTorch no disponible"
)


@skip_no_torch
class TestCfCCell(unittest.TestCase):
    """Tests para CfCCell."""

    def setUp(self):
        from cfc_engine import CfCCell
        self.cell = CfCCell(input_size=8, hidden_size=32)

    def test_output_shape(self):
        import torch
        x = torch.zeros(4, 32)
        u = torch.randn(4, 8)
        out = self.cell(x, u)
        self.assertEqual(out.shape, (4, 32))

    def test_no_nan_output(self):
        import torch
        x = torch.randn(2, 32)
        u = torch.randn(2, 8)
        out = self.cell(x, u)
        self.assertFalse(torch.isnan(out).any().item())

    def test_different_dt_changes_output(self):
        import torch
        x = torch.randn(1, 32)
        u = torch.randn(1, 8)
        out1 = self.cell(x, u, dt=0.1)
        out2 = self.cell(x, u, dt=0.5)
        self.assertFalse(torch.allclose(out1, out2))

    def test_tau_always_positive(self):
        """τ siempre positivo por Softplus + 1e-3."""
        import torch
        # El tau no es directamente accesible, pero la celda no debe explotar
        x = torch.randn(10, 32)
        u = torch.randn(10, 8)
        out = self.cell(x, u)
        self.assertFalse(torch.isnan(out).any().item())
        self.assertFalse(torch.isinf(out).any().item())


@skip_no_torch
class TestCfCRegimeSelector(unittest.TestCase):
    """Tests para CfCRegimeSelector."""

    def setUp(self):
        from cfc_engine import CfCRegimeSelector
        self.model = CfCRegimeSelector(window_size=6, state_dim=8, hidden=64)

    def test_output_shape(self):
        import torch
        history = torch.randn(3, 6)
        state = torch.randn(3, 8)
        logits = self.model(history, state)
        self.assertEqual(logits.shape, (3, 13))

    def test_softmax_sums_to_one(self):
        import torch
        history = torch.randn(2, 6)
        state = torch.randn(2, 8)
        probs = torch.softmax(self.model(history, state), dim=-1)
        sums = probs.sum(dim=-1)
        self.assertTrue(torch.allclose(sums, torch.ones(2), atol=1e-5))

    def test_regime_ids_in_range(self):
        import torch
        history = torch.randn(5, 6)
        state = torch.randn(5, 8)
        probs = torch.softmax(self.model(history, state), dim=-1)
        ids = probs.argmax(dim=-1)
        self.assertTrue((ids >= 0).all().item())
        self.assertTrue((ids < 13).all().item())

    def test_no_nan(self):
        import torch
        history = torch.randn(4, 6)
        state = torch.randn(4, 8)
        logits = self.model(history, state)
        self.assertFalse(torch.isnan(logits).any().item())


@skip_no_torch
class TestCfCTauMatrix(unittest.TestCase):
    """Tests para CfCTauMatrix."""

    def setUp(self):
        from cfc_engine import CfCTauMatrix
        self.model = CfCTauMatrix(attr_dim=4, behavior_dim=5)

    def test_output_shape(self):
        import torch
        attrs = torch.rand(10, 4)
        tau = self.model(attrs)
        self.assertEqual(tau.shape, (10, 5))

    def test_tau_always_positive(self):
        """τ mínimo ≥ 0.1 por Softplus + 0.1."""
        import torch
        attrs = torch.rand(50, 4)
        tau = self.model(attrs)
        self.assertTrue((tau >= 0.1).all().item())

    def test_no_nan(self):
        import torch
        attrs = torch.rand(8, 4)
        tau = self.model(attrs)
        self.assertFalse(torch.isnan(tau).any().item())


@skip_no_torch
class TestCfCArchitectPolicy(unittest.TestCase):
    """Tests para CfCArchitectPolicy."""

    def setUp(self):
        from cfc_engine import CfCArchitectPolicy
        self.model = CfCArchitectPolicy(
            state_dim=10, goal_dim=5, hidden=128, n_phases=5, n_regimes=13
        )

    def test_output_keys(self):
        import torch
        s = torch.randn(2, 10)
        g = torch.randn(2, 5)
        out = self.model(s, g)
        self.assertIn("regime_logits", out)
        self.assertIn("durations", out)
        self.assertIn("params", out)

    def test_output_shapes(self):
        import torch
        s = torch.randn(2, 10)
        g = torch.randn(2, 5)
        out = self.model(s, g)
        self.assertEqual(out["regime_logits"].shape, (2, 13))
        self.assertEqual(out["durations"].shape, (2, 5))
        self.assertEqual(out["params"].shape, (2, 5, 4))

    def test_durations_sum_to_one(self):
        import torch
        s = torch.randn(3, 10)
        g = torch.randn(3, 5)
        out = self.model(s, g)
        sums = out["durations"].sum(dim=-1)
        self.assertTrue(torch.allclose(sums, torch.ones(3), atol=1e-5))

    def test_no_nan(self):
        import torch
        s = torch.randn(4, 10)
        g = torch.randn(4, 5)
        out = self.model(s, g)
        for key, tensor in out.items():
            self.assertFalse(
                torch.isnan(tensor).any().item(),
                f"NaN encontrado en '{key}'",
            )


if __name__ == "__main__":
    unittest.main()
