"""
tests/test_mamba_engine.py — Tests unitarios para mamba_engine.py.

Verifica formas de tensores, comportamiento sin NaN, propiedades de la
celda SSM y el baseline PVU-BS sin requerir modelos entrenados.
"""

import pytest
import unittest
import numpy as np


class TestMambaEngineImport(unittest.TestCase):
    """Verifica que la importación de mamba_engine falla limpiamente sin torch."""

    def test_import_no_crash_without_torch(self):
        """mamba_engine importa si torch está instalado, y falla con ImportError si no."""
        try:
            import torch
            import mamba_engine
            self.assertTrue(hasattr(mamba_engine, "MambaCell"))
            self.assertTrue(hasattr(mamba_engine, "MambaSSM"))
            self.assertTrue(hasattr(mamba_engine, "MambaBaseline"))
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
class TestMambaCell(unittest.TestCase):
    """Tests para MambaCell."""

    def setUp(self):
        from mamba_engine import MambaCell
        self.cell = MambaCell(d_model=8, d_state=16)

    def test_output_shapes(self):
        import torch
        h = torch.zeros(4, 16)
        u = torch.randn(4, 8)
        y, h_new = self.cell(h, u)
        self.assertEqual(y.shape, (4, 8))
        self.assertEqual(h_new.shape, (4, 16))

    def test_no_nan_output(self):
        import torch
        h = torch.randn(2, 16)
        u = torch.randn(2, 8)
        y, h_new = self.cell(h, u)
        self.assertFalse(torch.isnan(y).any().item())
        self.assertFalse(torch.isnan(h_new).any().item())

    def test_state_updates(self):
        """El estado cambia con la entrada."""
        import torch
        h = torch.zeros(1, 16)
        u = torch.randn(1, 8)
        y, h_new = self.cell(h, u)
        self.assertFalse(torch.allclose(h, h_new))

    def test_A_diagonal_negative(self):
        """A debe ser diagonal negativa para garantizar estabilidad."""
        import torch
        A = -torch.exp(self.cell.A_log)
        self.assertTrue((A < 0).all().item())

    def test_delta_positive(self):
        """Δ (paso de discretización) debe ser siempre positivo."""
        import torch
        u = torch.randn(10, 8)
        # delta_proj incluye Softplus → siempre positivo
        delta = self.cell.delta_proj(u)
        self.assertTrue((delta > 0).all().item())


@skip_no_torch
class TestMambaSSM(unittest.TestCase):
    """Tests para MambaSSM (red recurrente sobre secuencia)."""

    def setUp(self):
        from mamba_engine import MambaSSM
        self.model = MambaSSM(d_model=8, d_state=16, n_layers=2)

    def test_output_shape(self):
        import torch
        x = torch.randn(3, 10, 8)  # (batch, seq_len, d_model)
        out = self.model(x)
        self.assertEqual(out.shape, (3, 8))  # último paso

    def test_no_nan(self):
        import torch
        x = torch.randn(2, 6, 8)
        out = self.model(x)
        self.assertFalse(torch.isnan(out).any().item())

    def test_seq_len_1(self):
        """Secuencia de longitud 1 no debe fallar."""
        import torch
        x = torch.randn(4, 1, 8)
        out = self.model(x)
        self.assertEqual(out.shape, (4, 8))

    def test_different_inputs_different_outputs(self):
        """Entradas distintas producen salidas distintas."""
        import torch
        x1 = torch.randn(2, 5, 8)
        x2 = torch.randn(2, 5, 8)
        out1 = self.model(x1)
        out2 = self.model(x2)
        self.assertFalse(torch.allclose(out1, out2))


@skip_no_torch
class TestMambaBaseline(unittest.TestCase):
    """Tests para MambaBaseline — interfaz predict(train, horizon)."""

    def setUp(self):
        from mamba_engine import MambaBaseline
        # Epocas mínimas para que los tests sean rápidos
        self.baseline = MambaBaseline(d_model=4, d_state=8, n_layers=1, lags=3, epochs=5)

    def test_predict_output_shape(self):
        train = np.linspace(0.3, 0.7, 20)
        preds = self.baseline.predict(train, horizon=5)
        self.assertEqual(len(preds), 5)

    def test_predict_values_in_range(self):
        """Predicciones clippeadas a [0, 1]."""
        train = np.linspace(0.2, 0.8, 15)
        preds = self.baseline.predict(train, horizon=4)
        self.assertTrue((preds >= 0.0).all())
        self.assertTrue((preds <= 1.0).all())

    def test_predict_no_nan(self):
        train = np.random.default_rng(0).uniform(0.3, 0.7, 20)
        preds = self.baseline.predict(train, horizon=6)
        self.assertFalse(np.isnan(preds).any())

    def test_short_series_fallback(self):
        """Series cortas no deben lanzar excepción — fallback a último valor."""
        train = np.array([0.5, 0.52])  # muy corta
        preds = self.baseline.predict(train, horizon=3)
        self.assertEqual(len(preds), 3)

    def test_name_attribute(self):
        from mamba_engine import MambaBaseline
        self.assertEqual(MambaBaseline.name, "mamba_ssm")

    def test_predict_returns_numpy(self):
        train = np.linspace(0.4, 0.6, 12)
        preds = self.baseline.predict(train, horizon=3)
        self.assertIsInstance(preds, np.ndarray)


class TestMambaInGetAllBaselines(unittest.TestCase):
    """Verifica que MambaBaseline se registra en get_all_baselines()."""

    def test_get_all_baselines_includes_mamba_when_torch_available(self):
        from benchmarks.baselines import get_all_baselines
        baselines = get_all_baselines()
        names = [getattr(b, "name", "") for b in baselines]
        if TORCH_AVAILABLE:
            self.assertIn("mamba_ssm", names)
        # Si torch no está disponible, el baseline se omite silenciosamente
        # — verificar que get_all_baselines() no lanza excepción
        self.assertIsInstance(baselines, list)
        self.assertGreater(len(baselines), 0)


if __name__ == "__main__":
    unittest.main()
