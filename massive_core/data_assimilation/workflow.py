"""Observation-assimilation workflows for MASSIVE histories."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from massive_core.data_assimilation.kalman import EnsembleKalmanFilter
from massive_core.diagnostics import trajectory_from_history

Array = np.ndarray
ObservationInput = Mapping[int, Array | float] | Sequence[tuple[int, Array | float]]


@dataclass(frozen=True)
class AssimilationResult:
    """Serializable result of assimilating observations into a trajectory.

    Args:
        assimilated_mean: Analysis mean for each time step.
        assimilated_std: Analysis standard deviation for each time step.
        observation_steps: Sorted steps where observations were applied.
    """

    assimilated_mean: Array
    assimilated_std: Array
    observation_steps: list[int]

    def to_dict(self) -> dict[str, Any]:
        """Convert result arrays to JSON-friendly lists.

        Returns:
            Serializable assimilation payload.
        """

        return {
            "assimilated_mean": self.assimilated_mean.tolist(),
            "assimilated_std": self.assimilated_std.tolist(),
            "observation_steps": self.observation_steps,
        }


def assimilate_history_observations(
    history: Sequence[Any],
    observations: ObservationInput,
    fields: Sequence[str] | None = None,
    H: Array | None = None,
    observation_variance: float = 0.01,
    n_ensemble: int = 50,
    ensemble_spread: float = 0.01,
    seed: int | None = None,
) -> AssimilationResult:
    """Assimilate sparse observations into a MASSIVE trajectory with EnKF.

    The simulated trajectory supplies the model forecast increments.  At each
    observed step, the EnKF updates the ensemble with the provided observation.
    This is a post-processing workflow: it does not mutate the original history.

    Args:
        history: Legacy dict history or array snapshots.
        observations: Mapping or sequence of ``(step, observation)`` pairs.
        fields: Optional fields for dict histories.
        H: Observation operator. Defaults to observing the first state dimension.
        observation_variance: Positive scalar variance used for ``R``.
        n_ensemble: Number of ensemble members.
        ensemble_spread: Initial ensemble spread around the simulated initial state.
        seed: Optional random seed.

    Returns:
        Assimilation result with per-step means/stds.
    """

    if observation_variance <= 0.0:
        raise ValueError("observation_variance must be positive")
    if ensemble_spread < 0.0:
        raise ValueError("ensemble_spread must be non-negative")

    trajectory = trajectory_from_history(history, fields)
    if trajectory.shape[0] < 2:
        raise ValueError("history needs at least two time points")

    obs_by_step = _normalize_observations(observations)
    state_dim = trajectory.shape[1]
    first_obs = next(iter(obs_by_step.values()), np.array([trajectory[0, 0]], dtype=float))
    obs_dim = int(np.asarray(first_obs, dtype=float).reshape(-1).size)
    H_mat = np.asarray(H, dtype=float) if H is not None else np.eye(obs_dim, state_dim)
    if H_mat.shape != (obs_dim, state_dim):
        raise ValueError("H must have shape (n_observations, state_dim)")

    rng = np.random.default_rng(seed)
    initial_ensemble = trajectory[0] + rng.normal(0.0, ensemble_spread, size=(n_ensemble, state_dim))
    enkf = EnsembleKalmanFilter(
        n_ensemble=n_ensemble,
        n_state_dim=state_dim,
        observation_covariance=np.eye(obs_dim) * observation_variance,
        initial_ensemble=initial_ensemble,
        rng=rng,
    )

    means = []
    stds = []
    mean, std = enkf.get_state_estimate()
    means.append(mean.copy())
    stds.append(std.copy())

    for step in range(1, trajectory.shape[0]):
        increment = trajectory[step] - trajectory[step - 1]
        enkf.predict(lambda member, inc=increment: member + inc)
        if step in obs_by_step:
            enkf.update(obs_by_step[step], H=H_mat)
        mean, std = enkf.get_state_estimate()
        means.append(mean.copy())
        stds.append(std.copy())

    return AssimilationResult(
        assimilated_mean=np.asarray(means),
        assimilated_std=np.asarray(stds),
        observation_steps=sorted(obs_by_step),
    )


def _normalize_observations(observations: ObservationInput) -> dict[int, Array]:
    items = observations.items() if isinstance(observations, Mapping) else observations
    normalized: dict[int, Array] = {}
    for step, value in items:
        step_index = int(step)
        if step_index < 0:
            raise ValueError("observation steps must be non-negative")
        normalized[step_index] = np.asarray(value, dtype=float).reshape(-1)
    return normalized
