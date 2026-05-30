"""Infer network structure from trajectories."""

from __future__ import annotations

import numpy as np

Array = np.ndarray


class NetworkReconstructor:
    """Reconstructs adjacency matrices from state time series."""

    def reconstruct_correlation_based(self, trajectories: Array, threshold: float = 0.3) -> Array:
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

    def reconstruct_transfer_entropy(self, trajectories: Array, lag: int = 1, bins: int = 10) -> Array:
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

    def reconstruct_granger_causality(self, trajectories: Array, max_lag: int = 5, alpha: float = 0.05) -> Array:
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
        return float(np.sum(residual**2))
