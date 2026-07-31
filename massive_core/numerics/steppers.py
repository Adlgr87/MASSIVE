"""Common stepper contract for opt-in MASSIVE numerical integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

import numpy as np

from .solvers import AdaptiveODESolver

Array = np.ndarray
DriftFunction = Callable[[Array], Array]
DiffusionFunction = Callable[[Array], Array]


@dataclass(frozen=True)
class NumericalDiagnostics:
    """Diagnostics produced by a dynamics stepper.

    Args:
        method: Numerical method used for the step.
        dt_next: Suggested next time step.
        metadata: Extra method-specific diagnostics.
    """

    method: str
    dt_next: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StepperResult:
    """Result returned by a ``DynamicsStepper``.

    Args:
        state: Updated state.
        diagnostics: Numerical diagnostics for the update.
    """

    state: Array
    diagnostics: NumericalDiagnostics


class DynamicsStepper(Protocol):
    """Protocol for numerical steppers used by MASSIVE engines."""

    def step(
        self,
        state: Array,
        dt: float,
        drift: DriftFunction,
        diffusion: DiffusionFunction | Array | float | None = None,
        noise: Array | None = None,
        bounds: tuple[float, float] | None = None,
        context: dict[str, Any] | None = None,
    ) -> StepperResult:
        """Advance one state update.

        Args:
            state: Current state array.
            dt: Positive time step.
            drift: Deterministic vector field.
            diffusion: Optional stochastic amplitude.
            noise: Optional standard-normal noise sample. Supplying this allows
                compatibility tests against existing Euler-Maruyama code paths.
            bounds: Optional uniform clipping range.
            context: Optional engine-specific metadata.

        Returns:
            Updated state and diagnostics.
        """


class EulerMaruyamaStepper:
    """Baseline Euler-Maruyama stepper matching the legacy update formula."""

    method = "euler_maruyama"

    def __init__(
        self,
        *,
        seed: int | None = None,
        rng: np.random.Generator | None = None,
    ) -> None:
        """Create a stepper with a local RNG for noise fallbacks.

        Args:
            seed: Optional seed when ``rng`` is not provided.
            rng: Optional NumPy Generator. Prefer supplying ``noise`` per step
                for fully external control of stochasticity.
        """

        self.rng = rng if rng is not None else np.random.default_rng(seed)

    def step(
        self,
        state: Array,
        dt: float,
        drift: DriftFunction,
        diffusion: DiffusionFunction | Array | float | None = None,
        noise: Array | None = None,
        bounds: tuple[float, float] | None = None,
        context: dict[str, Any] | None = None,
    ) -> StepperResult:
        """Advance one Euler-Maruyama update.

        Args:
            state: Current state.
            dt: Positive time step.
            drift: Deterministic vector field.
            diffusion: Optional stochastic amplitude.
            noise: Optional standard-normal noise sample.
            bounds: Optional uniform clipping range.
            context: Optional metadata, unused by this baseline.

        Returns:
            Updated state and diagnostics.
        """

        del context
        if dt <= 0.0:
            raise ValueError("dt must be positive")
        state_arr = np.asarray(state, dtype=float)
        update = state_arr + dt * np.asarray(drift(state_arr), dtype=float)
        if diffusion is not None:
            sigma = diffusion(state_arr) if callable(diffusion) else diffusion
            sigma_arr = np.asarray(sigma, dtype=float) * np.ones_like(state_arr)
            noise_arr = (
                np.asarray(noise, dtype=float)
                if noise is not None
                else self.rng.standard_normal(state_arr.shape)
            )
            update = update + sigma_arr * noise_arr * np.sqrt(dt)
        if bounds is not None:
            update = np.clip(update, bounds[0], bounds[1])
        return StepperResult(
            state=update,
            diagnostics=NumericalDiagnostics(method=self.method, dt_next=dt),
        )


class AdaptiveStepper:
    """Adapter exposing ``AdaptiveODESolver`` through ``DynamicsStepper``.

    Persists a single ``AdaptiveODESolver`` instance across steps and only
    refreshes drift/diffusion/bounds when they change identity.
    """

    method = "adaptive"

    def __init__(self) -> None:
        self._solver: AdaptiveODESolver | None = None
        self._bound_drift: DriftFunction | None = None
        self._bound_diffusion: Any = None
        self._bound_bounds: tuple[float, float] | None = None

    def step(
        self,
        state: Array,
        dt: float,
        drift: DriftFunction,
        diffusion: DiffusionFunction | Array | float | None = None,
        noise: Array | None = None,
        bounds: tuple[float, float] | None = None,
        context: dict[str, Any] | None = None,
    ) -> StepperResult:
        """Advance one adaptive update.

        Args:
            state: Current state.
            dt: Positive time step.
            drift: Deterministic vector field.
            diffusion: Optional stochastic amplitude.
            noise: Optional noise sample, ignored by the adaptive backend.
            bounds: Optional uniform clipping range.
            context: Optional metadata, unused by this adapter.

        Returns:
            Updated state and diagnostics.
        """

        del noise, context
        needs_new = (
            self._solver is None
            or drift is not self._bound_drift
            or diffusion is not self._bound_diffusion
            or bounds != self._bound_bounds
        )
        if needs_new:
            self._solver = AdaptiveODESolver(
                drift=drift, diffusion=diffusion, bounds=bounds
            )
            self._bound_drift = drift
            self._bound_diffusion = diffusion
            self._bound_bounds = bounds
        assert self._solver is not None
        next_state, dt_next = self._solver.step(np.asarray(state, dtype=float), dt)
        metadata: dict[str, Any] = {}
        method = self.method
        if self._solver.last_diagnostics is not None:
            method = self._solver.last_diagnostics.method
            metadata["stiffness_ratio"] = self._solver.last_diagnostics.stiffness_ratio
        return StepperResult(
            state=next_state,
            diagnostics=NumericalDiagnostics(method=method, dt_next=dt_next, metadata=metadata),
        )


def create_stepper(name: str | None) -> DynamicsStepper | None:
    """Create a stepper from a configuration name.

    Args:
        name: ``None``/``legacy`` for no wrapper, ``euler_maruyama`` or
            ``adaptive``.

    Returns:
        Stepper instance or ``None`` for legacy engine paths.
    """

    normalized = (name or "legacy").lower()
    if normalized in {"legacy", "legacy_euler_maruyama", "none"}:
        return None
    if normalized in {"euler", "euler_maruyama"}:
        return EulerMaruyamaStepper()
    if normalized in {"adaptive", "adaptive_ode"}:
        return AdaptiveStepper()
    raise ValueError(f"Unknown solver: {name}")
