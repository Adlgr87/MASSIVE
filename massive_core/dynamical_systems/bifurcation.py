"""Bifurcation diagnostics for parameterized MASSIVE dynamics."""

from __future__ import annotations

from typing import Callable

import numpy as np

from massive_core.numerics.stability import StabilityAnalyzer

Array = np.ndarray
VectorFieldFactory = Callable[[float], Callable[[Array], Array]]


class BifurcationAnalyzer:
    """Detects stability changes across a scalar parameter range.

    Args:
        vector_field_factory: Callable that receives a parameter value and
            returns a vector field ``f(x)``.
        bounds: Optional clipping range for fixed-point iteration.
    """

    def __init__(
        self,
        vector_field_factory: VectorFieldFactory,
        bounds: tuple[float, float] | None = None,
    ) -> None:
        self.vector_field_factory = vector_field_factory
        self.bounds = bounds
        self.stability = StabilityAnalyzer()

    def detect_bifurcation_diagram(
        self,
        param_range: Array,
        x0: Array,
        n_steps: int = 1000,
        dt: float = 0.01,
        tolerance: float = 1e-6,
    ) -> dict[str, Array | list[dict[str, object]]]:
        """Build a fixed-point and stability diagram over parameters.

        Args:
            param_range: One-dimensional parameter values.
            x0: Initial state for continuation.
            n_steps: Relaxation steps per parameter.
            dt: Relaxation time step.
            tolerance: Real-eigenvalue tolerance for classifying stability.

        Returns:
            Dictionary with fixed points, stability labels and detected changes.
        """

        params = np.asarray(param_range, dtype=float).reshape(-1)
        current = np.asarray(x0, dtype=float)
        fixed_points = []
        stable_flags = []
        max_real_eigenvalues = []
        bifurcation_points: list[dict[str, object]] = []
        previous_stable: bool | None = None

        for param in params:
            field = self.vector_field_factory(float(param))
            current = self._relax_to_fixed_point(field, current, n_steps, dt)
            report = self.stability.analyze_linear_stability(current, field, tolerance)
            stable = bool(report.stable)
            fixed_points.append(current.copy())
            stable_flags.append(stable)
            max_real_eigenvalues.append(report.max_real_eigenvalue)

            if previous_stable is not None and stable != previous_stable:
                bifurcation_points.append(
                    {
                        "type": "stability_change",
                        "parameter": float(param),
                        "position": current.copy(),
                        "max_real_eigenvalue": report.max_real_eigenvalue,
                    }
                )
            previous_stable = stable

        return {
            "parameter_range": params,
            "fixed_points": np.asarray(fixed_points),
            "stable": np.asarray(stable_flags, dtype=bool),
            "max_real_eigenvalues": np.asarray(max_real_eigenvalues, dtype=float),
            "bifurcation_points": bifurcation_points,
        }

    def compute_tipping_point_probability(
        self,
        potential: Array,
        noise_amplitude: float,
        barrier_index: int | None = None,
    ) -> float:
        """Estimate transition probability with a Kramers-style factor.

        Args:
            potential: One-dimensional potential landscape samples.
            noise_amplitude: Positive Langevin noise amplitude.
            barrier_index: Optional index for the barrier sample. If omitted,
                the maximum potential value is used.

        Returns:
            Probability-like transition factor in ``[0, 1]``.
        """

        if noise_amplitude <= 0.0:
            raise ValueError("noise_amplitude must be positive")
        landscape = np.asarray(potential, dtype=float).reshape(-1)
        if landscape.size == 0:
            raise ValueError("potential cannot be empty")
        barrier = landscape[barrier_index] if barrier_index is not None else np.max(landscape)
        well = np.min(landscape)
        barrier_height = max(float(barrier - well), 0.0)
        diffusivity = noise_amplitude**2
        return float(np.clip(np.exp(-barrier_height / diffusivity), 0.0, 1.0))

    def _relax_to_fixed_point(
        self,
        field: Callable[[Array], Array],
        x0: Array,
        n_steps: int,
        dt: float,
    ) -> Array:
        state = np.asarray(x0, dtype=float).copy()
        for _ in range(n_steps):
            update = dt * np.asarray(field(state), dtype=float)
            state = state + update
            if self.bounds is not None:
                state = np.clip(state, self.bounds[0], self.bounds[1])
            if np.linalg.norm(update) < 1e-10:
                break
        return state
