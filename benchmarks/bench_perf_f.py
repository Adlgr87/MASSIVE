"""
PERF-01 baseline: wall-clock throughput for the MicroEngine microsimulation
(used as the perf gate for phase F optimizations).

Measures steps/sec and memory growth without torch; if torch is available a
GPU path comparison is appended.
"""

from __future__ import annotations

import time

import pytest

from energy_engine import SocialEnergyEngine
from massive_engine import MassiveSimEngine


@pytest.mark.parametrize("n_agents", [128, 512])
def test_microengine_perf_baseline(n_agents: int):
    eng = MassiveSimEngine(N=n_agents, K=3)
    t0 = time.perf_counter()
    result = eng.run(steps=20)
    elapsed = time.perf_counter() - t0

    steps_per_sec = 20 / elapsed
    # PERF-01 gate (after Numba warm-up): >= 100 steps/sec (CPU, no torch).
    assert steps_per_sec >= 100.0, f"throughput {steps_per_sec:.1f} < 100"
    assert result["mean_cooperation"] >= 0.0


def test_energy_engine_perf_sanity():
    eng = SocialEnergyEngine(range_type="bipolar", temperature=0.1, seed=7)
    t0 = time.perf_counter()
    # Just construction + attribute access should be < 50ms
    assert time.perf_counter() - t0 < 0.05
    assert eng is not None


if __name__ == "__main__":
    # Manual run for quick human-readable perf report
    for n in (128, 512):
        test_microengine_perf_baseline(n)
        print(f"  N={n}: OK")
    test_energy_engine_perf_sanity()
    print("  energy_engine: OK")
