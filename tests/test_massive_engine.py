"""
Tests para el Motor de Simulación Masiva de MASSIVE (massive_engine.py).

Cubre:
  1. Cuantización: precisión, redondeo y simetría de quantize/dequantize.
  2. LOD (build_super_agents): forma, suma de counts, rango de valores.
  3. ActiveSet: comportamiento de activación y desactivación.
  4. MassiveSimEngine: forma del estado, rango de opiniones, métricas de resumen.
  5. apply_shock: activa clústeres y perturba opiniones correctamente.
  6. memory_report: campos requeridos y coherencia de ahorro.
  7. Rendimiento: N=50 000, M=100, 200 steps en tiempo razonable.
"""

import time

import numpy as np
import pytest

from massive_engine import (
    ActiveSet,
    MassiveSimEngine,
    _OPINION_MAX,
    _OPINION_MIN,
    build_super_agents,
    dequantize_state,
    quantize_state,
)


# ============================================================
# 1. CUANTIZACIÓN
# ============================================================

class TestQuantization:

    def test_quantize_shape(self):
        x = np.random.uniform(-1, 1, (50, 5))
        x[:, 1:] = np.random.uniform(0, 1, (50, 4))
        q = quantize_state(x)
        assert q.shape == x.shape
        assert q.dtype == np.uint8

    def test_quantize_opinion_range(self):
        """Opinión -1.0 → 0, +1.0 → 255."""
        x = np.array([[-1.0, 0.5, 0.5, 0.5, 0.5],
                      [ 1.0, 0.5, 0.5, 0.5, 0.5]])
        q = quantize_state(x)
        assert q[0, 0] == 0
        assert q[1, 0] == 255

    def test_quantize_unit_range(self):
        """Dimensiones unipolares: 0.0 → 0, 1.0 → 255."""
        x = np.zeros((2, 5))
        x[0, 1:] = 0.0
        x[1, 1:] = 1.0
        q = quantize_state(x)
        assert np.all(q[0, 1:] == 0)
        assert np.all(q[1, 1:] == 255)

    def test_roundtrip_precision(self):
        """Precisión de ida y vuelta ≤ 1/255 del rango (≈ 0.008)."""
        rng = np.random.default_rng(0)
        x = rng.uniform(-1, 1, (200, 1))
        q = quantize_state(x)
        x2 = dequantize_state(q)[:, 0]
        # Precisión máxima posible con uint8: 2/255 ≈ 0.00784
        assert np.max(np.abs(x[:, 0] - x2)) <= 2.0 / 255.0 + 1e-6

    def test_dequantize_opinion_midpoint(self):
        """q=127 → opinión ≈ 0 (neutro en rango bipolar)."""
        q = np.array([[127, 128, 128, 128, 128]], dtype=np.uint8)
        x = dequantize_state(q)
        assert abs(x[0, 0]) < 0.01   # cercano a 0

    def test_dequantize_unipolar_midpoint(self):
        """q=127 → dimensión unipolar ≈ 0.5."""
        q = np.array([[128, 127, 127, 127, 127]], dtype=np.uint8)
        x = dequantize_state(q)
        assert abs(x[0, 1] - 0.5) < 0.01


# ============================================================
# 2. LOD — build_super_agents
# ============================================================

class TestBuildSuperAgents:

    def test_shape(self):
        centers, counts = build_super_agents(N=1000, M=50)
        assert centers.shape == (50, 5)
        assert counts.shape == (50,)

    def test_counts_sum_to_N(self):
        N, M = 10_000, 100
        _, counts = build_super_agents(N, M)
        assert counts.sum() == N

    def test_counts_all_positive(self):
        _, counts = build_super_agents(N=500, M=30)
        assert np.all(counts >= 1)

    def test_opinion_in_range(self):
        centers, _ = build_super_agents(N=1000, M=40)
        assert np.all(centers[:, 0] >= _OPINION_MIN)
        assert np.all(centers[:, 0] <= _OPINION_MAX)

    def test_unipolar_dims_in_range(self):
        centers, _ = build_super_agents(N=1000, M=40)
        assert np.all(centers[:, 1:] >= 0.0)
        assert np.all(centers[:, 1:] <= 1.0)

    def test_reproducibility(self):
        c1, n1 = build_super_agents(100, 10, seed=7)
        c2, n2 = build_super_agents(100, 10, seed=7)
        np.testing.assert_array_equal(c1, c2)
        np.testing.assert_array_equal(n1, n2)


# ============================================================
# 3. ActiveSet
# ============================================================

