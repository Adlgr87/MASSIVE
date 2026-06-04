"""Ensemble Kalman Filter for assimilating observations into simulations."""

from __future__ import annotations

from typing import Callable, Optional, Tuple

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


# ============================================================================
# Sparse Ensemble Kalman Filter (new)
# ============================================================================


class SparseEnsembleKalmanFilter:
    """EnKF variant that operates on a subset of observable state variables.

    Parameters
    ----------
    n_ensemble :
        Number of ensemble members.
    n_state_dim :
        Total state dimension (full state vector).
    n_obs_dim :
        Dimension of the *observable* sub-space.
    observable_indices :
        Integer indices into the full state vector that correspond to the
        observed variables.
    observation_covariance :
        Covariance of the *observable* sub-space errors.
    process_covariance :
        Full-state process covariance (used during predict).
    initial_ensemble :
        Full-state ensemble of shape *(n_ensemble, n_state_dim)*.
    inflation :
        Multiplicative inflation factor for ensemble spread.
    rng :
        Random generator.
    """

    def __init__(
        self,
        n_ensemble: int,
        n_state_dim: int,
        n_obs_dim: int,
        observable_indices: list[int],
        observation_covariance: np.ndarray,
        process_covariance: Optional[np.ndarray] = None,
        initial_ensemble: Optional[np.ndarray] = None,
        inflation: float = 1.0,
        rng: Optional[np.random.Generator] = None,
    ) -> None:
        self.n_ensemble = n_ensemble
        self.n_state_dim = n_state_dim
        self.n_obs_dim = n_obs_dim
        self.observable_indices = observable_indices
        self.observation_covariance = observation_covariance
        self.process_covariance = process_covariance or np.eye(n_state_dim)
        self.inflation = inflation
        self.rng = rng if rng is not None else np.random.default_rng()
        self.obs_noise = np.sqrt(np.diag(self.observation_covariance))

        if initial_ensemble is not None:
            if initial_ensemble.shape != (n_ensemble, n_state_dim):
                raise ValueError(
                    f"initial_ensemble shape must be ({n_ensemble}, {n_state_dim}), "
                    f"got {initial_ensemble.shape}"
                )
            self.ensemble = initial_ensemble.copy()
        else:
            self.ensemble = self.rng.standard_normal((n_ensemble, n_state_dim))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_observations(self) -> np.ndarray:
        """Extract observable sub-space from ensemble mean."""
        return self.ensemble.mean(axis=0)[self.observable_indices]

    def _get_observed_state(self, state: np.ndarray) -> np.ndarray:
        """Extract observable sub-space from a single state vector."""
        return state[self.observable_indices]

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------

    def get_state_estimate(self) -> Tuple[np.ndarray, np.ndarray]:
        """Return *(full_mean, full_covariance)*."""
        mean = self.ensemble.mean(axis=0)
        centered = self.ensemble - mean
        cov = (centered.T @ centered) / (self.n_ensemble - 1)
        return mean, cov

    # ------------------------------------------------------------------
    # Predict / update
    # ------------------------------------------------------------------

    def predict(self, model_fn, process_noise: Optional[np.ndarray] = None):
        """Advance the full ensemble through *model_fn*."""
        self.ensemble = np.array([model_fn(row) for row in self.ensemble])
        if process_noise is not None:
            noise = self.rng.multivariate_normal(
                np.zeros(self.n_state_dim),
                process_noise,
                size=self.n_ensemble,
            )
            self.ensemble += noise

    def update(self, observations: np.ndarray) -> np.ndarray:
        """Perform EnKF analysis on the observable sub-space.

        Parameters
        ----------
        observations :
            1-D array of observed values (shape *n_obs_dim*).

        Returns
        -------
        np.ndarray
            Updated *full* state estimate.
        """
        obs_indices = np.array(self.observable_indices)
        n_obs = len(obs_indices)

        mean = self.ensemble.mean(axis=0)
        ensemble_mean = np.tile(mean, (self.n_ensemble, 1))
        ensemble_devs = self.ensemble - ensemble_mean

        observable_devs = ensemble_devs[:, obs_indices]
        if self.inflation != 1.0:
            observable_devs *= self.inflation

        mean_obs = self._get_observations()
        obs_perturbed = observations + self.rng.normal(
            0.0, self.obs_noise[:n_obs], size=(self.n_ensemble, n_obs)
        )
        obs_devs = obs_perturbed - np.tile(mean_obs, (self.n_ensemble, 1))

        Nm1 = self.n_ensemble - 1
        cross_cov = observable_devs.T @ obs_devs / Nm1
        obs_cov = obs_devs.T @ obs_devs / Nm1

        try:
            inv_obs_cov = np.linalg.inv(
                obs_cov + self.observation_covariance[:n_obs, :n_obs]
            )
        except np.linalg.LinAlgError:
            inv_obs_cov = np.linalg.pinv(
                obs_cov + self.observation_covariance[:n_obs, :n_obs] + 1e-6 * np.eye(n_obs)
            )

        kalman_gain_obs = cross_cov @ inv_obs_cov

        for j in range(self.n_ensemble):
            obs_delta = kalman_gain_obs @ (obs_perturbed[j] - mean_obs)
            for idx, obs_idx in enumerate(obs_indices):
                self.ensemble[j, obs_idx] += obs_delta[idx]

        return mean

    def assimilate_step(self, model_fn, observations: np.ndarray,
                        process_noise: Optional[np.ndarray] = None) -> Tuple[np.ndarray, np.ndarray]:
        """Full predict-update cycle for sparse EnKF."""
        self.predict(model_fn, process_noise)
        state_estimate = self.update(observations)
        return state_estimate, self.ensemble.copy()

    def get_ensemble(self) -> np.ndarray:
        """Return a copy of the full ensemble."""
        return self.ensemble.copy()

    def set_ensemble(self, ensemble: np.ndarray) -> None:
        """Replace the current ensemble (validates shape)."""
        if ensemble.shape != (self.n_ensemble, self.n_state_dim):
            raise ValueError(
                f"ensemble shape must be ({self.n_ensemble}, {self.n_state_dim}), "
                f"got {ensemble.shape}"
            )
        self.ensemble = ensemble.copy()

    def get_ensemble_spread(self) -> float:
        """Return mean ensemble spread."""
        return float(np.std(self.ensemble, axis=0).mean())
