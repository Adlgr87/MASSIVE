"""Tests for sparse multilayer engine, sparse EnKF, and stability modules."""

from __future__ import annotations

import logging
from typing import Generator

import numpy as np
import pytest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sparse_rng() -> np.random.Generator:
    return np.random.default_rng(42)


@pytest.fixture
def sample_adjacency() -> np.ndarray:
    """3-node social network adjacency."""
    return np.array([
        [0.0, 0.8, 0.2],
        [0.8, 0.0, 0.6],
        [0.2, 0.6, 0.0],
    ])


@pytest.fixture
def sample_features() -> np.ndarray:
    """Feature matrix for 3 nodes, 2 features."""
    return np.array([
        [0.5, 0.3],
        [0.4, 0.6],
        [0.7, 0.2],
    ])


@pytest.fixture
def sample_layer(sample_features, sample_adjacency):
    """Single-layer setup."""
    from massive_core.numerics.multilayer_engine_sparse import LayerState
    from scipy import sparse
    return LayerState(
        node_features=sample_features,
        graph_adjacency=sparse.csr_matrix(sample_adjacency),
        agent_types=np.array([0, 1, 0]),
        layer_id="test_layer",
    )


@pytest.fixture
def sample_layers(sample_features, sample_adjacency):
    """Two-layer setup."""
    from massive_core.numerics.multilayer_engine_sparse import LayerState
    from scipy import sparse
    adj = np.array([[0.0, 0.7, 0.3], [0.7, 0.0, 0.5], [0.3, 0.5, 0.0]])
    feat = np.array([[0.6, 0.4], [0.3, 0.7], [0.8, 0.1]])
    return [
        LayerState(
            node_features=sample_features,
            graph_adjacency=sparse.csr_matrix(sample_adjacency),
            agent_types=np.array([0, 1, 0]),
            layer_id="layer_1",
        ),
        LayerState(
            node_features=feat,
            graph_adjacency=sparse.csr_matrix(adj),
            agent_types=np.array([1, 0, 1]),
            layer_id="layer_2",
        ),
    ]


# ---------------------------------------------------------------------------
# SparseMultilayerEngine tests
# ---------------------------------------------------------------------------


