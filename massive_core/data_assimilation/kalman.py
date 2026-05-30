"""Ensemble Kalman Filter for assimilating observations into simulations."""

from __future__ import annotations

from typing import Callable

import numpy as np

Array = np.ndarray


class EnsembleKalmanFilter:
    """Small Ensemble Kalman Filter with dimensionally correct covariance.

    Args:
        n_ensemble: Number of ensemble members.
        n_state_dim: State dimension for each ensemble member.
        observation_covariance: Optional observation covariance ``R``.
        initial_ensemble: Optional initial ensemble with shape
            ``(n_ensemble, n_state_dim)``.
        rng: Optional NumPy random generator.
    """

    def __init__(
        self,
        n_ensemble: int = 100,
        n_state_dim: int = 5,
        observation_covariance: Array | None = None,
        initial_ensemble: Array | None = None,
        rng: np.random.Generator | None = None,
    ) -> None:
        if n_ensemble < 2:
            raise ValueError("n_ensemble must be at least 2")
        if n_state_dim < 1:
            raise ValueError("n_state_dim must be positive")

        self.n_ensemble = n_ensemble
        self.n_state_dim = n_state_dim
        self.rng = rng or np.random.default_rng()
        if initial_ensemble is None:
            self.ensemble = self.rng.normal(0.0, 1.0, size=(n_ensemble, n_state_dim))
        else:
            ensemble = np.asarray(initial_ensemble, dtype=float)
            if ensemble.shape != (n_ensemble, n_state_dim):
                raise ValueError("initial_ensemble has incompatible shape")
            self.ensemble = ensemble.copy()
        self.R = np.asarray(observation_covariance, dtype=float) if observation_covariance is not None else np.eye(n_state_dim) * 0.1

    def predict(self, model_step: Callable[[Array], Array], dt: float | None = None) -> Array:
        """Propagate every ensemble member through the model.

        Args:
            model_step: Callable receiving one state vector. If it accepts a
                ``dt`` keyword, pass ``dt`` by wrapping it at call site.
            dt: Kept for API clarity; not used directly.

        Returns:
            Updated ensemble.
        """

        del dt
        for i in range(self.n_ensemble):
            self.ensemble[i] = np.asarray(model_step(self.ensemble[i]), dtype=float)
        return self.ensemble

    def update(self, observations: Array, H: Array | None = None) -> Array:
        """Correct the ensemble using observations.

        Args:
            observations: Observation vector.
            H: Observation operator with shape ``(n_obs, n_state_dim)``.

        Returns:
            Analysis ensemble after the Kalman update.
        """

        y = np.asarray(observations, dtype=float).reshape(-1)
        if H is None:
            H_mat = np.eye(y.size, self.n_state_dim)
        else:
            H_mat = np.asarray(H, dtype=float)
        if H_mat.shape != (y.size, self.n_state_dim):
            raise ValueError("H must have shape (n_observations, n_state_dim)")
        if self.R.shape != (y.size, y.size):
            if self.R.shape == (self.n_state_dim, self.n_state_dim) and y.size <= self.n_state_dim:
                R = self.R[: y.size, : y.size]
            else:
                raise ValueError("observation covariance has incompatible shape")
        else:
            R = self.R

        x_mean = np.mean(self.ensemble, axis=0)
        anomalies = self.ensemble - x_mean
        state_covariance = (anomalies.T @ anomalies) / (self.n_ensemble - 1)
        innovation_covariance = H_mat @ state_covariance @ H_mat.T + R
        kalman_gain = state_covariance @ H_mat.T @ np.linalg.pinv(innovation_covariance)

        for i in range(self.n_ensemble):
            perturbed_obs = y + self.rng.multivariate_normal(np.zeros(y.size), R)
            innovation = perturbed_obs - H_mat @ self.ensemble[i]
            self.ensemble[i] = self.ensemble[i] + kalman_gain @ innovation
        return self.ensemble

    def get_state_estimate(self) -> tuple[Array, Array]:
        """Return ensemble mean and standard deviation.

        Returns:
            Tuple ``(mean, std)`` over ensemble members.
        """

        return np.mean(self.ensemble, axis=0), np.std(self.ensemble, axis=0)
