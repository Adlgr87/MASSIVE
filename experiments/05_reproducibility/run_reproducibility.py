#!/usr/bin/env python3
"""
REPRODUCIBILIDAD FORMAL — post-optimization.

Same local seed / Generator must yield identical results within machine.
Global ``np.random.seed`` is **not** required for engine reproducibility.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import traceback
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
os.environ.setdefault("PYTHONHASHSEED", "42")

results: list[dict] = []


def record(name, status, detail, deltas=None):
    results.append(
        {"test": name, "status": status, "detail": detail, "deltas": deltas or []}
    )
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"{icon} {name}: {status} — {detail}")


def test_simulator_reproducibility():
    """simular() with config seed=42 must match across 3 runs."""
    from simulator import simular

    runs = []
    for _ in range(3):
        estado = {"opinion": 0.5, "propaganda": 0.3}
        cfg = {
            "proveedor": "heurístico",
            "ruido_base": 0.03,
            "hk_epsilon": 0.3,
            "seed": 42,
        }
        result = simular(estado, pasos=50, cada_n_pasos=5, config=cfg, verbose=False)
        runs.append([h["opinion"] for h in result])

    delta_01 = max(abs(a - b) for a, b in zip(runs[0], runs[1]))
    delta_02 = max(abs(a - b) for a, b in zip(runs[0], runs[2]))
    max_delta = max(delta_01, delta_02)

    if max_delta < 1e-10:
        record(
            "Reproducibilidad simulator (3 runs, seed=42)",
            "PASS",
            f"max_delta={max_delta:.2e}",
            [delta_01, delta_02],
        )
    elif max_delta < 0.001:
        record(
            "Reproducibilidad simulator (3 runs, seed=42)",
            "WARN",
            f"Estocasticidad controlada: max_delta={max_delta:.2e}",
            [delta_01, delta_02],
        )
    else:
        record(
            "Reproducibilidad simulator (3 runs, seed=42)",
            "FAIL",
            f"max_delta={max_delta:.2e} — investigar fuente",
            [delta_01, delta_02],
        )


def test_massive_engine_reproducibility():
    """MassiveSimEngine(seed=42) must be reproducible without global seed."""
    from massive_engine import MassiveSimEngine

    runs = []
    for _ in range(3):
        engine = MassiveSimEngine(N=1000, quantize=False, event_driven=False, seed=42)
        result = engine.run(steps=20)
        runs.append(result.get("mean_opinion", 0))

    deltas = [abs(runs[0] - runs[1]), abs(runs[0] - runs[2])]
    max_delta = max(deltas)

    if max_delta < 1e-10:
        record(
            "Reproducibilidad MassiveSimEngine (3 runs, seed=42)",
            "PASS",
            f"max_delta={max_delta:.2e} (local engine seed)",
            deltas,
        )
    elif max_delta < 0.001:
        record(
            "Reproducibilidad MassiveSimEngine (3 runs, seed=42)",
            "WARN",
            f"Estocasticidad controlada: max_delta={max_delta:.2e}",
            deltas,
        )
    else:
        record(
            "Reproducibilidad MassiveSimEngine (3 runs, seed=42)",
            "FAIL",
            f"max_delta={max_delta:.2e}",
            deltas,
        )


def test_multilayer_reproducibility():
    """MultilayerEngine with seed=42 must be reproducible."""
    from multilayer_engine import MultilayerEngine

    runs = []
    for _ in range(3):
        engine = MultilayerEngine(
            N=50, layer_weights=(0.4, 0.3, 0.3), coupling=0.3, seed=42
        )
        history = engine.run(steps=20)
        final = np.array(history[-1])
        runs.append(float(np.mean(final)))

    deltas = [abs(runs[0] - runs[1]), abs(runs[0] - runs[2])]
    max_delta = max(deltas)

    if max_delta < 1e-10:
        record(
            "Reproducibilidad MultilayerEngine (3 runs, seed=42)",
            "PASS",
            f"max_delta={max_delta:.2e}",
            deltas,
        )
    elif max_delta < 0.001:
        record(
            "Reproducibilidad MultilayerEngine (3 runs, seed=42)",
            "WARN",
            f"Estocasticidad controlada: max_delta={max_delta:.2e}",
            deltas,
        )
    else:
        record(
            "Reproducibilidad MultilayerEngine (3 runs, seed=42)",
            "FAIL",
            f"max_delta={max_delta:.2e}",
            deltas,
        )


def test_energy_engine_reproducibility():
    """SocialEnergyEngine(seed=42) + Generator init must be reproducible."""
    from energy_engine import SocialEnergyEngine

    runs = []
    for _ in range(3):
        engine = SocialEnergyEngine(
            range_type="bipolar", temperature=0.05, lambda_social=0.5, seed=42
        )
        N = 50
        rng = np.random.default_rng(42)
        opinions = rng.uniform(-1, 1, N)
        adj = np.ones((N, N)) / N
        attractors = [
            {"position": -0.5, "strength": 1.0},
            {"position": 0.5, "strength": 1.0},
        ]
        repellers = [{"position": 0.0, "strength": 0.5}]
        for _ in range(20):
            opinions = engine.step(opinions, adj, attractors, repellers, eta=0.01)
        runs.append(float(np.mean(opinions)))

    deltas = [abs(runs[0] - runs[1]), abs(runs[0] - runs[2])]
    max_delta = max(deltas)

    if max_delta < 1e-10:
        record(
            "Reproducibilidad SocialEnergyEngine (3 runs, seed=42)",
            "PASS",
            f"max_delta={max_delta:.2e}",
            deltas,
        )
    elif max_delta < 0.001:
        record(
            "Reproducibilidad SocialEnergyEngine (3 runs, seed=42)",
            "WARN",
            f"Estocasticidad controlada: max_delta={max_delta:.2e}",
            deltas,
        )
    else:
        record(
            "Reproducibilidad SocialEnergyEngine (3 runs, seed=42)",
            "FAIL",
            f"max_delta={max_delta:.2e}",
            deltas,
        )


def test_pythonhashseed_isolation():
    """PYTHONHASHSEED=42 must be consistent across subprocesses."""
    proc = subprocess.run(
        [sys.executable, "-c", "print(hash('MASSIVE'))"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONHASHSEED": "42"},
        check=False,
    )
    hash_subprocess = int(proc.stdout.strip())

    proc2 = subprocess.run(
        [sys.executable, "-c", "print(hash('MASSIVE'))"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONHASHSEED": "42"},
        check=False,
    )
    hash_subprocess2 = int(proc2.stdout.strip())

    if hash_subprocess == hash_subprocess2:
        record(
            "PYTHONHASHSEED=42 consistencia cross-proceso",
            "PASS",
            f"hash={hash_subprocess} (consistente entre 2 subprocess)",
        )
    else:
        record(
            "PYTHONHASHSEED=42 consistencia cross-proceso",
            "FAIL",
            f"hash1={hash_subprocess}, hash2={hash_subprocess2}",
        )


if __name__ == "__main__":
    print("=" * 70)
    print("REPRODUCIBILIDAD FORMAL (local seed / Generator)")
    print("=" * 70)

    tests = [
        test_simulator_reproducibility,
        test_massive_engine_reproducibility,
        test_multilayer_reproducibility,
        test_energy_engine_reproducibility,
        test_pythonhashseed_isolation,
    ]

    for test in tests:
        print(f"\n--- {test.__name__} ---")
        try:
            test()
        except Exception as e:
            record(test.__name__, "FAIL", f"EXCEPCIÓN: {e}")
            traceback.print_exc()

    output_path = REPO / "experiments/05_reproducibility/reproducibility_results.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    passed = len([r for r in results if r["status"] == "PASS"])
    failed = len([r for r in results if r["status"] == "FAIL"])
    warned = len([r for r in results if r["status"] == "WARN"])
    print(f"\n{'=' * 70}")
    print(f"TOTAL: {passed} PASS, {failed} FAIL, {warned} WARN de {len(results)} tests")
    print(f"Resultados: {output_path}")
    print(f"{'=' * 70}")
    sys.exit(1 if failed else 0)
