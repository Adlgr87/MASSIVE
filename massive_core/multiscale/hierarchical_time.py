"""Hierarchical time-scale dynamics for MASSIVE states."""

from __future__ import annotations

from typing import Callable

import numpy as np

Array = np.ndarray


class MultiTimescaleEngine:
    """Superposes micro, meso and macro Langevin-like components.

    Args:
        timescales: Mapping from scale name to ``tau`` and ``amplitude``.
        bounds: Optional clipping range for bounded opinions.
        rng: Optional random generator for reproducible noise.
    """

    def __init__(
        self,
        timescales: dict[str, dict[str, float]] | None = None,
        bounds: tuple[float, float] | None = None,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.timescales = timescales or {
            "micro": {"tau": 0.01, "amplitude": 0.1},
            "meso": {"tau": 1.0, "amplitude": 0.3},
            "macro": {"tau": 10.0, "amplitude": 0.5},
        }
        for name, params in self.timescales.items():
            if params["tau"] <= 0.0:
                raise ValueError(f"tau for {name} must be positive")
        self.bounds = bounds
        self.rng = rng or np.random.default_rng()
        self.state: dict[str, Array] = {}

    def step(
        self,
        x: Array,
        dt: float,
        drift: Callable[[Array], Array],
        social_force: Callable[[Array], Array] | Array | None = None,
    ) -> Array:
        """Advance a state with coupled time-scale components.

        Args:
            x: Current state.
            dt: Positive time step.
            drift: Shared deterministic drift or potential-gradient term.
            social_force: Optional common social force as callable or array.

        Returns:
            Updated and optionally clipped state.
        """

        if dt <= 0.0:
            raise ValueError("dt must be positive")
        state = np.asarray(x, dtype=float)
        total_update = np.zeros_like(state, dtype=float)
        deterministic = np.asarray(drift(state), dtype=float)

        for scale_name, params in self.timescales.items():
            component = self.state.setdefault(scale_name, np.zeros_like(state, dtype=float))
            tau = params["tau"]
            sigma = params["amplitude"]
            component = component + dt * (deterministic - component / tau)
            component = component + sigma * np.sqrt(dt) * self.rng.normal(size=state.shape)
            self.state[scale_name] = component
            total_update += component / tau

        if social_force is not None:
            force = social_force(state) if callable(social_force) else social_force
            total_update += np.asarray(force, dtype=float)

        next_state = state + dt * total_update
        if self.bounds is not None:
            next_state = np.clip(next_state, self.bounds[0], self.bounds[1])
        return next_state
