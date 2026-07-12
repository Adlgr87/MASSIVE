import numpy as np
import pytest

from benchmarks.butterfly_diagnostic import run_butterfly_diagnostic_core
from massive_engine import MassiveEngine
from multilayer_engine import MultilayerEngine
from simulator import IntegratedSimulator


class TestMassiveEngineManualShock:
    def test_apply_shock_uniform_changes_target_layer(self):
        engine = MassiveEngine({"n_agents": 100, "seed": 0})
        before = engine.agents[:, 0].copy()
        engine.apply_shock(
            magnitude=0.4,
            distribution="uniform",
            target_layer=0,
            affected_fraction=0.3,
            seed=1,
        )
        assert not np.allclose(before, engine.agents[:, 0])
        assert np.all(engine.agents[:, 0] >= -1.0)
        assert np.all(engine.agents[:, 0] <= 1.0)

    def test_apply_shock_pareto_keeps_non_opinion_in_unit_range(self):
        engine = MassiveEngine({"n_agents": 80, "seed": 0})
        engine.apply_shock(
            magnitude=0.3,
            distribution="pareto",
            target_layer=2,
            affected_fraction=0.4,
            seed=2,
        )
        assert np.all(engine.agents[:, 2] >= 0.0)
        assert np.all(engine.agents[:, 2] <= 1.0)


class TestDynamicRewiring:
    @pytest.mark.skip(reason="dynamic_rewiring removido de MultilayerEngine en refactor — ver audit_report.md")
    def test_dynamic_rewiring_updates_layer(self):
        engine = MultilayerEngine(N=60, seed=3)
        original = engine.layers["social"].copy()
        engine.dynamic_rewiring("social", mode="censorship", intensity=0.2)
        updated = engine.layers["social"]
        assert updated.shape == original.shape
        assert not np.allclose(original, updated)

    @pytest.mark.skip(reason="graphs property removido de MultilayerEngine en refactor — ver audit_report.md")
    def test_graphs_property_returns_sparse_layers(self):
        engine = MultilayerEngine(N=25, seed=1)
        graphs = engine.graphs
        assert set(graphs.keys()) == {"social", "digital", "economic"}
        assert all(hasattr(m, "tocsr") for m in graphs.values())


class TestIntegratedSimulator:
    def test_integrated_simulator_runs_with_dynamic_modules(self):
        sim = IntegratedSimulator(
            {
                "n_agents": 50,
                "n_ticks": 6,
                "seed": 4,
                "enable_levy_jumps": True,
                "levy_lambda": 0.8,
                "enable_dynamic_topology": True,
                "topology_update_freq": 1,
                "butterfly_interval": 2,
                "diffusion_sigma": 0.0,
            }
        )
        history = sim.run()
        assert len(history) == 6
        assert len(sim.topology_history) >= 1
        assert len(sim.lyapunov_history) >= 1
        assert np.all(sim.massive_engine.agents[:, 0] >= -1.0)
        assert np.all(sim.massive_engine.agents[:, 0] <= 1.0)

    def test_integrated_simulator_emits_context_hooks(self):
        captured = []
        n_ticks = 2
        sim = IntegratedSimulator(
            {
                "n_agents": 20,
                "n_ticks": n_ticks,
                "seed": 5,
                "router_feedback_hook": lambda payload: captured.append(("router", payload)),
                "social_architect_hook": lambda payload: captured.append(("architect", payload)),
            }
        )
        sim.run()
        assert len(captured) == n_ticks * 2
        for _, payload in captured:
            assert {"tick", "polarization", "viral_activity", "lyapunov"} <= set(payload.keys())


class TestButterflyDiagnosticCore:
    def test_butterfly_core_returns_divergence_payload(self):
        rng = np.random.default_rng(0)
        agents = rng.uniform(-0.3, 0.3, (40, 5))
        graph = np.eye(40)
        result = run_butterfly_diagnostic_core(
            {"agents": agents, "graphs": {"social": graph}, "n_ticks_left": 6}
        )
        assert "divergence_score" in result
        assert "max_distance" in result
        assert result["divergence_score"] >= 0.0
