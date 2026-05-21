"""Core diagnostic for butterfly-effect style divergence checks."""

from __future__ import annotations

import numpy as np
from scipy import sparse


def _to_dense_mean_adjacency(graphs: dict | None, n_agents: int) -> np.ndarray:
    if not graphs:
        return np.eye(n_agents, dtype=np.float64)
    mats: list[np.ndarray] = []
    for matrix in graphs.values():
        if sparse.issparse(matrix):
            arr = matrix.toarray()
        else:
            arr = np.asarray(matrix, dtype=np.float64)
        if arr.shape == (n_agents, n_agents):
            mats.append(arr)
    if not mats:
        return np.eye(n_agents, dtype=np.float64)
    mean_adj = np.mean(mats, axis=0)
    row_sums = mean_adj.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0.0] = 1.0
    return mean_adj / row_sums


def run_butterfly_diagnostic_core(
    current_state_snapshot: dict,
    *,
    epsilon: float = 1e-4,
    steps: int = 8,
) -> dict[str, float]:
    """
    Estimates finite-time divergence from a tiny perturbation in current state.
    """
    agents = np.asarray(current_state_snapshot.get("agents"), dtype=np.float64)
    if agents.ndim != 2 or agents.shape[0] < 2:
        return {"divergence_score": 0.0, "max_distance": 0.0}

    opinions = np.clip(agents[:, 0], -1.0, 1.0)
    n_agents = opinions.shape[0]
    adjacency = _to_dense_mean_adjacency(current_state_snapshot.get("graphs"), n_agents)
    horizon = int(max(1, min(steps, int(current_state_snapshot.get("n_ticks_left", steps)))))

    base = opinions.copy()
    shadow = opinions.copy()
    pivot = int(np.argmin(np.abs(opinions - np.median(opinions))))
    shadow[pivot] = np.clip(shadow[pivot] + epsilon, -1.0, 1.0)

    d0 = np.linalg.norm(shadow - base) + 1e-12
    growth_logs: list[float] = []
    max_distance = d0

    for _ in range(horizon):
        base = np.clip(0.85 * base + 0.15 * (adjacency @ base) + 0.05 * np.tanh(base), -1.0, 1.0)
        shadow = np.clip(0.85 * shadow + 0.15 * (adjacency @ shadow) + 0.05 * np.tanh(shadow), -1.0, 1.0)
        dist = np.linalg.norm(shadow - base) + 1e-12
        growth_logs.append(np.log(dist / d0))
        max_distance = max(max_distance, dist)
        d0 = dist

    divergence = float(max(0.0, np.mean(growth_logs))) if growth_logs else 0.0
    return {"divergence_score": divergence, "max_distance": float(max_distance)}
