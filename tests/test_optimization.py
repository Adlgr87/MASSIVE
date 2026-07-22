import numpy as np
import pytest

from massive.core.intervention_optimizer import optimize_interventions
from multilayer_engine import MultilayerEngine
from social_architect import find_optimal_interventions
from state_compression import compress_agent_states, decompress_agent_states


def _dummy_objective_function(interventions: np.ndarray) -> float:
    return float(-np.sum(interventions ** 2) + 0.1 * np.sum(interventions))


def test_optimizer_returns_required_fields():
    result = optimize_interventions(_dummy_objective_function, n_agents=10, n_phases=3, max_iter=40)
    assert {"interventions", "score", "strategy"}.issubset(result.keys())


def test_optimizer_matrix_shape_matches_request():
    result = optimize_interventions(_dummy_objective_function, n_agents=8, n_phases=4, max_iter=40)
    assert result["interventions"].shape == (4, 8)


def test_optimizer_strategy_tag():
    result = optimize_interventions(_dummy_objective_function, n_agents=6, n_phases=2, max_iter=20)
    assert result["strategy"] == "multiobjective_stochastic_search"
    assert "feasible" in result
    assert "effectiveness" in result


def test_optimizer_fiscal_does_not_only_shrink_iterations():
    """Fiscal/cost constraints must report density budget, not only mutate max_iter."""
    result = optimize_interventions(
        _dummy_objective_function,
        n_agents=10,
        n_phases=3,
        max_iter=30,
        seed=1,
        fiscal_constraint=0.2,
        cost_scale_factor=2.0,
    )
    assert 0.0 < result["max_density"] <= 1.0
    assert result["feasibility"] == 0.2
    # Interventions should be sparser than fully dense ±1 matrix.
    density = float(np.mean(np.abs(result["interventions"]) > 0))
    assert density <= result["max_density"] + 1e-9


def test_optimizer_deterministic_for_same_seed():
    a = optimize_interventions(_dummy_objective_function, n_agents=7, n_phases=3, max_iter=50, seed=123)
    b = optimize_interventions(_dummy_objective_function, n_agents=7, n_phases=3, max_iter=50, seed=123)
    np.testing.assert_array_equal(a["interventions"], b["interventions"])
    assert a["score"] == b["score"]


def test_optimizer_rejects_invalid_shape_arguments():
    with pytest.raises(ValueError):
        optimize_interventions(_dummy_objective_function, n_agents=0, n_phases=1)


def test_wrapper_returns_valid_score():
    result = find_optimal_interventions(_dummy_objective_function, n_agents=12, n_phases=2, max_iter=50)
    assert np.isfinite(result["score"])


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
