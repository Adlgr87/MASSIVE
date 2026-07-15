"""Perturbation-theory helpers for weakly coupled MASSIVE dynamics."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)

Array = np.ndarray


@dataclass
class StabilityReport:
    """Summary of local linear stability diagnostics.

    Attributes (backward-compatible):
        eigenvalues: Eigenvalues of the local Jacobian.
        spectral_radius: Maximum absolute eigenvalue.
        max_real_eigenvalue: Largest real part across eigenvalues.
        stable: Whether all real parts are negative within tolerance.
    """
    eigenvalues: Array
    spectral_radius: float
    max_real_eigenvalue: float
    stable: bool


@dataclass
class PerturbationResult:
    """Results of a perturbation analysis.

    Attributes
    ----------
    unperturbed_state :
        Original state vector.
    perturbed_state :
        State after perturbation.
    displacement :
        Norm of the perturbation.
    relative_displacement :
        Relative displacement (L2 norm / original norm).
    stability :
        Whether the perturbed state remains near equilibrium.
    iterations :
        Number of iterations performed.
    """
    unperturbed_state: np.ndarray
    perturbed_state: np.ndarray
    displacement: float
    relative_displacement: float
    stability: bool
    iterations: int


@dataclass
class ParameterSensitivity:
    """Parameter sensitivity analysis results.

    Attributes
    ----------
    parameter :
        Name or index of the perturbed parameter.
    nominal_value :
        Nominal value of the parameter.
    perturbed_value :
        Perturbed value of the parameter.
    effect_size :
        Absolute change in the system state.
    relative_effect :
        Relative change in the system state.
    sensitivity_coefficient :
        Normalised sensitivity (relative effect / relative perturbation).
    """
    parameter: Union[str, int]
    nominal_value: float
    perturbed_value: float
    effect_size: float
    relative_effect: float
    sensitivity_coefficient: float


# ============================================================================
# Legacy: PerturbationTheorySolver (dt / n_steps / bounds API)
# ============================================================================


class PerturbationTheorySolver:
    """Computes low-order perturbative trajectories.

    Args:
        dt: Positive integration step.
        n_steps: Number of integration steps.
        bounds: Optional clipping range for bounded states.
    """

    def __init__(self, dt: float = 0.01, n_steps: int = 100,
                 bounds: Optional[tuple[float, float]] = None) -> None:
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
                drift = drift + 0.5 * (strength ** 2) * self._directional_correction(
                    state, perturbation
                )
            state = state + self.dt * drift
            if self.bounds is not None:
                state = np.clip(state, self.bounds[0], self.bounds[1])
            trajectory.append(state.copy())
        return np.asarray(trajectory)

    def compute_green_function(self, operator: Array, source: Array,
                                regularization: float = 1e-2) -> Array:
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

    def _directional_correction(self, state: Array,
                                 perturbation: Callable[[Array], Array]) -> Array:
        eps = 1e-6
        direction = np.asarray(perturbation(state), dtype=float)
        norm = np.linalg.norm(direction)
        if norm == 0.0:
            return np.zeros_like(state, dtype=float)
        unit = direction / norm
        return (np.asarray(perturbation(state + eps * unit), dtype=float) - direction) / eps


# ============================================================================
# Extended: Equilibrium-based solver (stable + perturbation/scanning)
# ============================================================================


class EquilibriumPerturbationSolver:
    """Equilibrium-focused perturbation & stability analysis.

    This class adds equilibrium-based diagnostics, state perturbations,
    parameter sensitivity scans, and eigenvalue analysis on top of the
    legacy solver.

    Parameters
    ----------
    system_fn :
        Callable ``state → state`` defining the sociodynamic system.
    equilibrium :
        The equilibrium state at which perturbations are centred.
    jacobian_fn :
        Optional callable ``state → Jacobian``.  If *None*, finite
        differences are used.
    rng :
        Random number generator for stochastic perturbations.
    tolerance :
        Threshold for determining whether the perturbed state is still
        considered "near" equilibrium.
    """

    def __init__(
        self,
        system_fn: Optional[Callable[[Array], Array]] = None,
        equilibrium: Optional[Array] = None,
        jacobian_fn: Optional[Callable[[Array], Array]] = None,
        rng: Optional[np.random.Generator] = None,
        tolerance: float = 1e-4,
    ) -> None:
        self.system_fn = system_fn
        self.equilibrium = equilibrium
        self.jacobian_fn = jacobian_fn
        self.rng = rng if rng is not None else np.random.default_rng()
        self.tolerance = tolerance

    def _compute_jacobian(self, state: Array, eps: float = 1e-6) -> Array:
        """Compute the Jacobian at *state* via finite differences."""
        n = len(state)
        jacobian = np.zeros((n, n))
        base = self.system_fn(state)
        for i in range(n):
            perturbed = state.copy()
            perturbed[i] += eps
            jacobian[:, i] = (self.system_fn(perturbed) - base) / eps
        return jacobian

    def get_jacobian(self, state: Optional[Array] = None,
                     eps: float = 1e-6) -> Array:
        """Return the Jacobian at the given state."""
        state = state or self.equilibrium
        if state is None:
            raise ValueError("state or equilibrium must be provided")
        if self.jacobian_fn is not None:
            return self.jacobian_fn(state)
        return self._compute_jacobian(state, eps)

    def perturb_state(self, magnitude: float,
                      perturbation_type: str = "uniform",
                      max_iterations: int = 100) -> PerturbationResult:
        """Apply a perturbation to the current state."""
        if self.equilibrium is None:
            raise ValueError("equilibrium must be set")

        state = self.equilibrium.copy()
        n = len(state)

        if perturbation_type == "uniform":
            perturbation = self.rng.standard_normal(n)
            perturbation = perturbation / np.linalg.norm(perturbation) * magnitude
        elif perturbation_type == "normal":
            perturbation = self.rng.normal(0, magnitude / np.sqrt(n), size=n)
        elif perturbation_type == "targeted":
            n_perturb = max(1, n // 3)
            perturbation = np.zeros(n)
            indices = self.rng.choice(n, size=n_perturb, replace=False)
            perturbation[indices] = self.rng.standard_normal(n_perturb)
            perturbation = perturbation / np.linalg.norm(perturbation) * magnitude
        elif perturbation_type == "structured":
            perturbation = self.rng.standard_normal(n)
            rank = max(1, n // 5)
            principal = self.rng.standard_normal((n, rank))
            perturbation = principal @ self.rng.standard_normal(rank)
            perturbation = perturbation / np.linalg.norm(perturbation) * magnitude
        else:
            raise ValueError(f"Unknown perturbation type: {perturbation_type!r}")

        perturbed_state = state + perturbation

        for _ in range(max_iterations):
            new_state = self.system_fn(perturbed_state)
            residual = np.linalg.norm(new_state - perturbed_state)
            if residual < self.tolerance:
                break
            perturbed_state = new_state

        displacement = float(np.linalg.norm(perturbed_state - state))
        state_norm = float(np.linalg.norm(state))
        relative_displacement = displacement / state_norm if state_norm > 0 else float("inf")
        stability = displacement < self.tolerance * state_norm

        result = PerturbationResult(
            unperturbed_state=state,
            perturbed_state=perturbed_state,
            displacement=displacement,
            relative_displacement=relative_displacement,
            stability=stability,
            iterations=max_iterations,
        )

        logger.info(
            "State perturbation applied: displacement=%.6f, relative=%.6f, stable=%s",
            displacement, relative_displacement, stability,
        )

        return result

    def analyze_parameter_sensitivity(self, parameter_index: int,
                                       nominal_value: float,
                                       perturbation_fraction: float = 0.01,
                                       state: Optional[Array] = None) -> ParameterSensitivity:
        """Analyse the sensitivity of the system to parameter changes."""
        if self.equilibrium is None:
            raise ValueError("equilibrium must be set")
        state = state or self.equilibrium
        perturbed_value = nominal_value * (1 + perturbation_fraction)

        perturbed_state = state.copy()
        perturbed_state[parameter_index] = perturbed_value

        response = self.system_fn(perturbed_state)
        nominal_response = self.system_fn(state)

        effect_size = float(np.linalg.norm(response - nominal_response))
        response_norm = float(np.linalg.norm(nominal_response))
        relative_effect = effect_size / response_norm if response_norm > 0 else float("inf")
        sensitivity = (relative_effect / perturbation_fraction) if perturbation_fraction != 0 else 0.0

        return ParameterSensitivity(
            parameter=parameter_index,
            nominal_value=nominal_value,
            perturbed_value=perturbed_value,
            effect_size=effect_size,
            relative_effect=relative_effect,
            sensitivity_coefficient=sensitivity,
        )

    def analyze_all_parameters(self, nominal_values: Array,
                                perturbation_fraction: float = 0.01,
                                state: Optional[Array] = None) -> list[ParameterSensitivity]:
        """Analyse sensitivity for all parameters simultaneously."""
        results: list[ParameterSensitivity] = []
        n_params = int(np.asarray(nominal_values).shape[0])
        for i in range(n_params):
            result = self.analyze_parameter_sensitivity(
                i, nominal_values[i], perturbation_fraction, state,
            )
            results.append(result)
        return results

    def stability_analysis(self, state: Optional[Array] = None) -> StabilityReport:
        """Perform a stability analysis of the system at *state*."""
        if self.equilibrium is None:
            raise ValueError("equilibrium must be set")
        jacobian = self.get_jacobian(state)
        eigenvalues = np.linalg.eigvals(jacobian)

        spectral_radius = float(np.max(np.abs(eigenvalues))) if eigenvalues.size else 0.0
        max_real = float(np.max(eigenvalues.real)) if eigenvalues.size else 0.0
        stable = bool(max_real < -1e-9)

        return StabilityReport(eigenvalues, spectral_radius, max_real, stable)
