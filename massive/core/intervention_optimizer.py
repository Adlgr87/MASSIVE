"""Intervention optimization utilities for MASSIVE."""

from __future__ import annotations

from typing import Callable

import numpy as np


def _evaluate_candidate(
    evaluate_fn: Callable[[np.ndarray], float],
    candidate: np.ndarray,
) -> float:
    score = float(evaluate_fn(candidate))
    if not np.isfinite(score):
        return -np.inf
    return score


def optimize_interventions(
    evaluate_fn: Callable[[np.ndarray], float],
    n_agents: int,
    n_phases: int,
    max_iter: int = 100,
    seed: int = 42,
) -> dict:
    """Optimize interventions with stochastic search."""
    if n_agents <= 0 or n_phases <= 0:
        raise ValueError("n_agents and n_phases must be > 0")

    rng = np.random.default_rng(seed)
    best = rng.choice([-1.0, 1.0], size=(n_phases, n_agents)).astype(np.float64)
    best_score = _evaluate_candidate(evaluate_fn, best)

    for _ in range(max_iter):
        candidate = rng.choice([-1.0, 1.0], size=(n_phases, n_agents)).astype(
            np.float64
        )
        score = _evaluate_candidate(evaluate_fn, candidate)
        if score > best_score:
            best_score = score
            best = candidate

    return {
        "interventions": best,
        "score": float(best_score),
        "strategy": "stochastic_search",
    }
