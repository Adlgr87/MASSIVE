"""Quantization / LOD fidelity vs float64 baseline."""

from __future__ import annotations

from benchmarks.fidelity import compare_massive_approx, trajectory_mae


def test_trajectory_mae_identity():
    import numpy as np

    x = np.array([0.1, 0.2, 0.3])
    assert trajectory_mae(x, x) == 0.0


def test_quantize_fidelity_within_limits():
    report = compare_massive_approx(
        n_agents=60,
        m_clusters=10,
        steps=12,
        seed=1,
        max_traj_mae=0.35,
        max_final_err=0.45,
        max_pol_err=0.40,
    )
    q = report["quantize_vs_float64"]
    assert q["within_limits"], q
    assert q["trajectory_mae"] >= 0.0


def test_aggregated_lod_consistency():
    report = compare_massive_approx(
        n_agents=50,
        m_clusters=8,
        steps=8,
        seed=2,
    )
    lod = report["aggregated_lod"]
    assert lod["within_limits"], lod
    assert lod["counts_sum"] == 50