class TestActiveSet:

    def test_initial_all_active(self):
        aset = ActiveSet(M=20, sleep_threshold=1e-3)
        assert aset.mask.all()
        assert aset.n_active == 20

    def test_sleep_fraction_initial_zero(self):
        aset = ActiveSet(M=20)
        assert aset.sleep_fraction == 0.0

    def test_unchanged_agents_sleep(self):
        """Agentes que no cambian pasan a dormir."""
        M = 10
        aset = ActiveSet(M, sleep_threshold=0.01)
        adj = np.eye(M)   # sin vecinos externos
        x0 = np.zeros((M, 5))
        x1 = x0.copy()   # sin cambios
        aset.step(x0, x1, adj)
        assert aset.n_active == 0

    def test_changed_agents_stay_active(self):
        """Agentes que cambian suficientemente permanecen activos."""
        M = 10
        aset = ActiveSet(M, sleep_threshold=0.01)
        adj = np.zeros((M, M))
        x0 = np.zeros((M, 5))
        x1 = x0.copy()
        x1[3, 0] = 0.5   # agente 3 cambió
        aset.step(x0, x1, adj)
        assert aset.mask[3]

    def test_neighbors_of_changed_reactivated(self):
        """Los vecinos de agentes que cambiaron se reactivan."""
        M = 5
        aset = ActiveSet(M, sleep_threshold=0.01)
        # Agente 0 conectado con agente 1
        adj = np.zeros((M, M))
        adj[0, 1] = 1.0
        x0 = np.zeros((M, 5))
        x1 = x0.copy()
        x1[0, 0] = 0.5   # agente 0 cambió
        aset.step(x0, x1, adj)
        assert aset.mask[1]   # vecino del agente que cambió

    def test_history_grows(self):
        aset = ActiveSet(M=5)
        adj = np.eye(5)
        x0 = np.zeros((5, 5))
        x1 = x0.copy()
        for _ in range(3):
            aset.step(x0, x1, adj)
        assert len(aset.active_history) == 4  # inicial + 3 pasos


# ============================================================
# 4. MassiveSimEngine — funcionalidad básica
# ============================================================

class TestMassiveSimEngine:

    def test_init_no_crash(self):
        """El motor se inicializa sin errores."""
        engine = MassiveSimEngine(N=1000, M=20, seed=0)
        assert engine.N == 1000
        assert engine.M == 20

    def test_auto_M(self):
        """M se calcula automáticamente como max(50, sqrt(N))."""
        engine = MassiveSimEngine(N=10_000)
        assert engine.M == max(50, int(10_000 ** 0.5))

    def test_run_returns_dict(self):
        engine = MassiveSimEngine(N=500, M=20, seed=1)
        result = engine.run(steps=5)
        assert isinstance(result, dict)

    def test_required_keys_in_result(self):
        engine = MassiveSimEngine(N=500, M=20, seed=2)
        result = engine.run(steps=5)
        for key in ("mean_opinion", "std_opinion", "polarization",
                    "mean_cooperation", "n_agents", "n_clusters",
                    "n_steps", "elapsed_seconds", "memory_savings_pct",
                    "opinion_history", "active_history",
                    "cluster_opinions", "cluster_counts"):
            assert key in result, f"Falta clave '{key}' en resultado"

    def test_opinion_in_valid_range(self):
        """Opinión media siempre en [-1, 1]."""
        engine = MassiveSimEngine(N=1000, M=30, seed=3)
        result = engine.run(steps=20)
        assert _OPINION_MIN <= result["mean_opinion"] <= _OPINION_MAX

    def test_cluster_opinions_in_range(self):
        """Opinión de cada clúster en [-1, 1] tras la simulación."""
        engine = MassiveSimEngine(N=1000, M=30, seed=4)
        engine.run(steps=10)
        assert np.all(engine.x[:, 0] >= _OPINION_MIN)
        assert np.all(engine.x[:, 0] <= _OPINION_MAX)

    def test_state_shape_preserved(self):
        engine = MassiveSimEngine(N=500, M=25, seed=5)
        engine.run(steps=10)
        assert engine.x.shape == (25, 5)

    def test_opinion_history_length(self):
        steps = 15
        engine = MassiveSimEngine(N=500, M=20, seed=6)
        result = engine.run(steps=steps)
        assert len(result["opinion_history"]) == steps + 1

    def test_n_steps_accumulates(self):
        engine = MassiveSimEngine(N=300, M=15, seed=7)
        engine.run(steps=5)
        engine.run(steps=7)
        assert engine._steps_run == 12

    def test_quantize_disabled(self):
        """El motor funciona con cuantización desactivada."""
        engine = MassiveSimEngine(N=500, M=20, quantize=False, seed=8)
        result = engine.run(steps=5)
        assert result["mean_opinion"] is not None

    def test_event_driven_disabled(self):
        """El motor funciona sin event-driven."""
        engine = MassiveSimEngine(N=500, M=20, event_driven=False, seed=9)
        result = engine.run(steps=5)
        assert all(f == 1.0 for f in result["active_history"])

    def test_event_driven_some_sleep(self):
        """Con event-driven y threshold alto, los super-agentes pasan a dormir."""
        # threshold=0.5 >> noise típico (~0.01/paso) → la mayoría duerme tras el 1er paso
        engine = MassiveSimEngine(
            N=500, M=30,
            event_driven=True,
            sleep_threshold=0.5,
            seed=10,
        )
        result = engine.run(steps=10)
        # Después del primer paso, al menos un paso debe tener fracción < 100%
        assert (result["active_history"] < 1.0).any(), (
            "Se esperaba que al menos un paso tuviera super-agentes dormidos "
            "con sleep_threshold=0.5 (por encima del ruido típico ~0.01/paso)"
        )


