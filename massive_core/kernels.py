"""Vectorized NumPy kernels for the hot paths of the simulation engines.

These three functions are the inner loop of the opinion dynamics: the social
potential gradient, the Langevin update, and the event-driven active mask.

Historical note: this module used to dispatch to an optional PyO3 Rust
extension, falling back to NumPy when it was absent. That extension was never
actually built by anything in the project: the build backend is setuptools
rather than maturin, so ``pip install -e .`` never produced it; no CI job or
Dockerfile ever invoked cargo; and the crate's ``[lib] path`` did not even
resolve. The NumPy path below is therefore the only code that has ever run,
and it is already fully vectorized (100k agents x 5D in ~4.5 ms). The
dual-path indirection was removed so that what you read here is what executes.
"""

from __future__ import annotations

import numpy as np


def multi_potential_gradient(x: np.ndarray) -> np.ndarray:
    """Return the multidimensional social potential gradient.

    Args:
        x: State matrix with shape ``(N, K)``.

    Returns:
        Gradient matrix with the same shape as ``x``.
    """
    arr = np.asarray(x, dtype=np.float64)
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

    Raises:
        TypeError: if ``agents`` is not a writable float64 ``ndarray``. This
            function mutates its argument and returns ``None``, so it cannot
            accept anything that would need converting: ``np.asarray(agents,
            dtype=np.float64)`` silently *copies* a float32 array or a list,
            the update lands on the throwaway copy, and the caller observes
            no change at all with no error raised. Converting the input is
            the caller's decision to make, explicitly.
    """
    if not isinstance(agents, np.ndarray):
        raise TypeError(
            "langevin_opinion_update_inplace mutates `agents` in place and so "
            f"requires a numpy ndarray, got {type(agents).__name__}."
        )
    if agents.dtype != np.float64:
        raise TypeError(
            "langevin_opinion_update_inplace requires a float64 `agents` array "
            f"(got {agents.dtype}); converting it here would write the update "
            "to a temporary copy and silently discard it. Convert explicitly "
            "with `agents.astype(np.float64)` and keep the result."
        )
    if not agents.flags.writeable:
        raise TypeError("langevin_opinion_update_inplace requires a writable `agents` array.")

    agents_arr = agents
    drift = np.asarray(drift_vector, dtype=np.float64)
    diffusion = np.asarray(diffusion_noise, dtype=np.float64)
    jumps = np.asarray(jump_values, dtype=np.float64)

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
    changed = np.abs(new - prev).max(axis=1) > threshold
    if changed.any():
        neighbor_active = adjacency[changed, :].sum(axis=0) > 0
    else:
        neighbor_active = np.zeros(prev.shape[0], dtype=bool)
    return changed | neighbor_active
