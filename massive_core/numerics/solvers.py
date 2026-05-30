"""Adaptive deterministic and stochastic steppers for MASSIVE dynamics.

The classes in this module are intentionally independent from the legacy
``simular`` API.  They provide reusable building blocks for future engines
without changing existing simulation behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

Array = np.ndarray
Drift = Callable[[Array], Array]
Diffusion = Callable[[Array], Array] | Array | float | None


@dataclass(frozen=True)
class SolverDiagnostics:
    """Metadata produced by an adaptive solver step.

    Args:
        method: Name of the numerical method selected for the step.
        stiffness_ratio: Local stiffness proxy used for method selection.
        dt_next: Suggested next time step after the current step.
    """

    method: str
    stiffness_ratio: float
    dt_next: float


class AdaptiveODESolver:
    """Selects a stable stepper from local stiffness diagnostics.

    The solver supports deterministic ODEs and additive/multiplicative SDEs.
    It keeps the API small: callers provide a drift function, an optional
    diffusion term, and a clipping range for bounded MASSIVE state variables.

    Args:
        drift: Function returning the deterministic vector field ``f(x)``.
        diffusion: Optional scalar, vector/matrix, or callable noise amplitude.
        bounds: Optional ``(min, max)`` clipping range applied after each step.
        rng: Optional NumPy random generator for reproducible stochastic steps.
        stiffness_soft: Below this ratio Milstein/Euler methods are preferred.
        stiffness_hard: Above this ratio an implicit Euler fixed-point step is
            preferred for stability.
    """

    def __init__(
        self,
        drift: Drift,
        diffusion: Diffusion = None,
        bounds: tuple[float, float] | None = None,
        rng: np.random.Generator | None = None,
        stiffness_soft: float = 10.0,
        stiffness_hard: float = 100.0,
    ) -> None:
        self.drift = drift
        self.diffusion = diffusion
        self.bounds = bounds
        self.rng = rng or np.random.default_rng()
        self.stiffness_soft = stiffness_soft
        self.stiffness_hard = stiffness_hard
        self.last_diagnostics: SolverDiagnostics | None = None

    def step(self, x: Array, dt_current: float) -> tuple[Array, float]:
        """Advance one adaptive step.

        Args:
            x: Current state vector or matrix.
            dt_current: Current positive time step.

        Returns:
            Tuple ``(x_next, dt_next)`` with the clipped next state and a
            conservative suggestion for the following step.
        """

        if dt_current <= 0.0:
            raise ValueError("dt_current must be positive")

        x_arr = np.asarray(x, dtype=float)
        ratio = self.estimate_stiffness(x_arr)
        has_noise = self.diffusion is not None

        if ratio >= self.stiffness_hard:
            method = "implicit_euler_maruyama" if has_noise else "backward_euler"
            x_next = self._implicit_euler_step(x_arr, dt_current)
            if has_noise:
                x_next = x_next + self._noise_increment(x_arr, dt_current)
            dt_next = max(dt_current * 0.5, np.finfo(float).eps)
        elif ratio >= self.stiffness_soft:
            method = "rk4_maruyama" if has_noise else "rk4"
            x_next = self._rk4_step(x_arr, dt_current)
            if has_noise:
                x_next = x_next + self._noise_increment(x_arr, dt_current)
            dt_next = dt_current
        elif has_noise:
            method = "milstein"
            x_next = self._milstein_step(x_arr, dt_current)
            dt_next = dt_current * 1.1
        else:
            method = "euler"
            x_next = self._euler_step(x_arr, dt_current)
            dt_next = dt_current * 1.1

        x_next = self._clip(x_next)
        self.last_diagnostics = SolverDiagnostics(method, ratio, dt_next)
        return x_next, dt_next

    def estimate_stiffness(self, x: Array) -> float:
        """Estimate local stiffness via ``||J f(x)|| / ||f(x)||``.

        Args:
            x: State where the Jacobian should be estimated.

        Returns:
            Non-negative stiffness proxy.
        """

        f = np.asarray(self.drift(x), dtype=float)
        jacobian = self.estimate_jacobian(x)
        numerator = np.linalg.norm(jacobian @ f.reshape(-1))
        denominator = np.linalg.norm(f) + 1e-12
        return float(numerator / denominator)

    def estimate_jacobian(self, x: Array, eps: float = 1e-6) -> Array:
        """Estimate the drift Jacobian with central finite differences.

        Args:
            x: State where the Jacobian should be estimated.
            eps: Perturbation size.

        Returns:
            Dense Jacobian with shape ``(x.size, x.size)``.
        """

        flat = np.asarray(x, dtype=float).reshape(-1)
        original_shape = np.asarray(x).shape
        jacobian = np.zeros((flat.size, flat.size), dtype=float)
        for i in range(flat.size):
            plus = flat.copy()
            minus = flat.copy()
            plus[i] += eps
            minus[i] -= eps
            f_plus = np.asarray(self.drift(plus.reshape(original_shape))).reshape(-1)
            f_minus = np.asarray(self.drift(minus.reshape(original_shape))).reshape(-1)
            jacobian[:, i] = (f_plus - f_minus) / (2.0 * eps)
        return jacobian

    def _euler_step(self, x: Array, dt: float) -> Array:
        return x + dt * np.asarray(self.drift(x), dtype=float)

    def _rk4_step(self, x: Array, dt: float) -> Array:
        k1 = np.asarray(self.drift(x), dtype=float)
        k2 = np.asarray(self.drift(x + 0.5 * dt * k1), dtype=float)
        k3 = np.asarray(self.drift(x + 0.5 * dt * k2), dtype=float)
        k4 = np.asarray(self.drift(x + dt * k3), dtype=float)
        return x + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

    def _implicit_euler_step(self, x: Array, dt: float, iterations: int = 8) -> Array:
        x_next = self._euler_step(x, dt)
        for _ in range(iterations):
            x_next = x + dt * np.asarray(self.drift(x_next), dtype=float)
            x_next = self._clip(x_next)
        return x_next

    def _milstein_step(self, x: Array, dt: float) -> Array:
        sigma = self._diffusion_value(x)
        d_w = self.rng.normal(0.0, np.sqrt(dt), size=x.shape)
        base = self._euler_step(x, dt) + sigma * d_w
        if callable(self.diffusion):
            sigma_grad = self._diffusion_derivative_diag(x)
            base = base + 0.5 * sigma * sigma_grad * (d_w**2 - dt)
        return base

    def _noise_increment(self, x: Array, dt: float) -> Array:
        sigma = self._diffusion_value(x)
        return sigma * self.rng.normal(0.0, np.sqrt(dt), size=x.shape)

    def _diffusion_value(self, x: Array) -> Array:
        if callable(self.diffusion):
            value = self.diffusion(x)
        else:
            value = self.diffusion
        return np.asarray(value, dtype=float) * np.ones_like(x, dtype=float)

    def _diffusion_derivative_diag(self, x: Array, eps: float = 1e-6) -> Array:
        grad = np.zeros_like(x, dtype=float)
        flat = x.reshape(-1)
        shape = x.shape
        for i in range(flat.size):
            plus = flat.copy()
            minus = flat.copy()
            plus[i] += eps
            minus[i] -= eps
            s_plus = np.asarray(self.diffusion(plus.reshape(shape))).reshape(-1)
            s_minus = np.asarray(self.diffusion(minus.reshape(shape))).reshape(-1)
            grad.reshape(-1)[i] = (s_plus[i] - s_minus[i]) / (2.0 * eps)
        return grad

    def _clip(self, x: Array) -> Array:
        if self.bounds is None:
            return x
        lower, upper = self.bounds
        return np.clip(x, lower, upper)