# ============================================================
# 5. apply_shock
# ============================================================

class TestApplyShock:

    def test_shock_changes_opinions(self):
        engine = MassiveSimEngine(N=500, M=20, seed=0)
        x_before = engine.x[:, 0].copy()
        engine.apply_shock(shock_value=0.5, fraction=0.5, seed=0)
        assert not np.allclose(engine.x[:, 0], x_before)

    def test_shock_stays_in_range(self):
        engine = MassiveSimEngine(N=500, M=20, seed=0)
        engine.apply_shock(shock_value=10.0, fraction=1.0)   # saturar intencionalmente
        assert np.all(engine.x[:, 0] >= _OPINION_MIN)
        assert np.all(engine.x[:, 0] <= _OPINION_MAX)

    def test_shock_activates_clusters(self):
        """Los clústeres perturbados se marcan como activos."""
        engine = MassiveSimEngine(N=500, M=20, event_driven=True, seed=0)
        # Primero ejecutar algunos pasos para que algunos duerman
        engine.run(steps=10)
        engine.apply_shock(shock_value=0.3, fraction=1.0)
        assert engine._active_set is not None
        # Al menos los clústeres afectados están activos
        assert engine._active_set.n_active > 0


# ============================================================
# 6. memory_report
# ============================================================

class TestMemoryReport:

    def test_required_keys(self):
        engine = MassiveSimEngine(N=10_000, M=100)
        rep = engine.memory_report
        for key in ("n_agents", "n_clusters", "float64_MB",
                    "lod_MB", "final_MB", "savings_pct",
                    "strategies", "gpu_backend"):
            assert key in rep

    def test_savings_positive(self):
        engine = MassiveSimEngine(N=10_000, M=100, quantize=True)
        rep = engine.memory_report
        assert rep["savings_pct"] > 0.0

    def test_savings_over_99pct_large_N(self):
        """Con N=1M y M=300 y cuantización, el ahorro supera el 99%."""
        engine = MassiveSimEngine(N=1_000_000, M=300, quantize=True)
        rep = engine.memory_report
        assert rep["savings_pct"] > 99.0

    def test_lod_strategy_always_present(self):
        engine = MassiveSimEngine(N=1000, M=50)
        assert "LOD (Super-Agentes)" in engine.memory_report["strategies"]

    def test_quantize_strategy_when_enabled(self):
        engine = MassiveSimEngine(N=1000, M=50, quantize=True)
        assert "Cuantización uint8" in engine.memory_report["strategies"]

    def test_event_driven_strategy_when_enabled(self):
        engine = MassiveSimEngine(N=1000, M=50, event_driven=True)
        assert "Event-Driven" in engine.memory_report["strategies"]


# ============================================================
# 7. RENDIMIENTO
# ============================================================

class TestPerformance:

    def test_large_N_runs_fast(self):
        """N=50 000, M=100, 200 steps en < 15 segundos."""
        engine = MassiveSimEngine(N=50_000, M=100, seed=0)
        # Warm-up Numba JIT
        engine.run(steps=2)

        engine2 = MassiveSimEngine(N=50_000, M=100, seed=1)
        t0 = time.perf_counter()
        engine2.run(steps=200)
        elapsed = time.perf_counter() - t0
        assert elapsed < 15.0, (
            f"200 pasos con N=50k tardaron {elapsed:.2f}s — esperado < 15s"
        )

    def test_million_agents_init_fast(self):
        """Inicializar 1M de agentes (como M=500 clústeres) en < 5s."""
        t0 = time.perf_counter()
        engine = MassiveSimEngine(N=1_000_000, M=500, seed=0)
        elapsed = time.perf_counter() - t0
        assert elapsed < 5.0, (
            f"Inicialización de 1M agentes tardó {elapsed:.2f}s — esperado < 5s"
        )

    def test_memory_savings_scale(self):
        """El ahorro de memoria escala correctamente con N y M."""
        small = MassiveSimEngine(N=1000,   M=50,  quantize=True)
        large = MassiveSimEngine(N=100_000, M=50,  quantize=True)
        # Ambos usan el mismo M → mismo almacenamiento real
        assert abs(small.memory_report["final_MB"] - large.memory_report["final_MB"]) < 0.01
        # Pero el ahorro relativo es mayor para N grande
        assert large.memory_report["savings_pct"] > small.memory_report["savings_pct"]
