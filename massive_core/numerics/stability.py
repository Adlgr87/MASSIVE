"""Stability and convergence diagnostics for MASSIVE-like dynamics."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
from scipy.sparse.linalg import eigsh

logger = logging.getLogger(__name__)

Array = np.ndarray


@dataclass(frozen=True)
class StabilityReport:
    """Summary of local linear stability diagnostics.

    Args:
        eigenvalues: Eigenvalues of the local Jacobian.
        spectral_radius: Maximum absolute eigenvalue.
        max_real_eigenvalue: Largest real part across eigenvalues.
        stable: Whether all real parts are negative within tolerance.
    """

    eigenvalues: Array
    spectral_radius: float
    max_real_eigenvalue: float
    stable: bool


class StabilityAnalyzer:
    """Computes Jacobian, spectral and Lyapunov diagnostics.

    Args:
        vector_field: Optional dynamics function ``f(x)`` used by Jacobian
            methods when a method-specific function is not supplied.
    """

    def __init__(self, vector_field: Optional[Callable[[Array], Array]] = None) -> None:
        self.vector_field = vector_field

    def compute_jacobian(
        self,
        x: Array,
        vector_field: Optional[Callable[[Array], Array]] = None,
        eps: float = 1e-6,
    ) -> Array:
        """Estimate a dense Jacobian by central finite differences.

        Args:
            x: State where the Jacobian is evaluated.
            vector_field: Optional override for ``self.vector_field``.
            eps: Perturbation size.

        Returns:
            Jacobian matrix with shape ``(x.size, x.size)``.
        """

        f = vector_field or self.vector_field
        if f is None:
            raise ValueError("A vector_field must be provided")

        x_arr = np.asarray(x, dtype=float)
        flat = x_arr.reshape(-1)
        shape = x_arr.shape
        jacobian = np.zeros((flat.size, flat.size), dtype=float)
        for i in range(flat.size):
            plus = flat.copy()
            minus = flat.copy()
            plus[i] += eps
            minus[i] -= eps
            f_plus = np.asarray(f(plus.reshape(shape)), dtype=float).reshape(-1)
            f_minus = np.asarray(f(minus.reshape(shape)), dtype=float).reshape(-1)
            jacobian[:, i] = (f_plus - f_minus) / (2.0 * eps)
        return jacobian

    def analyze_linear_stability(
        self,
        x: Array,
        vector_field: Optional[Callable[[Array], Array]] = None,
        tolerance: float = 1e-9,
    ) -> StabilityReport:
        """Classify local linear stability from Jacobian eigenvalues.

        Args:
            x: State where the system should be linearized.
            vector_field: Optional dynamics function.
            tolerance: Numerical tolerance for negative real parts.

        Returns:
            Stability report.
        """

        jacobian = self.compute_jacobian(x, vector_field)
        eigenvalues = np.linalg.eigvals(jacobian)
        spectral_radius = float(np.max(np.abs(eigenvalues))) if eigenvalues.size else 0.0
        max_real = float(np.max(eigenvalues.real)) if eigenvalues.size else 0.0
        return StabilityReport(eigenvalues, spectral_radius, max_real, max_real < -tolerance)

    def compute_spectral_radius(self, matrix: Array, iterations: int = 100, tol: float = 1e-10) -> float:
        """Estimate spectral radius with power iteration.

        Args:
            matrix: Square matrix.
            iterations: Maximum power iterations.
            tol: Convergence tolerance on the eigenvalue estimate.

        Returns:
            Estimated spectral radius.
        """

        mat = np.asarray(matrix, dtype=float)
        if mat.ndim != 2 or mat.shape[0] != mat.shape[1]:
            raise ValueError("matrix must be square")
        if mat.size == 0:
            return 0.0

        vector = np.ones(mat.shape[1], dtype=float)
        vector /= np.linalg.norm(vector)
        last_value = 0.0
        for _ in range(iterations):
            next_vector = mat @ vector
            norm = np.linalg.norm(next_vector)
            if norm == 0.0:
                return 0.0
            vector = next_vector / norm
            value = float(abs(vector @ (mat @ vector)))
            if abs(value - last_value) < tol:
                break
            last_value = value
        return last_value

    def compute_lyapunov_exponent(self, trajectory: Array, dt: float) -> float:
        """Estimate the largest Lyapunov exponent from a trajectory.

        The estimator uses the average log ratio of consecutive increments. It
        is a lightweight diagnostic rather than a full tangent-space algorithm.

        Args:
            trajectory: Array with time along axis 0.
            dt: Positive time step.

        Returns:
            Approximate largest Lyapunov exponent.
        """

        if dt <= 0.0:
            raise ValueError("dt must be positive")
        values = np.asarray(trajectory, dtype=float)
        if values.shape[0] < 3:
            raise ValueError("trajectory needs at least three time points")

        increments = np.linalg.norm(np.diff(values.reshape(values.shape[0], -1), axis=0), axis=1)
        ratios = (increments[1:] + 1e-12) / (increments[:-1] + 1e-12)
        return float(np.mean(np.log(ratios)) / dt)

    def compute_lyapunov_exponents(self, trajectory: Array, dt: float) -> Array:
        """Estimate one Lyapunov-like exponent per state dimension.

        Args:
            trajectory: Time series with shape ``(time, dimensions)``.
            dt: Positive time step.

        Returns:
            Vector of per-dimension exponents.
        """

        data = np.asarray(trajectory, dtype=float)
        flat = data.reshape(data.shape[0], -1)
        return np.array([self.compute_lyapunov_exponent(flat[:, i], dt) for i in range(flat.shape[1])])


# ---------------------------------------------------------------------------
# Extended API: StabilityAnalyzer with equilibrium state (sparse-mode)
# ---------------------------------------------------------------------------


class SparseStabilityAnalyzer:
    """Extended stability analyzer supporting equilibrium-based scans.

    This class wraps :class:`StabilityAnalyzer` and adds equilibrium-focused
    diagnostics, random-IC scanning, and optional sparse eigensolvers for
    large Jacobians.

    Parameters
    ----------
    system_fn :
        Callable ``state → state`` defining the sociodynamic system.
    equilibrium :
        The equilibrium state at which to evaluate stability.
    jacobian_fn :
        Optional callable ``state → Jacobian``.  If *None*, finite
        differences are used.
    n_random_perturbations :
        Number of random initial conditions to scan for global stability.
    rng :
        Numpy random generator (default ``default_rng``).
    """

    def __init__(
        self,
        system_fn: Optional[Callable[[Array], Array]] = None,
        equilibrium: Optional[Array] = None,
        jacobian_fn: Optional[Callable[[Array], Array]] = None,
        n_random_perturbations: int = 5,
        rng: Optional[np.random.Generator] = None,
    ) -> None:
        self._legacy = StabilityAnalyzer(system_fn)
        self.equilibrium = equilibrium
        self.jacobian_fn = jacobian_fn
        self.n_random_perturbations = n_random_perturbations
        self.rng = rng if rng is not None else np.random.default_rng()

    # ------------------------------------------------------------------
    # Compatibility
    # ------------------------------------------------------------------

    def compute_jacobian(
        self,
        x: Array,
        vector_field: Optional[Callable[[Array], Array]] = None,
        eps: float = 1e-6,
    ) -> Array:
        """Delegate to :meth:`StabilityAnalyzer.compute_jacobian`."""
        return self._legacy.compute_jacobian(x, vector_field=vector_field, eps=eps)

    def analyze_linear_stability(
        self,
        x: Array,
        vector_field: Optional[Callable[[Array], Array]] = None,
        tolerance: float = 1e-9,
    ) -> StabilityReport:
        """Delegate to :meth:`StabilityAnalyzer.analyze_linear_stability`."""
        return self._legacy.analyze_linear_stability(
            x, vector_field=vector_field, tolerance=tolerance
        )

    def compute_spectral_radius(
        self,
        matrix: Array,
        iterations: int = 100,
        tol: float = 1e-10,
    ) -> float:
        """Delegate to :meth:`StabilityAnalyzer.compute_spectral_radius`."""
        return self._legacy.compute_spectral_radius(
            matrix, iterations=iterations, tol=tol
        )

    # ------------------------------------------------------------------
    # Extended diagnostics
    # ------------------------------------------------------------------

    def analyze(self, state: Optional[Array] = None,
                eps: float = 1e-6,
                sparse: bool = False,
                k: Optional[int] = None) -> StabilityReport:
        """Perform a full stability analysis.

        Parameters
        ----------
        state :
            State at which to evaluate stability.  Falls back to
            :attr:`equilibrium` if *None*.
        eps :
            Finite-difference step for Jacobian approximation.
        sparse :
            Use sparse eigensolver.
        k :
            Number of eigenvalues to compute (sparse mode).

        Returns
        -------
        StabilityReport
            Stability diagnostics (same schema as :class:`StabilityReport`).
        """
        state = state if state is not None else self.equilibrium
        if state is None:
            raise ValueError("state or equilibrium must be provided")

        # Compute Jacobian (optionally using jacobian_fn)
        if self.jacobian_fn is not None:
            jacobian = self.jacobian_fn(np.asarray(state, dtype=float))
        else:
            jacobian = self._legacy.compute_jacobian(state, eps=eps)

        # Eigenvalue computation (dense or sparse)
        if sparse and k is not None and k < jacobian.shape[0]:
            try:
                eigenvalues = eigsh(jacobian, k=k, which="LR", return_eigenvectors=False)
            except Exception:
                eigenvalues = np.linalg.eigvals(jacobian)
        else:
            eigenvalues = np.linalg.eigvals(jacobian)

        spectral_radius = float(np.max(np.abs(eigenvalues))) if eigenvalues.size else 0.0
        max_real = float(np.max(eigenvalues.real)) if eigenvalues.size else 0.0

        logger.info(
            "Stability analysis complete. Stable: %s, Dominant eigenvalue: %.4f",
            max_real < -1e-9, max_real,
        )

        return StabilityReport(eigenvalues, spectral_radius, max_real, max_real < -1e-9)

    def scan_initial_conditions(self, n_samples: Optional[int] = None,
                                 eps: float = 1e-6) -> list[StabilityReport]:
        """Scan multiple initial conditions to assess global stability.

        Parameters
        ----------
        n_samples :
            Number of random initial conditions.  Defaults to
            :attr:`n_random_perturbations`.
        eps :
            Finite-difference step for Jacobian approximation.

        Returns
        -------
        list[StabilityReport]
            Stability reports for each sampled initial condition.
        """
        if self.equilibrium is None:
            raise ValueError("equilibrium must be set for scanning")

        n_samples = n_samples or self.n_random_perturbations
        state_dim = len(self.equilibrium)

        reports: list[StabilityReport] = []
        for i in range(n_samples):
            perturbation = self.rng.standard_normal(state_dim) * 0.1
            initial_state = self.equilibrium + perturbation

            report = self.analyze(state=initial_state, eps=eps)
            reports.append(report)

            logger.info(
                "Scan %d/%d: Stable=%s, Dominant eigenvalue=%.4f",
                i + 1, n_samples, report.stable, report.max_real_eigenvalue,
            )

        return reports

    def get_stability_status(self, state: Optional[Array] = None,
                             eps: float = 1e-6) -> str:
        """Return a human-readable stability status string."""
        report = self.analyze(state, eps)
        if report.stable:
            return f"Stable (dominant eigenvalue: {report.max_real_eigenvalue:.4f})"
        else:
            return f"Unstable (dominant eigenvalue: {report.max_real_eigenvalue:.4f})"
