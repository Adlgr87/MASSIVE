"""Drop-in integration helpers for MASSIVE core modules."""

from __future__ import annotations

from typing import Callable

import numpy as np

from .quantum_optimizer import qaoa_optimize_interventions
from .tensor_network import compress_to_mps, decompress_from_mps


def quantum_optimize_interventions(
    evaluate_fn: Callable[[np.ndarray], float],
    n_agents: int,
    n_phases: int,
    max_iter: int = 100,
    force_classical: bool = False,
) -> dict:
    """Drop-in optimizer that auto-falls back to classical mode when needed."""
    return qaoa_optimize_interventions(
        evaluate_fn=evaluate_fn,
        n_agents=n_agents,
        n_phases=n_phases,
        max_iter=max_iter,
        force_classical=force_classical,
    )


def compress_agent_states(states: np.ndarray, max_bond_dim: int = 32) -> dict:
    """Compress agent-state matrix into an MPS-like payload."""
    return compress_to_mps(states, max_bond_dim=max_bond_dim)


def decompress_agent_states(mps_state: dict) -> np.ndarray:
    """Recover dense agent-state matrix from compressed payload."""
    return decompress_from_mps(mps_state)
