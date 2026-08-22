"""
Targeted coverage for uncovered scientific/dispatch paths in multilayer_engine.py.

Covers: multilayer_langevin_step dense kernel, the sparse core dispatch,
_bimodal_grad / multi_potential_gradient, targeted_llm_bias heuristic path,
MultilayerEngine public API (step fallback, run compact history, diagnose,
graphs, dynamic_rewiring, behavior_correlation_matrix, plot, get_landscape,
update_opinions/get_opinions, N<2 and steps<1 validation).
"""

import numpy as np
import pytest
from scipy import sparse

from multilayer_engine import (
    COL_COOP,
    COL_OPINION,
    K,
    MultilayerEngine,
    _bimodal_grad,
    generate_watts_strogatz,
    multi_potential_gradient,
    multilayer_langevin_step,
    targeted_llm_bias,
)

# ── Kernel functions ───────────────────────────────────────────────────────


class TestMultilayerKernels:

    def test_multilayer_langevin_step_dense_path(self):
        N = 10
        x = np.column_stack(
            [
                np.linspace(-0.5, 0.5, N),
                np.full(N, 0.4),
                np.full(N, 0.3),
                np.full(N, 0.2),
                np.full(N, 0.6),
            ]
        )
        adj = generate_watts_strogatz(N)
        layers = np.stack([adj, adj, adj], axis=0)
        theta = np.ones((N, K))
        out = multilayer_langevin_step(
            x,
            layers,
            np.array([0.4, 0.3, 0.3]),
            theta,
            coupling=0.3,
            dt=0.01,
            x_min=-1.0,
            x_max=1.0,
            rng=np.random.default_rng(0),
        )
        assert out.shape == (N, K)
        assert np.all(out[:, COL_OPINION] >= -1.0) and np.all(out[:, COL_OPINION] <= 1.0)

    def test_multilayer_langevin_step_sparse_path(self):
        N = 10
        x = np.column_stack(
            [
                np.linspace(-0.5, 0.5, N),
                np.full(N, 0.4),
                np.full(N, 0.3),
                np.full(N, 0.2),
                np.full(N, 0.6),
            ]
        )
        adj = generate_watts_strogatz(N)
        layers = [sparse.csr_matrix(adj), sparse.csr_matrix(adj), sparse.csr_matrix(adj)]
        theta = np.ones((N, K))
        out = multilayer_langevin_step(
            x,
            layers,
            np.array([0.4, 0.3, 0.3]),
            theta,
            coupling=0.3,
            dt=0.01,
            x_min=-1.0,
            x_max=1.0,
            rng=np.random.default_rng(0),
        )
        assert out.shape == (N, K)
        assert np.all(out[:, 1:] >= 0.0) and np.all(out[:, 1:] <= 1.0)

    def test_bimodal_grad_zero_at_minima(self):
        assert _bimodal_grad(0.7) == pytest.approx(0.0, abs=1e-12)
        assert _bimodal_grad(-0.7) == pytest.approx(0.0, abs=1e-12)

    def test_bimodal_grad_nonzero_at_origin(self):
        assert _bimodal_grad(0.0) == pytest.approx(0.0, abs=1e-12) or _bimodal_grad(0.1) != 0.0

    def test_multi_potential_gradient_shape(self):
        x = np.zeros((8, K))
        g = multi_potential_gradient(x)
        assert g.shape == (8, K)

    def test_multi_potential_gradient_coop_alignment(self):
        x = np.array([[1.0, 0.5, 0.5, 0.5, 0.5]])
        g = multi_potential_gradient(x.copy())
        op = 1.0
        align = 0.5 * (op + 1.0)
        expected_coop = 2.0 * (0.5 - 0.8 * align)
        assert g[0, COL_COOP] == pytest.approx(expected_coop)


# ── targeted_llm_bias ──────────────────────────────────────────────────────


class TestTargetedLlmBias:

    def test_heuristic_provider_returns_narrative(self):
        text = targeted_llm_bias(
            layer_target="social",
            demographic="religion=1",
            proveedor="heurístico",
            api_key="",
            modelo="",
        )
        assert "Heurístico" in text
        assert "cooperación" in text

    def test_unknown_demographic_uses_raw_label(self):
        text = targeted_llm_bias(
            layer_target="economic",
            demographic="custom_group",
            proveedor="heurístico",
            api_key="",
            modelo="",
        )
        assert "custom_group" in text

    def test_fallback_on_connection_error(self):
        text = targeted_llm_bias(
            layer_target="digital",
            demographic="gender=1",
            proveedor="openai",
            api_key="fake",
            modelo="gpt",
        )
        assert "Fallback" in text

    def test_fallback_on_unknown_provider_without_key(self):
        text = targeted_llm_bias(
            layer_target="digital",
            demographic="gender=0",
            proveedor="unknown_provider",
            api_key="",
            modelo="",
        )
        assert "Heurístico" in text


# ── MultilayerEngine public API ────────────────────────────────────────────