class TestSparseMultilayerEngine:
    """Tests for the sparse multilayer engine."""

    def test_initialisation_single_layer(self, sample_layer):
        from massive_core.numerics.multilayer_engine_sparse import SparseMultilayerEngine
        engine = SparseMultilayerEngine(
            layers=[sample_layer],
            interaction_matrix=np.array([[1.0]]),
        )
        assert engine.n_layers == 1
        assert len(engine.layers) == 1

    def test_initialisation_multi_layer(self, sample_layers):
        from massive_core.numerics.multilayer_engine_sparse import SparseMultilayerEngine
        engine = SparseMultilayerEngine(
            layers=sample_layers,
            interaction_matrix=np.array([[1.0, 0.3], [0.3, 1.0]]),
        )
        assert engine.n_layers == 2

    def test_initialisation_invalid_interaction_matrix(self, sample_layers):
        from massive_core.numerics.multilayer_engine_sparse import SparseMultilayerEngine
        with pytest.raises(ValueError, match="interaction_matrix shape"):
            SparseMultilayerEngine(
                layers=sample_layers,
                interaction_matrix=np.eye(3),
            )

    def test_run_simulation_single_layer(self, sample_layer):
        from massive_core.numerics.multilayer_engine_sparse import SparseMultilayerEngine
        engine = SparseMultilayerEngine(
            layers=[sample_layer],
            interaction_matrix=np.array([[1.0]]),
            max_iterations=3,
        )
        result = engine.run_simulation()
        assert len(result.final_states) == 1
        assert result.final_states[0].shape == sample_layer.node_features.shape
        assert result.simulation_time > 0

    def test_run_simulation_multi_layer(self, sample_layers):
        from massive_core.numerics.multilayer_engine_sparse import SparseMultilayerEngine
        engine = SparseMultilayerEngine(
            layers=sample_layers,
            interaction_matrix=np.array([[1.0, 0.2], [0.2, 1.0]]),
            max_iterations=2,
        )
        result = engine.run_simulation()
        assert len(result.final_states) == 2
        assert result.simulation_time > 0

    def test_convergence(self, sample_layer):
        from massive_core.numerics.multilayer_engine_sparse import SparseMultilayerEngine
        engine = SparseMultilayerEngine(
            layers=[sample_layer],
            interaction_matrix=np.array([[1.0]]),
            max_iterations=100,
            convergence_threshold=1e-6,
        )
        result = engine.run_simulation()
        # Should converge within max iterations
        assert result.simulation_time > 0
        assert len(result.metrics_history) > 0

    def test_network_metrics(self, sample_layer):
        from massive_core.numerics.multilayer_engine_sparse import SparseMultilayerEngine
        engine = SparseMultilayerEngine(
            layers=[sample_layer],
            interaction_matrix=np.array([[1.0]]),
        )
        metrics = engine.get_network_metrics()
        assert "layer_0_test_layer" in metrics
        assert "avg_degree" in metrics["layer_0_test_layer"]
        assert "density" in metrics["layer_0_test_layer"]

    def test_add_layer(self, sample_layer):
        from massive_core.numerics.multilayer_engine_sparse import SparseMultilayerEngine, LayerState
        from scipy import sparse
        engine = SparseMultilayerEngine(layers=[sample_layer])
        new_layer = LayerState(
            node_features=np.array([[0.5, 0.5]]),
            graph_adjacency=sparse.csr_matrix(np.array([[0.0]])),
            layer_id="new_layer",
        )
        engine.add_layer(new_layer)
        assert engine.n_layers == 2
        assert len(engine.layers) == 2

    def test_remove_layer(self, sample_layers):
        from massive_core.numerics.multilayer_engine_sparse import SparseMultilayerEngine
        engine = SparseMultilayerEngine(layers=sample_layers)
        engine.remove_layer(0)
        assert engine.n_layers == 1
        assert len(engine.layers) == 1

    def test_remove_layer_invalid_index(self, sample_layers):
        from massive_core.numerics.multilayer_engine_sparse import SparseMultilayerEngine
        engine = SparseMultilayerEngine(layers=sample_layers)
        with pytest.raises(ValueError, match="out of range"):
            engine.remove_layer(5)

    def test_add_inter_layer_edge(self, sample_layers):
        from massive_core.numerics.multilayer_engine_sparse import SparseMultilayerEngine
        engine = SparseMultilayerEngine(layers=sample_layers)
        engine.add_inter_layer_edge(0, 0, 1, 0)
        assert engine.inter_layer_edges.shape[0] == 1

    def test_get_layer_states(self, sample_layers):
        from massive_core.numerics.multilayer_engine_sparse import SparseMultilayerEngine
        engine = SparseMultilayerEngine(
            layers=sample_layers,
            interaction_matrix=np.array([[1.0, 0.0], [0.0, 1.0]]),
        )
        states = engine.get_layer_states()
        assert len(states) == 2

    def test_metrics_history_structure(self, sample_layer):
        from massive_core.numerics.multilayer_engine_sparse import SparseMultilayerEngine
        engine = SparseMultilayerEngine(
            layers=[sample_layer],
            interaction_matrix=np.array([[1.0]]),
            max_iterations=3,
        )
        result = engine.run_simulation()
        for entry in result.metrics_history:
            assert "iteration" in entry


# ---------------------------------------------------------------------------
# SparseEnsembleKalmanFilter tests
# ---------------------------------------------------------------------------


