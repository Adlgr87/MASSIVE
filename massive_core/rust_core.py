"""Optional Python wrappers for the PyO3/Maturin Rust core.

The project keeps the public Python API stable: callers use this module and get
Rust acceleration when the compiled ``massive_rust_core`` extension is installed,
or NumPy fallbacks otherwise.
"""

from __future__ import annotations

import importlib.util
from typing import Final

import numpy as np

_RUST_EXTENSION: Final[str] = "massive_rust_core"
RUST_CORE_AVAILABLE: Final[bool] = importlib.util.find_spec(_RUST_EXTENSION) is not None

if RUST_CORE_AVAILABLE:
    import massive_rust_core as _rust_core
else:  # pragma: no cover - exercised implicitly in environments without maturin builds
    _rust_core = None


def multi_potential_gradient(x: np.ndarray) -> np.ndarray:
    """Return the multidimensional social potential gradient.

    Args:
        x: State matrix with shape ``(N, K)``.

    Returns:
        Gradient matrix with the same shape as ``x``.
    """
    arr = np.asarray(x, dtype=np.float64)
    if _rust_core is not None:
        return np.asarray(_rust_core.multi_potential_gradient_rs(arr), dtype=np.float64)

    grad = np.zeros_like(arr)
    op = arr[:, 0]
    grad[:, 0] = 4.0 * op * (op * op - 0.49)
    if arr.shape[1] > 1:
        coop = arr[:, 1]
        align = 0.5 * (op + 1.0)
        grad[:, 1] = 2.0 * (coop - 0.8 * align)
    if arr.shape[1] > 2:
        hier = arr[:, 2]
        grad[:, 2] = -2.0 * hier * (1.0 - hier) * (2.0 * hier - 1.0)
    if arr.shape[1] > 3:
        grad[:, 3] = 0.5 * (arr[:, 3] - 0.5) * (1.0 + arr[:, 2])
    if arr.shape[1] > 4:
        grad[:, 4] = 0.3 * (arr[:, 4] - 0.5 - 0.2 * arr[:, 1])
    return grad


def langevin_opinion_update_inplace(
    agents: np.ndarray,
    drift_vector: np.ndarray,
    diffusion_noise: np.ndarray,
    jump_values: np.ndarray,
    dt: float,
    diffusion_sigma: float,
    x_min: float = -1.0,
    x_max: float = 1.0,
) -> None:
    """Apply a clipped Langevin opinion update in-place.

    Args:
        agents: Agent state matrix whose first column stores opinions.
        drift_vector: Drift term for each agent before multiplication by ``dt``.
        diffusion_noise: Wiener increments already scaled by ``sqrt(dt)``.
        jump_values: Lévy jump contribution per agent.
        dt: Integration step.
        diffusion_sigma: Diffusion coefficient.
        x_min: Minimum allowed opinion.
        x_max: Maximum allowed opinion.
    """
    agents_arr = np.asarray(agents, dtype=np.float64)
    drift = np.asarray(drift_vector, dtype=np.float64)
    diffusion = np.asarray(diffusion_noise, dtype=np.float64)
    jumps = np.asarray(jump_values, dtype=np.float64)

    if _rust_core is not None:
        _rust_core.langevin_opinion_update_inplace(
            agents_arr,
            drift,
            diffusion,
            jumps,
            float(dt),
            float(diffusion_sigma),
            float(x_min),
            float(x_max),
        )
        return

    updated = agents_arr[:, 0] + drift * dt + diffusion_sigma * diffusion + jumps
    agents_arr[:, 0] = np.clip(updated, x_min, x_max)


def active_mask_step(
    x_prev: np.ndarray,
    x_new: np.ndarray,
    adj: np.ndarray,
    threshold: float,
) -> np.ndarray:
    """Compute the next event-driven active mask.

    Args:
        x_prev: Previous state matrix.
        x_new: Updated state matrix.
        adj: Adjacency matrix used to reactivate changed neighbors.
        threshold: Maximum coordinate delta needed to mark an agent as changed.

    Returns:
        Boolean active mask for the next step.
    """
    prev = np.asarray(x_prev, dtype=np.float64)
    new = np.asarray(x_new, dtype=np.float64)
    adjacency = np.asarray(adj, dtype=np.float64)
    if _rust_core is not None:
        return np.asarray(_rust_core.active_mask_step_rs(prev, new, adjacency, float(threshold)), dtype=bool)

    changed = np.abs(new - prev).max(axis=1) > threshold
    if changed.any():
        neighbor_active = adjacency[changed, :].sum(axis=0) > 0
    else:
        neighbor_active = np.zeros(prev.shape[0], dtype=bool)
    return changed | neighbor_active