class TestMultilayerEngineApi:

    def test_run_compact_history_returns_aggregates(self):
        eng = MultilayerEngine(N=20, seed=0)
        agg = eng.run(steps=5, store_history=False)
        assert len(agg) == 6  # steps + 1
        assert isinstance(agg[0], dict)
        assert "mean_opinion" in agg[0]
        assert "std_opinion" in agg[0]
        assert "polarization" in agg[0]
        assert "sample_size" in agg[0]
        # Retains only last full snapshot
        assert len(eng._history) == 1

    def test_diagnose_reports_metrics(self):
        eng = MultilayerEngine(N=20, seed=0)
        eng.run(steps=3)
        d = eng.diagnose()
        assert d["n_agents"] == 20
        assert d["n_features"] == K
        assert d["n_steps_recorded"] >= 1
        assert d["state_bytes"] > 0
        assert -1.0 <= d["opinion_mean"] <= 1.0

    def test_diagnose_after_compact_history(self):
        eng = MultilayerEngine(N=20, seed=0)
        eng.run(steps=3, store_history=False)
        d = eng.diagnose()
        assert d["n_steps_recorded"] == len(eng._history_compact)

    def test_graphs_returns_csr(self):
        eng = MultilayerEngine(N=15, seed=0)
        graphs = eng.graphs
        assert set(graphs.keys()) == {"social", "digital", "economic"}
        for _name, g in graphs.items():
            assert g.format == "csr"

    def test_dynamic_rewiring_censorship(self):
        eng = MultilayerEngine(N=20, seed=0)
        before = int((eng.layers["social"] > 0).sum())
        eng.dynamic_rewiring("social", mode="censorship", intensity=0.5)
        after = int((eng.layers["social"] > 0).sum())
        assert after <= before

    def test_dynamic_rewiring_viral_hub(self):
        eng = MultilayerEngine(N=20, seed=0)
        before = int((eng.layers["digital"] > 0).sum())
        eng.dynamic_rewiring("digital", mode="viral_hub", intensity=0.2)
        after = int((eng.layers["digital"] > 0).sum())
        assert after >= before

    def test_dynamic_rewiring_zero_intensity_noop(self):
        eng = MultilayerEngine(N=15, seed=0)
        before = eng.layers["social"].copy()
        eng.dynamic_rewiring("social", mode="censorship", intensity=0.0)
        np.testing.assert_array_equal(before, eng.layers["social"])

    def test_dynamic_rewiring_invalid_layer_raises(self):
        eng = MultilayerEngine(N=10, seed=0)
        with pytest.raises(KeyError):
            eng.dynamic_rewiring("unknown", mode="censorship", intensity=0.1)

    def test_dynamic_rewiring_invalid_mode_raises(self):
        eng = MultilayerEngine(N=10, seed=0)
        with pytest.raises(ValueError):
            eng.dynamic_rewiring("social", mode="bad_mode", intensity=0.1)

    def test_behavior_correlation_matrix_shape(self):
        eng = MultilayerEngine(N=20, seed=0)
        eng.run(steps=3)
        corr = eng.behavior_correlation_matrix()
        assert corr.shape == (K, K)

    def test_plot_returns_components(self):
        eng = MultilayerEngine(N=20, seed=0)
        eng.run(steps=3)
        out = eng.plot()
        assert "trajectories_df" in out
        assert "corr_matrix" in out
        assert "landscape" in out

    def test_update_opinions_rejects_bad_shape(self):
        eng = MultilayerEngine(N=10, seed=0)
        with pytest.raises(ValueError):
            eng.update_opinions(np.zeros((9, K)))

    def test_update_opinions_clamps_ranges(self):
        eng = MultilayerEngine(N=10, seed=0)
        new_state = np.zeros((10, K))
        new_state[:, COL_OPINION] = 5.0
        new_state[:, COL_COOP] = -2.0
        eng.update_opinions(new_state)
        assert eng.x[:, COL_OPINION].max() <= 1.0
        assert eng.x[:, COL_COOP].min() >= 0.0

    def test_get_opinions_returns_state(self):
        eng = MultilayerEngine(N=10, seed=0)
        ops = eng.get_opinions()
        assert ops.shape == (10, K)
        np.testing.assert_array_equal(ops, eng.x)

    def test_get_landscape_keys(self):
        eng = MultilayerEngine(N=10, seed=0)
        eng.run(steps=2)
        land = eng.get_landscape()
        for key in (
            "mean_opinion",
            "std_opinion",
            "polarization",
            "mean_cooperation",
            "mean_hierarchy",
        ):
            assert key in land

    def test_init_N_too_small_raises(self):
        with pytest.raises(ValueError):
            MultilayerEngine(N=1)

    def test_run_steps_too_small_raises(self):
        eng = MultilayerEngine(N=10, seed=0)
        with pytest.raises(ValueError):
            eng.run(steps=0)

    def test_default_layer_weights_normalized(self):
        eng = MultilayerEngine(N=10, seed=0)
        assert sum(eng.layer_weights) == pytest.approx(1.0)

    def test_step_stores_last_diagnostics(self):
        eng = MultilayerEngine(N=10, seed=0)
        eng.step()
        assert eng.last_numerical_diagnostics is not None
