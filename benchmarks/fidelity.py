"""Fidelity metrics for approximate engines vs float64 baseline.

Compares quantized and aggregated-LOD MassiveSimEngine trajectories
against a dense float64 MultilayerEngine (or unquantized full-M engine).
"""

from __future__ import annotations

from typing import Any

import numpy as np


def trajectory_mae(a: np.ndarray, b: np.ndarray) -> float:
    """Mean absolute error between two 1-D trajectories (aligned length)."""
    x = np.asarray(a, dtype=float).ravel()
    y = np.asarray(b, dtype=float).ravel()
    n = min(len(x), len(y))
    if n == 0:
        return float("nan")
    return float(np.mean(np.abs(x[:n] - y[:n])))


def final_error(a: np.ndarray, b: np.ndarray) -> float:
    x = np.asarray(a, dtype=float).ravel()
    y = np.asarray(b, dtype=float).ravel()
    if len(x) == 0 or len(y) == 0:
        return float("nan")
    return float(abs(x[-1] - y[-1]))


def polarization_error(opinions_a: np.ndarray, opinions_b: np.ndarray) -> float:
    """Absolute difference of mean |opinion| (polarization index)."""
    pa = float(np.mean(np.abs(np.asarray(opinions_a, dtype=float))))
    pb = float(np.mean(np.abs(np.asarray(opinions_b, dtype=float))))
    return abs(pa - pb)


def compare_massive_approx(
    *,
    n_agents: int = 80,
    m_clusters: int = 12,
    steps: int = 15,
    seed: int = 0,
    max_traj_mae: float = 0.35,
    max_final_err: float = 0.40,
    max_pol_err: float = 0.35,
) -> dict[str, Any]:
    """
    Run baseline (no quantize, synthetic LOD) vs quantized and vs aggregated.

    Returns metrics and boolean ``within_limits`` flags for each approx mode.
    """
    from massive_engine import MassiveSimEngine

    # Baseline: synthetic LOD, float64 state (quantize=False)
    base = MassiveSimEngine(
        N=n_agents,
        M=m_clusters,
        quantize=False,
        event_driven=False,
        seed=seed,
    )
    base_res = base.run(steps=steps)
    base_hist = np.asarray(base_res["opinion_history"], dtype=float)
    base_op = np.asarray(base_res["cluster_opinions"], dtype=float)

    # Quantized approximation (same seed/LOD)
    quant = MassiveSimEngine(
        N=n_agents,
        M=m_clusters,
        quantize=True,
        event_driven=False,
        seed=seed,
    )
    quant_res = quant.run(steps=steps)
    quant_hist = np.asarray(quant_res["opinion_history"], dtype=float)
    quant_op = np.asarray(quant_res["cluster_opinions"], dtype=float)

    quant_metrics = {
        "trajectory_mae": trajectory_mae(base_hist, quant_hist),
        "final_error": final_error(base_hist, quant_hist),
        "polarization_error": polarization_error(base_op, quant_op),
    }
    quant_metrics["within_limits"] = (
        quant_metrics["trajectory_mae"] <= max_traj_mae
        and quant_metrics["final_error"] <= max_final_err
        and quant_metrics["polarization_error"] <= max_pol_err
    )

    # Aggregated LOD from micro agents vs synthetic baseline of same N/M
    rng = np.random.default_rng(seed)
    agents = rng.uniform(-0.5, 0.5, size=(n_agents, 5))
    agents[:, 1:] = np.clip(agents[:, 1:], 0.0, 1.0)
    agg = MassiveSimEngine(
        lod_mode="aggregated",
        agent_states=agents,
        M=m_clusters,
        quantize=False,
        event_driven=False,
        seed=seed,
    )
    # Comparable baseline: synthetic with same seed (different init → larger tol)
    syn = MassiveSimEngine(
        N=n_agents,
        M=m_clusters,
        quantize=False,
        event_driven=False,
        seed=seed,
    )
    agg_res = agg.run(steps=steps)
    syn_res = syn.run(steps=steps)
    agg_hist = np.asarray(agg_res["opinion_history"], dtype=float)
    syn_hist = np.asarray(syn_res["opinion_history"], dtype=float)

    # Aggregated is a different representation; check internal consistency:
    # counts sum to N and trajectory is finite.
    lod_metrics = {
        "counts_sum": int(agg._counts.sum()),
        "trajectory_finite": bool(np.all(np.isfinite(agg_hist))),
        "n_clusters": int(agg.M),
        "vs_synthetic_traj_mae": trajectory_mae(syn_hist, agg_hist),
    }
    lod_metrics["within_limits"] = (
        lod_metrics["counts_sum"] == n_agents
        and lod_metrics["trajectory_finite"]
        and lod_metrics["n_clusters"] == m_clusters
    )

    return {
        "quantize_vs_float64": quant_metrics,
        "aggregated_lod": lod_metrics,
        "limits": {
            "max_traj_mae": max_traj_mae,
            "max_final_err": max_final_err,
            "max_pol_err": max_pol_err,
        },
        "n_agents": n_agents,
        "m_clusters": m_clusters,
        "steps": steps,
        "seed": seed,
    }