class TestSparseEnsembleKalmanFilter:
    """Tests for the sparse EnKF."""

    @pytest.fixture
    def sparse_ekf(self):
        """Standard sparse EnKF fixture."""
        from massive_core.data_assimilation.kalman import SparseEnsembleKalmanFilter
        n_ensemble = 20
        n_state = 10
        n_obs = 5
        return SparseEnsembleKalmanFilter(
            n_ensemble=n_ensemble,
            n_state_dim=n_state,
            n_obs_dim=n_obs,
            observable_indices=list(range(n_obs)),
            observation_covariance=np.eye(n_obs) * 0.1,
            inflation=1.2,
        )

    def test_initialisation(self, sparse_ekf):
        assert sparse_ekf.n_ensemble == 20
        assert sparse_ekf.n_state_dim == 10
        assert sparse_ekf.n_obs_dim == 5

    def test_get_state_estimate(self, sparse_ekf):
        mean, cov = sparse_ekf.get_state_estimate()
        assert mean.shape == (10,)
        assert cov.shape == (10, 10)

    def test_predict(self, sparse_ekf):
        def identity(state: np.ndarray) -> np.ndarray:
            return state * 1.01
        sparse_ekf.predict(identity)
        # Ensemble should have shifted
        spread = sparse_ekf.get_ensemble_spread()
        assert spread >= 0

    def test_update(self, sparse_ekf):
        observations = np.random.randn(sparse_ekf.n_obs_dim)
        state = sparse_ekf.update(observations)
        assert state.shape == (10,)

    def test_assimilate_step(self, sparse_ekf):
        def model_fn(state: np.ndarray) -> np.ndarray:
            return state * 1.01
        observations = np.random.randn(sparse_ekf.n_obs_dim)
        state, ensemble = sparse_ekf.assimilate_step(model_fn, observations)
        assert state.shape == (10,)
        assert ensemble.shape == (20, 10)

    def test_get_ensemble(self, sparse_ekf):
        ens = sparse_ekf.get_ensemble()
        assert ens.shape == (20, 10)

    def test_ensemble_spread(self, sparse_ekf):
        spread = sparse_ekf.get_ensemble_spread()
        assert isinstance(spread, float)
        assert spread >= 0

    def test_set_ensemble(self, sparse_ekf):
        new_ensemble = np.random.randn(20, 10)
        sparse_ekf.set_ensemble(new_ensemble)
        assert np.allclose(sparse_ekf.get_ensemble(), new_ensemble)

    def test_set_ensemble_wrong_shape(self, sparse_ekf):
        with pytest.raises(ValueError, match="ensemble shape"):
            sparse_ekf.set_ensemble(np.random.randn(10, 5))


# ---------------------------------------------------------------------------
# Stability tests
# ---------------------------------------------------------------------------


class TestStabilityAnalyzer:
    """Tests for the stability analyzer."""

    @pytest.fixture
    def linear_stable_system(self):
        """dx/dt = -x → Jacobian = -1, stable."""
        return lambda x: -x * 0.1

    @pytest.fixture
    def stable_equilibrium(self):
        return np.array([1.0])

    @pytest.fixture
    def analyzer(self, linear_stable_system, stable_equilibrium):
        from massive_core.numerics.stability import SparseStabilityAnalyzer
        return SparseStabilityAnalyzer(
            system_fn=linear_stable_system,
            equilibrium=stable_equilibrium,
        )

    def test_jacobian_computation(self, analyzer):
        # SparseStabilityAnalyzer delegates to legacy StabilityAnalyzer
        jacobian = analyzer.compute_jacobian(np.array([1.0]))
        assert jacobian.shape == (1, 1)
        assert abs(jacobian[0, 0] - (-0.1)) < 0.01

    def test_stability_analysis_stable(self, analyzer):
        report = analyzer.analyze()
        assert report.stable is True
        assert report.max_real_eigenvalue < 0

    def test_get_stability_status(self, analyzer):
        status = analyzer.get_stability_status()
        assert "Stable" in status

    def test_scan_initial_conditions(self, analyzer):
        reports = analyzer.scan_initial_conditions(n_samples=3)
        assert len(reports) == 3
