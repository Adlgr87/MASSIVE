"""State compression helpers for large agent-state matrices."""

from __future__ import annotations

import numpy as np


def compress_agent_states(
    states: np.ndarray,
    max_bond_dim: int = 32,
    explained_variance: float = 0.99,
) -> dict:
    """Compress a 2D state matrix with truncated SVD."""
    arr = np.asarray(states, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError("states must be a 2D matrix")
    if max_bond_dim < 1:
        raise ValueError("max_bond_dim must be >= 1")

    mean = arr.mean(axis=0, keepdims=True)
    centered = arr - mean
    u, s, vt = np.linalg.svd(centered, full_matrices=False)

    if s.size == 0:
        rank = 1
    else:
        energy = np.cumsum(s**2)
        total = energy[-1]
        ratio = energy / max(total, 1e-12)
        rank = int(np.searchsorted(ratio, explained_variance) + 1)

    rank = max(1, min(rank, int(max_bond_dim), vt.shape[0]))

    left = u[:, :rank] * s[:rank]
    right = vt[:rank, :]

    original_values = arr.size
    compressed_values = left.size + right.size + mean.size

    return {
        "left": left,
        "right": right,
        "mean": mean,
        "shape": arr.shape,
        "rank": rank,
        "compression_ratio": float(original_values / max(1, compressed_values)),
    }


def decompress_agent_states(mps_state: dict) -> np.ndarray:
    """Decompress a matrix produced by `compress_agent_states`."""
    left = np.asarray(mps_state["left"], dtype=np.float64)
    right = np.asarray(mps_state["right"], dtype=np.float64)
    mean = np.asarray(mps_state["mean"], dtype=np.float64)
    target_shape = tuple(mps_state["shape"])

    reconstructed = left @ right + mean
    return reconstructed.reshape(target_shape)
