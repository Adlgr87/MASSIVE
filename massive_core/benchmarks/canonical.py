"""Small deterministic benchmarks for scientific MASSIVE modules.

These benchmarks use canonical synthetic systems only.  They are intended as
sanity checks for stability, tipping and network-reconstruction workflows before
any empirical calibration data is available.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from massive_core.diagnostics import build_scientific_report
from massive_core.network_inference import NetworkReconstructor
from massive_core.numerics import StabilityAnalyzer

Array = np.ndarray


def stable_fixed_point_benchmark(dt: float = 0.1, steps: int = 20) -> dict[str, Any]:
    """Benchmark a stable scalar fixed point ``dx/dt = -x``.

    Args:
        dt: Positive time step.
        steps: Number of updates.

    Returns:
        Serializable benchmark metrics.
    """

    trajectory = _simulate_scalar(lambda x: -x, x0=1.0, dt=dt, steps=steps)
    report = build_scientific_report(list(trajectory), dt=dt)
    stability = StabilityAnalyzer(lambda x: -x).analyze_linear_stability(np.array([0.0]))
    return {
        "name": "stable_fixed_point",
        "passed": report.stability_label == "stable" and stability.stable,
        "report": report.to_dict(),
        "max_real_eigenvalue": stability.max_real_eigenvalue,
    }


def unstable_fixed_point_benchmark(dt: float = 0.1, steps: int = 12) -> dict[str, Any]:
    """Benchmark an unstable scalar fixed point ``dx/dt = x``.

    Args:
        dt: Positive time step.
        steps: Number of updates.

    Returns:
        Serializable benchmark metrics.
    """

    trajectory = _simulate_scalar(lambda x: x, x0=0.1, dt=dt, steps=steps)
    report = build_scientific_report(list(trajectory), dt=dt)
    stability = StabilityAnalyzer(lambda x: x).analyze_linear_stability(np.array([0.0]))
    return {
        "name": "unstable_fixed_point",
        "passed": report.stability_label == "unstable" and not stability.stable,
        "report": report.to_dict(),
        "max_real_eigenvalue": stability.max_real_eigenvalue,
    }


def double_well_tipping_benchmark() -> dict[str, Any]:
    """Benchmark tipping detection with a synthetic double-well jump.

    Returns:
        Serializable benchmark metrics.
    """

    left_well = np.linspace(-0.9, -0.7, 8)
    right_well = np.linspace(0.7, 0.9, 8)
    trajectory = np.concatenate([left_well, right_well]).reshape(-1, 1)
    report = build_scientific_report(list(trajectory), dt=1.0, bins=6)
    return {
        "name": "double_well_tipping",
        "passed": len(report.tipping_indices) >= 1,
        "report": report.to_dict(),
        "tipping_indices": report.tipping_indices,
    }


def network_reconstruction_benchmark(threshold: float = 0.8) -> dict[str, Any]:
    """Benchmark correlation reconstruction on a known synthetic network.

    Args:
        threshold: Correlation threshold for reconstruction.

    Returns:
        Serializable precision/recall metrics.
    """

    t = np.linspace(0.0, 2.0 * np.pi, 100)
    trajectories = np.column_stack([
        np.sin(t),
        np.sin(t + 0.05),
        np.cos(t),
    ])
    expected = np.array([
        [0.0, 1.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
    ])
    adjacency = NetworkReconstructor().reconstruct_correlation_based(
        trajectories,
        threshold=threshold,
    )
    true_positive = float(np.sum((adjacency == 1.0) & (expected == 1.0)))
    false_positive = float(np.sum((adjacency == 1.0) & (expected == 0.0)))
    false_negative = float(np.sum((adjacency == 0.0) & (expected == 1.0)))
    precision = true_positive / max(true_positive + false_positive, 1.0)
    recall = true_positive / max(true_positive + false_negative, 1.0)
    return {
        "name": "network_reconstruction",
        "passed": precision >= 0.5 and recall >= 1.0,
        "precision": precision,
        "recall": recall,
        "adjacency": adjacency.tolist(),
    }


def run_canonical_benchmarks() -> dict[str, Any]:
    """Run all canonical benchmarks.

    Returns:
        Dictionary with per-benchmark results and aggregate status.
    """

    results = [
        stable_fixed_point_benchmark(),
        unstable_fixed_point_benchmark(),
        double_well_tipping_benchmark(),
        network_reconstruction_benchmark(),
    ]
    return {
        "passed": all(bool(result["passed"]) for result in results),
        "benchmarks": results,
    }


def _simulate_scalar(vector_field, x0: float, dt: float, steps: int) -> Array:
    state = float(x0)
    trajectory = [state]
    for _ in range(steps):
        state = state + dt * float(vector_field(np.array([state]))[0])
        trajectory.append(state)
    return np.asarray(trajectory, dtype=float).reshape(-1, 1)
