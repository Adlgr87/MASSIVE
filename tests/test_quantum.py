import numpy as np

from multilayer_engine import MultilayerEngine
from quantum.integration import (
    compress_agent_states,
    decompress_agent_states,
    quantum_optimize_interventions,
)
from quantum.quantum_optimizer import QISKIT_AVAILABLE, qaoa_optimize_interventions
from social_architect import find_optimal_interventions


def _dummy_eval(interventions: np.ndarray) -> float:
    return float(-np.sum(interventions ** 2) + 0.1 * np.sum(interventions))


def test_optimizer_returns_required_fields_classical():
    result = qaoa_optimize_interventions(_dummy_eval, n_agents=10, n_phases=3, force_classical=True)
    assert {"interventions", "score", "strategy", "qiskit_available"}.issubset(result.keys())


def test_optimizer_matrix_shape_matches_request():
    result = qaoa_optimize_interventions(_dummy_eval, n_agents=8, n_phases=4, force_classical=True)
    assert result["interventions"].shape == (4, 8)


def test_optimizer_force_classical_strategy_tag():
    result = qaoa_optimize_interventions(_dummy_eval, n_agents=6, n_phases=2, force_classical=True)
    assert result["strategy"] == "classical"


def test_optimizer_deterministic_for_same_seed():
    a = qaoa_optimize_interventions(_dummy_eval, n_agents=7, n_phases=3, force_classical=True, seed=123)
    b = qaoa_optimize_interventions(_dummy_eval, n_agents=7, n_phases=3, force_classical=True, seed=123)
    np.testing.assert_array_equal(a["interventions"], b["interventions"])
    assert a["score"] == b["score"]


def test_optimizer_rejects_invalid_shape_arguments():
    try:
        qaoa_optimize_interventions(_dummy_eval, n_agents=0, n_phases=1, force_classical=True)
        assert False, "Expected ValueError"
    except ValueError:
        assert True


def test_quantum_wrapper_returns_valid_score():
    result = quantum_optimize_interventions(_dummy_eval, n_agents=12, n_phases=2, max_iter=50)
    assert np.isfinite(result["score"])


def test_qiskit_optional_flag_consistent():
    result = qaoa_optimize_interventions(_dummy_eval, n_agents=5, n_phases=2)
    assert result["qiskit_available"] == QISKIT_AVAILABLE


def test_tensor_compression_roundtrip_shape():
    states = np.random.default_rng(42).normal(size=(120, 5))
    mps = compress_agent_states(states)
    restored = decompress_agent_states(mps)
    assert restored.shape == states.shape


def test_tensor_compression_reconstruction_quality_low_rank():
    rng = np.random.default_rng(0)
    base = rng.normal(size=(200, 2))
    projector = rng.normal(size=(2, 5))
    states = base @ projector
    mps = compress_agent_states(states, max_bond_dim=2)
    restored = decompress_agent_states(mps)
    error = float(np.mean(np.abs(states - restored)))
    assert error < 1e-6


def test_tensor_compression_ratio_is_reported():
    states = np.random.default_rng(1).normal(size=(64, 5))
    mps = compress_agent_states(states, max_bond_dim=3)
    assert "compression_ratio" in mps
    assert mps["compression_ratio"] > 0


def test_multilayer_engine_mps_helpers_for_large_population():
    engine = MultilayerEngine(N=1001, seed=3)
    candidate = np.random.default_rng(3).uniform(low=-1.0, high=1.0, size=(1001, 5))
    candidate[:, 1:] = np.clip(candidate[:, 1:], 0.0, 1.0)
    engine.update_opinions(candidate)
    recovered = engine.get_opinions()
    assert recovered.shape == (1001, 5)


def test_social_architect_drop_in_optimizer_available():
    result = find_optimal_interventions(_dummy_eval, n_agents=9, n_phases=3)
    assert "score" in result
    assert result["interventions"].shape == (3, 9)
