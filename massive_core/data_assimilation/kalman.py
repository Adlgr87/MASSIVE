"""Ensemble Kalman Filter for assimilating observations into simulations."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

Array = np.ndarray


def _gaspari_cohn_matrix(n: int, radius: float) -> Array:
    """Gaspari-Cohn (1999) 5th-order piecewise-rational correlation taper.

    Returns an ``(n, n)`` matrix whose entry ``(i, j)`` decays smoothly from 1
    at ``|i-j| = 0`` to exactly 0 at ``|i-j| >= 2·radius``. Unlike a hard
    cut-off, this function is positive-definite, so the tapered covariance
    remains a valid covariance matrix.
    """
    idx = np.arange(n)
    dist = np.abs(idx[:, None] - idx[None, :]) / float(radius)
    taper = np.zeros_like(dist)

    near = dist <= 1.0
    d = dist[near]
    taper[near] = 1.0 - (5.0 / 3.0) * d**2 + (5.0 / 8.0) * d**3 + 0.5 * d**4 - 0.25 * d**5

    far = (dist > 1.0) & (dist < 2.0)
    d = dist[far]
    taper[far] = (
        4.0
        - 5.0 * d
        + (5.0 / 3.0) * d**2
        + (5.0 / 8.0) * d**3
        - 0.5 * d**4
        + (1.0 / 12.0) * d**5
        - (2.0 / 3.0) / d
    )
    return np.clip(taper, 0.0, 1.0)


class EnsembleKalmanFilter:
    """Small Ensemble Kalman Filter with dimensionally correct covariance.

    Args:
        n_ensemble: Number of ensemble members.
        n_state_dim: State dimension for each ensemble member.
        observation_covariance: Optional observation covariance ``R``.
        initial_ensemble: Optional initial ensemble with shape
            ``(n_ensemble, n_state_dim)``.
        rng: Optional NumPy random generator.
        seed: Seed used when ``rng`` is not supplied. Defaults to
            ``DEFAULT_ENKF_SEED`` so runs are reproducible; pass ``None``
            explicitly for nondeterministic behaviour.
        inflation: Multiplicative covariance inflation factor applied to the
            ensemble anomalies before the analysis. Finite ensembles
            systematically under-estimate the forecast spread, and the filter
            then over-trusts its own prior and diverges from the observations
            ("filter divergence"). Typical operational range is 1.0–1.1;
            ``1.0`` disables inflation.
        localization_radius: Radius (in state-index units) of the Gaspari-Cohn
            taper applied to the state covariance. With a small ensemble the
            sample covariance between distant state components is mostly noise;
            tapering removes those spurious long-range correlations. ``None``
            disables localization.
    """

    #: Default seed — a data-assimilation filter whose RNG is unseeded makes
    #: every simulation that uses it irreproducible.
    DEFAULT_ENKF_SEED = 20240101

    def __init__(
        self,
        n_ensemble: int = 100,
        n_state_dim: int = 5,
        observation_covariance: Array | None = None,
        initial_ensemble: Array | None = None,
        rng: np.random.Generator | None = None,
        seed: int | None = DEFAULT_ENKF_SEED,
        inflation: float = 1.02,
        localization_radius: float | None = None,
    ) -> None:
        if n_ensemble < 2:
            raise ValueError("n_ensemble must be at least 2")
        if n_state_dim < 1:
            raise ValueError("n_state_dim must be positive")
        if inflation < 1.0:
            raise ValueError("inflation must be >= 1.0")
        if localization_radius is not None and localization_radius <= 0:
            raise ValueError("localization_radius must be positive or None")

        self.n_ensemble = n_ensemble
        self.n_state_dim = n_state_dim
        self.inflation = float(inflation)
        self.localization_radius = localization_radius
        self.rng = rng if rng is not None else np.random.default_rng(seed)
        self._localization_matrix = (
            _gaspari_cohn_matrix(n_state_dim, localization_radius)
            if localization_radius is not None
            else None
        )
        if initial_ensemble is None:
            self.ensemble = self.rng.normal(0.0, 1.0, size=(n_ensemble, n_state_dim))
        else:
            ensemble = np.asarray(initial_ensemble, dtype=float)
            if ensemble.shape != (n_ensemble, n_state_dim):
                raise ValueError("initial_ensemble has incompatible shape")
            self.ensemble = ensemble.copy()
        self.R = (
            np.asarray(observation_covariance, dtype=float)
            if observation_covariance is not None
            else np.eye(n_state_dim) * 0.1
        )

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
        H_mat = np.eye(y.size, self.n_state_dim) if H is None else np.asarray(H, dtype=float)
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

        # Multiplicative covariance inflation — counteracts the systematic
        # under-dispersion of a finite ensemble, which otherwise causes the
        # filter to ignore observations and diverge.
        if self.inflation != 1.0:
            anomalies = anomalies * self.inflation
            self.ensemble = x_mean + anomalies

        state_covariance = (anomalies.T @ anomalies) / (self.n_ensemble - 1)

        # Covariance localization — tapers spurious long-range sample
        # correlations that a small ensemble cannot resolve.
        if self._localization_matrix is not None:
            state_covariance = state_covariance * self._localization_matrix

        innovation_covariance = H_mat @ state_covariance @ H_mat.T + R
        kalman_gain = state_covariance @ H_mat.T @ np.linalg.pinv(innovation_covariance)

        # Vectorised stochastic (perturbed-observation) analysis: one
        # multivariate draw for the whole ensemble instead of a Python loop
        # re-factorising R on every member.
        perturbations = self.rng.multivariate_normal(
            np.zeros(y.size), R, size=self.n_ensemble
        )
        innovations = (y + perturbations) - self.ensemble @ H_mat.T
        self.ensemble = self.ensemble + innovations @ kalman_gain.T
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
        process_covariance: np.ndarray | None = None,
        initial_ensemble: np.ndarray | None = None,
        inflation: float = 1.0,
        rng: np.random.Generator | None = None,
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

    def get_state_estimate(self) -> tuple[np.ndarray, np.ndarray]:
        """Return *(full_mean, full_covariance)*."""
        mean = self.ensemble.mean(axis=0)
        centered = self.ensemble - mean
        cov = (centered.T @ centered) / (self.n_ensemble - 1)
        return mean, cov

    # ------------------------------------------------------------------
    # Predict / update
    # ------------------------------------------------------------------

    def predict(
        self,
        model_fn: Callable[[Array], Array],
        process_noise: np.ndarray | None = None,
    ) -> Array:
        """Advance the full ensemble through *model_fn*.

        Args:
            model_fn: Maps one full state vector to the next.
            process_noise: Optional process-noise covariance for additive noise.

        Returns:
            Updated ensemble array of shape ``(n_ensemble, n_state_dim)``.
        """
        self.ensemble = np.array([model_fn(row) for row in self.ensemble])
        if process_noise is not None:
            noise = self.rng.multivariate_normal(
                np.zeros(self.n_state_dim),
                process_noise,
                size=self.n_ensemble,
            )
            self.ensemble += noise
        return self.ensemble

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
            inv_obs_cov = np.linalg.inv(obs_cov + self.observation_covariance[:n_obs, :n_obs])
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

    def assimilate_step(
        self,
        model_fn: Callable[[Array], Array],
        observations: np.ndarray,
        process_noise: np.ndarray | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Full predict-update cycle for sparse EnKF.

        Args:
            model_fn: Maps one full state vector to the next.
            observations: Observation vector of length ``n_obs_dim``.
            process_noise: Optional process-noise covariance for the predict step.

        Returns:
            Tuple ``(state_estimate, ensemble_copy)``.
        """
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
