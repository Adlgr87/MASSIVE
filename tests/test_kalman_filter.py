"""Dedicated unit tests for SparseEnsembleKalmanFilter and EnsembleKalmanFilter.

Located at tests/test_kalman_filter.py for CI discoverability.
"""

import numpy as np
import pytest

from massive_core.data_assimilation.kalman import (
    EnsembleKalmanFilter,
    SparseEnsembleKalmanFilter,
)


def test_standard_enkf_update_converges():
    rng = np.random.default_rng(42)
    true_state = np.array([1.0, 2.0, 3.0])
    initial = true_state + rng.normal(0, 0.5, size=(50, 3))
    enkf = EnsembleKalmanFilter(
        n_ensemble=50,
        n_state_dim=3,
        observation_covariance=np.eye(3) * 0.01,
        initial_ensemble=initial,
        rng=rng,
    )

    # Identity model (no drift) so the update should pull ensemble toward obs
    def model_step(x):
        return x.copy()

    enkf.predict(model_step)
    obs = true_state.copy()
    enkf.update(obs)
    mean, std = enkf.get_state_estimate()
    assert mean.shape == (3,)
    # After update with observation at true_state, mean should be close to true
    assert np.linalg.norm(mean - true_state) < 0.5


def test_sparse_enkf_assimilate_step_roundtrip():
    rng = np.random.default_rng(7)
    n_ens, n_state = 40, 6
    obs_idx = [0, 2, 4]
    R = np.eye(3) * 0.05

    enkf = SparseEnsembleKalmanFilter(
        n_ensemble=n_ens,
        n_state_dim=n_state,
        n_obs_dim=3,
        observable_indices=obs_idx,
        observation_covariance=R,
        rng=rng,
    )

    def model_fn(x):
        x = x.copy()
        x[0] += 0.1
        return x

    obs = np.array([0.0, 0.0, 0.0])
    before_mean = enkf.ensemble[:, obs_idx].mean(axis=0)
    state_est, ens_copy = enkf.assimilate_step(model_fn, obs)

    assert state_est.shape == (n_state,)
    assert ens_copy.shape == (n_ens, n_state)
    # Observable indices should have moved toward observations
    after_mean = enkf.ensemble[:, obs_idx].mean(axis=0)
    assert np.linalg.norm(after_mean - obs) < np.linalg.norm(before_mean - obs)


def test_sparse_enkf_rejects_bad_shapes():
    with pytest.raises(ValueError, match="initial_ensemble shape"):
        SparseEnsembleKalmanFilter(
            n_ensemble=10,
            n_state_dim=5,
            n_obs_dim=2,
            observable_indices=[0, 1],
            observation_covariance=np.eye(2) * 0.1,
            initial_ensemble=np.zeros((20, 5)),
        )


def test_standard_enkf_rejects_n_ensemble_below_2():
    with pytest.raises(ValueError, match="n_ensemble must be at least 2"):
        EnsembleKalmanFilter(n_ensemble=1, n_state_dim=3)


def test_sparse_enkf_get_set_ensemble():
    rng = np.random.default_rng(99)
    enkf = SparseEnsembleKalmanFilter(
        n_ensemble=10,
        n_state_dim=4,
        n_obs_dim=2,
        observable_indices=[0, 1],
        observation_covariance=np.eye(2) * 0.1,
        rng=rng,
    )
    ens = enkf.get_ensemble()
    assert ens.shape == (10, 4)
    new_ens = np.ones((10, 4))
    enkf.set_ensemble(new_ens)
    assert np.allclose(enkf.ensemble, 1.0)


def test_sparse_enkf_predict_with_process_noise():
    rng = np.random.default_rng(123)
    enkf = SparseEnsembleKalmanFilter(
        n_ensemble=20,
        n_state_dim=3,
        n_obs_dim=1,
        observable_indices=[0],
        observation_covariance=np.eye(1) * 0.1,
        rng=rng,
    )
    before = enkf.ensemble.copy()
    noise_cov = np.eye(3) * 0.01
    enkf.predict(lambda x: x.copy(), process_noise=noise_cov)
    after = enkf.ensemble
    assert not np.allclose(before, after)


def test_enkf_h_get_shape_validation():
    enkf = EnsembleKalmanFilter(n_ensemble=30, n_state_dim=4, rng=np.random.default_rng(1))
    bad_H = np.zeros((2, 3))
    with pytest.raises(ValueError, match="H must have shape"):
        enkf.update(np.array([0.5, 0.5]), H=bad_H)


def test_sparse_enkf_get_state_estimate_returns_full_covariance():
    rng = np.random.default_rng(77)
    enkf = SparseEnsembleKalmanFilter(
        n_ensemble=25,
        n_state_dim=5,
        n_obs_dim=2,
        observable_indices=[1, 3],
        observation_covariance=np.eye(2) * 0.1,
        rng=rng,
    )
    mean, cov = enkf.get_state_estimate()
    assert mean.shape == (5,)
    assert cov.shape == (5, 5)


def test_sparse_enkf_get_ensemble_spread():
    rng = np.random.default_rng(88)
    enkf = SparseEnsembleKalmanFilter(
        n_ensemble=15,
        n_state_dim=3,
        n_obs_dim=1,
        observable_indices=[0],
        observation_covariance=np.eye(1) * 0.1,
        rng=rng,
    )
    spread = enkf.get_ensemble_spread()
    assert isinstance(spread, float)
    assert spread > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
