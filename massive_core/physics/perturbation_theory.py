"""Perturbation-theory helpers for weakly coupled MASSIVE dynamics."""

from __future__ import annotations

from typing import Callable

import numpy as np

Array = np.ndarray


class PerturbationTheorySolver:
    """Computes low-order perturbative trajectories.

    Args:
        dt: Positive integration step.
        n_steps: Number of integration steps.
        bounds: Optional clipping range for bounded states.
    """

    def __init__(self, dt: float = 0.01, n_steps: int = 100, bounds: tuple[float, float] | None = None) -> None:
        if dt <= 0.0:
            raise ValueError("dt must be positive")
        if n_steps < 1:
            raise ValueError("n_steps must be positive")
        self.dt = dt
        self.n_steps = n_steps
        self.bounds = bounds

    def compute_perturbation_expansion(
        self,
        x0: Array,
        base_system: Callable[[Array], Array],
        perturbation: Callable[[Array], Array],
        epsilon: float,
        order: int = 2,
    ) -> Array:
        """Integrate ``dx/dt = f0(x) + epsilon f1(x)`` to low order.

        Args:
            x0: Initial state.
            base_system: Unperturbed vector field.
            perturbation: Perturbing vector field.
            epsilon: Perturbation strength.
            order: 0, 1 or 2. Order 2 includes an Euler approximation to the
                full weakly perturbed system.

        Returns:
            Trajectory with shape ``(n_steps + 1, *x0.shape)``.
        """

        if order not in (0, 1, 2):
            raise ValueError("order must be 0, 1 or 2")
        state = np.asarray(x0, dtype=float).copy()
        trajectory = [state.copy()]
        strength = 0.0 if order == 0 else epsilon
        for _ in range(self.n_steps):
            drift = np.asarray(base_system(state), dtype=float)
            if order >= 1:
                drift = drift + strength * np.asarray(perturbation(state), dtype=float)
            if order >= 2:
                drift = drift + 0.5 * (strength**2) * self._directional_correction(state, perturbation)
            state = state + self.dt * drift
            if self.bounds is not None:
                state = np.clip(state, self.bounds[0], self.bounds[1])
            trajectory.append(state.copy())
        return np.asarray(trajectory)

    def compute_green_function(self, operator: Array, source: Array, regularization: float = 1e-2) -> Array:
        """Solve a regularized linear response problem.

        Args:
            operator: Square linear operator.
            source: Source vector or matrix.
            regularization: Positive diagonal shift.

        Returns:
            Response ``(operator + regularization I)^-1 source``.
        """

        mat = np.asarray(operator, dtype=float)
        if mat.ndim != 2 or mat.shape[0] != mat.shape[1]:
            raise ValueError("operator must be square")
        shifted = mat + regularization * np.eye(mat.shape[0])
        return np.linalg.solve(shifted, np.asarray(source, dtype=float))

    def _directional_correction(self, state: Array, perturbation: Callable[[Array], Array]) -> Array:
        eps = 1e-6
        direction = np.asarray(perturbation(state), dtype=float)
        norm = np.linalg.norm(direction)
        if norm == 0.0:
            return np.zeros_like(state, dtype=float)
        unit = direction / norm
        return (np.asarray(perturbation(state + eps * unit), dtype=float) - direction) / eps
