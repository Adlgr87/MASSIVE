#!/usr/bin/env python3
"""Profile-guided hotspot helper (B16).

Runs a short multilayer + energy workload under ``cProfile`` and prints the
top cumulative functions. Use before proposing micro-optimizations or Rust
ports.

Usage:
    PYTHONHASHSEED=42 python scripts/profile_hotspot.py
    PYTHONHASHSEED=42 python scripts/profile_hotspot.py --top 30
"""

from __future__ import annotations

import argparse
import cProfile
import pstats
import sys
from io import StringIO
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _workload() -> None:
    import numpy as np
    from energy_engine import SocialEnergyEngine
    from multilayer_engine import MultilayerEngine

    eng = MultilayerEngine(N=80, layer_weights=(0.4, 0.3, 0.3), coupling=0.3, seed=42)
    eng.run(steps=40)

    se = SocialEnergyEngine(range_type="bipolar", temperature=0.05, seed=42)
    n = 100
    rng = np.random.default_rng(42)
    opinions = rng.uniform(-1, 1, n)
    adj = np.ones((n, n)) / n
    attractors = [{"position": -0.5, "strength": 1.0}, {"position": 0.5, "strength": 1.0}]
    repellers = [{"position": 0.0, "strength": 0.3}]
    for _ in range(50):
        opinions = se.step(opinions, adj, attractors, repellers, eta=0.01)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=int, default=25, help="Top rows to print")
    args = parser.parse_args()

    profiler = cProfile.Profile()
    profiler.enable()
    _workload()
    profiler.disable()

    stream = StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats("cumulative")
    stats.print_stats(args.top)
    print(stream.getvalue())
    print(
        "Hint: prefer optimizing pure array loops that dominate cumulative time; "
        "see docs/rust_core_plan_ES.md before proposing Rust ports."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
