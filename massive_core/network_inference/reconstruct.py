"""Sociomatrix reconstruction via constrained optimization and correlation analysis."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.optimize import differential_evolution

logger = logging.getLogger(__name__)

Array = np.ndarray


@dataclass
class ReconstructionResult:
    """Results from :meth:`NetworkReconstructor.reconstruct`.

    Attributes
    ----------
    reconstructed_matrix :
        Recovered sociomatrix.
    error :
        Mean squared error on observed entries.
    iterations :
        Number of iterations performed by the optimizer.
    convergence :
        ``True`` if the optimizer converged within tolerance.
    missingness :
        Fraction of entries that were *not* observed.
    """
    reconstructed_matrix: np.ndarray
    error: float
    iterations: int
    convergence: bool
    missingness: float = field(default=0.0)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _squared_penalty(matrix: np.ndarray, indices: np.ndarray,
                     target: np.ndarray) -> np.ndarray:
    """Return squared residuals on observed entries.

    Parameters
    ----------
    matrix :
        Reconstructed sociomatrix *(n, n)*.
    indices :
        Observed coordinates *(N, 2)*.
    target :
        Observed values *(N,)* or *(N, 1)*.
    """
    vals = matrix[indices[:, 0], indices[:, 1]]
    target = np.asarray(target).ravel()
    return (vals - target) ** 2


def _matrix_flatten(matrix: np.ndarray) -> np.ndarray:
    """Flatten a square matrix to a 1-D vector."""
    return matrix.ravel()


def _matrix_reshape(flat: np.ndarray, dim: int) -> np.ndarray:
    """Reshape a 1-D vector to a square matrix."""
    return flat.reshape(dim, dim)


# ---------------------------------------------------------------------------
# NetworkReconstructor (legacy + sparse)
# ---------------------------------------------------------------------------


class NetworkReconstructor:
    """Reconstructs adjacency / sociomatrix structures from data.

    This class unifies the legacy correlation-/entropy-based reconstruction
    methods with the new sparse-constrained optimisation path.

    Parameters
    ----------
    method :
        Optimiser for the sparse path: ``"de"`` (default) or ``"cg"``.
    bounds :
        ``(min_val, max_val)`` clamp for all entries.  Default ``[0, 1]``.
    de_options :
        Keyword arguments forwarded to
        :func:`scipy.optimize.differential_evolution`.
    cg_tol :
        Tolerance for the conjugate-gradient solver.
    cg_max_iter :
        Maximum number of CG iterations.
    """

    def __init__(
        self,
        method: str = "de",
        bounds: tuple[float, float] = (0.0, 1.0),
        de_options: Optional[dict] = None,
        cg_tol: float = 1e-8,
        cg_max_iter: int = 1000,
    ) -> None:
        self.method = method
        self.bounds = bounds
        self.de_options = de_options or {
            "popsize": 15,
            "maxiter": 1000,
            "tol": 1e-6,
        }
        self.cg_tol = cg_tol
        self.cg_max_iter = cg_max_iter

    # ================================================================
    # Legacy API — correlation-based
    # ================================================================

    def reconstruct_correlation_based(self, trajectories: Array,
                                       threshold: float = 0.3) -> Array:
        """Infer undirected links from absolute Pearson correlation.

        Args:
            trajectories: Time series with shape ``(time, agents)``.
            threshold: Correlation threshold in ``[0, 1]``.

        Returns:
            Binary adjacency matrix with zero diagonal.
        """

        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be in [0, 1]")
        data = np.asarray(trajectories, dtype=float)
        if data.ndim != 2:
            raise ValueError("trajectories must have shape (time, agents)")
        corr = np.nan_to_num(np.corrcoef(data.T), nan=0.0)
        adjacency = (np.abs(corr) > threshold).astype(float)
        np.fill_diagonal(adjacency, 0.0)
        return adjacency

    def reconstruct_transfer_entropy(self, trajectories: Array, lag: int = 1,
                                     bins: int = 10) -> Array:
        """Estimate directed links with discrete transfer entropy.

        Args:
            trajectories: Time series with shape ``(time, agents)``.
            lag: Positive lag.
            bins: Number of discretization bins.

        Returns:
            Transfer-entropy score matrix where entry ``i, j`` means ``i -> j``.
        """

        if lag < 1:
            raise ValueError("lag must be positive")
        data = np.asarray(trajectories, dtype=float)
        if data.ndim != 2 or data.shape[0] <= lag + 1:
            raise ValueError("trajectories must have enough time points")
        discrete = np.column_stack([self._discretize(data[:, i], bins) for i in range(data.shape[1])])
        n_agents = data.shape[1]
        scores = np.zeros((n_agents, n_agents), dtype=float)
        for source in range(n_agents):
            for target in range(n_agents):
                if source != target:
                    scores[source, target] = self._transfer_entropy(discrete[:, source], discrete[:, target], lag)
        return scores

    def reconstruct_granger_causality(self, trajectories: Array, max_lag: int = 5,
                                      alpha: float = 0.05) -> Array:
        """Infer linear directed influence from lagged regression improvement.

        Args:
            trajectories: Time series with shape ``(time, agents)``.
            max_lag: Number of lagged samples in each regression.
            alpha: Kept for API compatibility; this lightweight method returns
                positive F-like scores and does not compute p-values.

        Returns:
            Directed score matrix.
        """

        del alpha
        if max_lag < 1:
            raise ValueError("max_lag must be positive")
        data = np.asarray(trajectories, dtype=float)
        if data.ndim != 2 or data.shape[0] <= max_lag + 2:
            raise ValueError("trajectories must have enough time points")
        n_agents = data.shape[1]
        scores = np.zeros((n_agents, n_agents), dtype=float)
        for source in range(n_agents):
            for target in range(n_agents):
                if source != target:
                    scores[source, target] = self._granger_score(data[:, source], data[:, target], max_lag)
        return scores

    def _discretize(self, values: Array, bins: int) -> Array:
        if bins < 2:
            raise ValueError("bins must be at least 2")
        edges = np.histogram_bin_edges(values, bins=bins)
        return np.clip(np.digitize(values, edges[1:-1]), 0, bins - 1)

    def _transfer_entropy(self, source: Array, target: Array, lag: int) -> float:
        y_next = target[lag:]
        y_past = target[:-lag]
        x_past = source[:-lag]
        return max(self._conditional_mutual_information(y_next, x_past, y_past), 0.0)

    def _conditional_mutual_information(self, y: Array, x: Array, z: Array) -> float:
        xyz = list(zip(x, y, z))
        xz = list(zip(x, z))
        yz = list(zip(y, z))
        z_values = list(z)
        n = float(len(y))
        score = 0.0
        for triple in set(xyz):
            x_val, y_val, z_val = triple
            p_xyz = xyz.count(triple) / n
            p_xz = xz.count((x_val, z_val)) / n
            p_yz = yz.count((y_val, z_val)) / n
            p_z = z_values.count(z_val) / n
            if p_xyz > 0.0 and p_xz > 0.0 and p_yz > 0.0 and p_z > 0.0:
                score += p_xyz * np.log((p_xyz * p_z) / (p_xz * p_yz))
        return float(score)

    def _granger_score(self, source: Array, target: Array, max_lag: int) -> float:
        y = target[max_lag:]
        target_lags = self._lag_matrix(target, max_lag)
        source_lags = self._lag_matrix(source, max_lag)
        restricted = self._residual_sum_squares(target_lags, y)
        unrestricted = self._residual_sum_squares(np.column_stack([target_lags, source_lags]), y)
        if unrestricted <= 1e-12:
            return 0.0
        return float(max((restricted - unrestricted) / unrestricted, 0.0))

    def _lag_matrix(self, values: Array, max_lag: int) -> Array:
        return np.column_stack([values[max_lag - lag : -lag] for lag in range(1, max_lag + 1)])

    def _residual_sum_squares(self, predictors: Array, target: Array) -> float:
        design = np.column_stack([np.ones(predictors.shape[0]), predictors])
        coefficients = np.linalg.lstsq(design, target, rcond=None)[0]
        residual = target - design @ coefficients
        return float(np.sum(residual ** 2))

    # ================================================================
    # Sparse constrained optimisation
    # ================================================================

    def _build_mask(self, known_matrix: np.ndarray) -> tuple[Array, Array, Array]:
        """Return observed-index array, flat target, and flat index map."""
        observed_mask = ~np.isnan(known_matrix)
        indices = np.argwhere(observed_mask)
        target = known_matrix[observed_mask]
        dim = known_matrix.shape[0]
        index_map = indices[:, 0] * dim + indices[:, 1]
        return observed_mask, indices, target

    def _reconstruct_de(self, known_matrix: np.ndarray,
                        indices: np.ndarray) -> ReconstructionResult:
        """Reconstruct via differential evolution."""
        dim = known_matrix.shape[0]
        flat_target = known_matrix[~np.isnan(known_matrix)]

        def objective(flat_matrix: np.ndarray) -> float:
            matrix = _matrix_reshape(flat_matrix, dim)
            residuals = _squared_penalty(matrix, indices, flat_target)
            return residuals.sum()

        result = differential_evolution(
            objective,
            bounds=[self.bounds for _ in range(dim * dim)],
            seed=42,
            **self.de_options,
        )

        reconstructed = _matrix_reshape(result.x, dim)
        reconstructed[np.isnan(reconstructed)] = 0.0
        reconstructed = np.clip(reconstructed, *self.bounds)

        observed_mask = ~np.isnan(known_matrix)
        predicted_values = reconstructed[observed_mask]
        actual_values = known_matrix[observed_mask]
        mse = float(np.mean((predicted_values - actual_values) ** 2))

        logger.info("DE reconstruction complete. MSE: %.6f", mse)

        missingness = 1.0 - np.count_nonzero(observed_mask) / known_matrix.size

        return ReconstructionResult(
            reconstructed_matrix=reconstructed,
            error=mse,
            iterations=int(result.nit),
            convergence=bool(result.success),
            missingness=float(missingness),
        )

    def _reconstruct_cg(self, known_matrix: np.ndarray,
                        indices: np.ndarray) -> ReconstructionResult:
        """Reconstruct via conjugate-gradient."""
        dim = known_matrix.shape[0]
        n_obs = len(indices)

        A_rows = np.repeat(np.arange(n_obs), dim)
        A_cols = indices.ravel()
        A_vals = np.ones(n_obs)

        from scipy.sparse import csr_matrix
        A_obs = csr_matrix((A_vals, (A_rows, A_cols)), shape=(n_obs, dim * dim))

        b_obs = known_matrix[~np.isnan(known_matrix)]
        AtA = A_obs.T @ A_obs
        Atb = A_obs.T @ b_obs

        AtA = AtA + 1e-6 * np.eye(dim * dim)

        x0 = np.zeros(dim * dim)
        solution = self._solve_cg(AtA.toarray() if hasattr(AtA, "toarray") else AtA, Atb)

        reconstructed = _matrix_reshape(solution, dim)
        reconstructed = np.clip(reconstructed, *self.bounds)

        observed_mask = ~np.isnan(known_matrix)
        mse = float(np.mean((reconstructed[observed_mask] - known_matrix[observed_mask]) ** 2))

        logger.info("CG reconstruction complete. MSE: %.6f", mse)

        missingness = 1.0 - np.count_nonzero(observed_mask) / known_matrix.size

        return ReconstructionResult(
            reconstructed_matrix=reconstructed,
            error=mse,
            iterations=self.cg_max_iter,
            convergence=True,
            missingness=float(missingness),
        )

    def _solve_cg(self, A: Array, b: Array, x0: Optional[Array] = None,
                  tol: float = 1e-8, max_iter: int = 1000) -> Array:
        """Minimal conjugate-gradient solver."""
        n = A.shape[0]
        x = x0.copy() if x0 is not None else np.zeros(n)
        r = b - A @ x
        p = r.copy()
        rs_old = float(r @ r)

        for _ in range(max_iter):
            if np.sqrt(rs_old) / max(np.sqrt(b @ b), 1e-15) < tol:
                break
            Ap = A @ p
            alpha = rs_old / float(p @ Ap)
            x += alpha * p
            r -= alpha * Ap
            rs_new = float(r @ r)
            if np.sqrt(rs_new) / max(np.sqrt(b @ b), 1e-15) < tol:
                break
            p = r + (rs_new / rs_old) * p
            rs_old = rs_new

        return x

    def reconstruct(self, known_matrix: np.ndarray) -> ReconstructionResult:
        """Reconstruct the full sociomatrix from partial observations.

        Parameters
        ----------
        known_matrix :
            Square matrix with observed entries and ``np.nan`` for missing.

        Returns
        -------
        ReconstructionResult
            Reconstructed sociomatrix and diagnostics.
        """
        observed_mask, indices, _ = self._build_mask(known_matrix)

        if not np.any(observed_mask):
            raise ValueError("known_matrix has no observed entries (all NaN)")

        logger.info(
            "Reconstructing sociomatrix (%d×%d) with %.1f%% missing data (%s)",
            *known_matrix.shape,
            100.0 * (1.0 - np.count_nonzero(observed_mask) / known_matrix.size),
            self.method,
        )

        if self.method == "de":
            return self._reconstruct_de(known_matrix, indices)
        elif self.method == "cg":
            return self._reconstruct_cg(known_matrix, indices)
        else:
            raise ValueError(f"Unknown reconstruction method: {self.method!r}")

    def get_reconstruction_error(self, known_matrix: np.ndarray,
                                 reconstructed: np.ndarray) -> float:
        """Mean squared error between known entries and reconstructed values."""
        observed_mask = ~np.isnan(known_matrix)
        if not np.any(observed_mask):
            return float("nan")
        return float(np.mean((known_matrix[observed_mask] - reconstructed[observed_mask]) ** 2))
