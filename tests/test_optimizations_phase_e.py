"""Regression tests for the Phase E optimisation work."""

from __future__ import annotations

import numpy as np
import pytest

import energy_engine as E
from energy_engine import DENSE_ADJACENCY_CAP, random_network
from massive_core.rust_core import langevin_opinion_update_inplace


def _legacy_random_network(n, connectivity=0.3, seed=42):
    """The pre-optimisation implementation, kept as the reference oracle."""
    rng = np.random.default_rng(seed)
    upper = rng.random((n, n))
    mask = (upper < connectivity).astype(float)
    adj = np.triu(mask, k=1)
    adj = adj + adj.T
    np.fill_diagonal(adj, 0.0)
    return adj


class TestRandomNetworkBlockGeneration:
    """A-08: blocked generation must not change a single bit of the output."""

    @pytest.mark.parametrize("n", [2, 3, 10, 257, 1024, 1500])
    @pytest.mark.parametrize("connectivity", [0.0, 0.3, 1.0])
    def test_matches_legacy_exactly(self, n, connectivity):
        np.testing.assert_array_equal(
            random_network(n, connectivity, 42),
            _legacy_random_network(n, connectivity, 42),
        )

    @pytest.mark.parametrize("block_rows", [1, 7, 1024])
    def test_result_is_independent_of_block_size(self, block_rows, monkeypatch):
        monkeypatch.setattr(E, "_ADJACENCY_BLOCK_ROWS", block_rows)
        np.testing.assert_array_equal(
            random_network(300, 0.3, 7), _legacy_random_network(300, 0.3, 7)
        )

    def test_symmetric_with_zero_diagonal(self):
        adj = random_network(128, 0.25, 3)
        np.testing.assert_array_equal(adj, adj.T)
        assert adj.diagonal().sum() == 0.0

    def test_same_seed_same_network(self):
        np.testing.assert_array_equal(random_network(64, 0.3, 11), random_network(64, 0.3, 11))

    def test_cap_error_reports_the_real_memory_cost(self):
        with pytest.raises(ValueError, match="GB"):
            random_network(DENSE_ADJACENCY_CAP + 1)


class TestInPlaceUpdateFailsLoudly:
    """A-12: a silently-discarded in-place update is worse than an error."""

    def test_float64_array_is_mutated(self):
        agents = np.zeros((4, 2), dtype=np.float64)
        agents[:, 0] = 0.5
        langevin_opinion_update_inplace(
            agents, np.ones(4), np.zeros(4), np.zeros(4), 0.1, 0.0
        )
        assert np.allclose(agents[:, 0], 0.6)

    @pytest.mark.parametrize("dtype", [np.float32, np.int64])
    def test_wrong_dtype_raises_instead_of_silently_copying(self, dtype):
        agents = np.zeros((4, 2), dtype=dtype)
        with pytest.raises(TypeError, match="float64"):
            langevin_opinion_update_inplace(
                agents, np.ones(4), np.zeros(4), np.zeros(4), 0.1, 0.0
            )

    def test_non_array_raises(self):
        with pytest.raises(TypeError, match="ndarray"):
            langevin_opinion_update_inplace(
                [[0.5, 0.0]], np.ones(1), np.zeros(1), np.zeros(1), 0.1, 0.0
            )

    def test_readonly_array_raises(self):
        agents = np.zeros((4, 2), dtype=np.float64)
        agents.flags.writeable = False
        with pytest.raises(TypeError, match="writable"):
            langevin_opinion_update_inplace(
                agents, np.ones(4), np.zeros(4), np.zeros(4), 0.1, 0.0
            )


class TestCfCStatusIsObservable:
    """A-14: the rule-based fallback must not be silent."""

    def test_engine_exposes_which_modulators_loaded(self):
        engine = E.SocialEnergyEngine()
        assert set(engine.cfc_status) == {
            "torch_available",
            "temperature_model",
            "lambda_model",
            "landscape_model",
        }
        assert all(isinstance(v, bool) for v in engine.cfc_status.values())
