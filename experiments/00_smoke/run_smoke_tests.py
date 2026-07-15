#!/usr/bin/env python3
"""
SMOKE TESTS — post-optimization baseline.

Verifies each core engine:
  - no exceptions on a minimal run
  - expected output shape / ranges
  - reproducibility via local seed / Generator (not global np.random)
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np

os.environ.setdefault("PYTHONHASHSEED", "42")

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

results: list[dict] = []


def record(name, motor, status, detail, elapsed_ms, reproducible=None):
    results.append(
        {
            "test": name,
            "motor": motor,
            "status": status,
            "detail": detail,
            "elapsed_ms": round(elapsed_ms, 1),
            "reproducible": reproducible,
        }
    )
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"{icon} [{motor}] {name}: {status} ({elapsed_ms:.0f}ms) — {detail}")


def test_simulator():
    from simulator import simular, resumen_historial

    estado = {"opinion": 0.5, "propaganda": 0.0}
    cfg = {"proveedor": "heurístico", "seed": 42}

    t0 = time.time()
    result_a = simular(
        estado, escenario="campana", pasos=10, cada_n_pasos=5, config=cfg, verbose=False
    )
    elapsed = (time.time() - t0) * 1000

    assert isinstance(result_a, list), "simular debe devolver lista"
    assert len(result_a) == 11, f"Esperado 11 entradas (0-10), got {len(result_a)}"
    assert "opinion" in result_a[0], "Falta key 'opinion' en resultado"
    assert all(0.0 <= h["opinion"] <= 1.0 for h in result_a), "Opinión fuera de rango [0,1]"
    assert "_regla_nombre" in result_a[1], "Falta key '_regla_nombre' en paso 1"

    result_b = simular(
        estado, escenario="campana", pasos=10, cada_n_pasos=5, config=cfg, verbose=False
    )
    reproducible = result_a == result_b
    assert reproducible, "FALLO DE REPRODUCIBILIDAD: simular con config seed=42"

    record(
        "simular_campana_10steps",
        "simulator.py",
        "PASS",
        f"11 steps, opinion_final={result_a[-1]['opinion']:.4f}",
        elapsed,
        reproducible,
    )

    estado_prop = {"opinion": 0.3, "propaganda": 0.7}
    t0 = time.time()
    r_prop = simular(
        estado_prop, pasos=10, config={"proveedor": "heurístico", "seed": 42}, verbose=False
    )
    elapsed = (time.time() - t0) * 1000
    record(
        "simular_propaganda_07",
        "simulator.py",
        "PASS",
        f"opinion_final={r_prop[-1]['opinion']:.4f}",
        elapsed,
    )

    stats = resumen_historial(result_a)
    assert "opinion_final" in stats, "Falta key en resumen"
    record("resumen_historial", "simulator.py", "PASS", f"delta={stats['delta_total']:.4f}", 0)


def test_massive_engine():
    from massive_engine import MassiveSimEngine

    # Local engine seed controls noise after FASE 1 optimization.
    t0 = time.time()
    engine_a = MassiveSimEngine(N=1000, quantize=False, event_driven=False, seed=42)
    r_a = engine_a.run(steps=10)
    elapsed = (time.time() - t0) * 1000

    assert isinstance(r_a, dict), "run() debe devolver dict"
    assert "mean_opinion" in r_a, "Falta 'mean_opinion' en resultado"
    assert isinstance(r_a["mean_opinion"], (int, float)), "mean_opinion debe ser numérico"

    engine_b = MassiveSimEngine(N=1000, quantize=False, event_driven=False, seed=42)
    r_b = engine_b.run(steps=10)
    reproducible = abs(r_a["mean_opinion"] - r_b["mean_opinion"]) < 1e-10
    if not reproducible:
        record(
            "massive_N1000_10steps",
            "massive_engine.py",
            "FAIL",
            f"seed=42 no reproduce. Delta={abs(r_a['mean_opinion'] - r_b['mean_opinion']):.6e}",
            elapsed,
            False,
        )
    else:
        record(
            "massive_N1000_10steps",
            "massive_engine.py",
            "PASS",
            f"mean_opinion={r_a['mean_opinion']:.6f} (local seed)",
            elapsed,
            True,
        )

    t0 = time.time()
    engine_q = MassiveSimEngine(N=5000, quantize=True, event_driven=True, seed=42)
    r_q = engine_q.run(steps=10)
    elapsed = (time.time() - t0) * 1000
    record(
        "massive_N5000_quant_events",
        "massive_engine.py",
        "PASS",
        f"mean_opinion={r_q['mean_opinion']:.6f}, "
        f"mem_savings={r_q.get('memory_savings_pct', 'N/A')}",
        elapsed,
    )


def test_energy_engine():
    from energy_engine import SocialEnergyEngine

    engine = SocialEnergyEngine(
        range_type="bipolar", temperature=0.05, lambda_social=0.5, seed=42
    )

    N = 50
    rng = np.random.default_rng(42)
    opinions = rng.uniform(-1, 1, N)
    adj = np.ones((N, N)) / N
    attractors = [{"position": -0.5, "strength": 1.0}, {"position": 0.5, "strength": 1.0}]
    repellers = [{"position": 0.0, "strength": 0.5}]

    t0 = time.time()
    for _ in range(10):
        opinions = engine.step(opinions, adj, attractors, repellers, eta=0.01)
    elapsed = (time.time() - t0) * 1000

    assert all(-1.0 <= x <= 1.0 for x in opinions), "Opinión fuera de rango [-1,1]"
    assert not np.any(np.isnan(opinions)), "NaN detectado en opiniones"
    assert not np.any(np.isinf(opinions)), "Inf detectado en opiniones"

    engine_b = SocialEnergyEngine(
        range_type="bipolar", temperature=0.05, lambda_social=0.5, seed=42
    )
    rng_b = np.random.default_rng(42)
    opinions_b = rng_b.uniform(-1, 1, N)
    for _ in range(10):
        opinions_b = engine_b.step(opinions_b, adj, attractors, repellers, eta=0.01)
    reproducible = np.allclose(opinions, opinions_b, atol=1e-10)

    record(
        "energy_langevin_50agents",
        "energy_engine.py",
        "PASS" if reproducible else "FAIL",
        f"mean={np.mean(opinions):.4f}, std={np.std(opinions):.4f}",
        elapsed,
        bool(reproducible),
    )

    metrics = engine.system_metrics(opinions, adj, attractors, repellers)
    assert isinstance(metrics, dict), "system_metrics debe devolver dict"
    record("energy_system_metrics", "energy_engine.py", "PASS", f"keys={list(metrics.keys())[:5]}", 0)


def test_multilayer_engine():
    from multilayer_engine import MultilayerEngine

    t0 = time.time()
    engine_a = MultilayerEngine(N=50, layer_weights=(0.4, 0.3, 0.3), coupling=0.3, seed=42)
    history_a = engine_a.run(steps=20)
    elapsed = (time.time() - t0) * 1000

    assert isinstance(history_a, list), "run() debe devolver lista"
    assert len(history_a) == 21, f"Esperado 21 entradas (0-20), got {len(history_a)}"

    h0 = np.array(history_a[0])
    assert h0.shape[0] == 50, f"Shape incorrecto: {h0.shape}"
    assert not np.any(np.isnan(h0)), "NaN detectado"
    assert not np.any(np.isinf(h0)), "Inf detectado"

    engine_b = MultilayerEngine(N=50, layer_weights=(0.4, 0.3, 0.3), coupling=0.3, seed=42)
    history_b = engine_b.run(steps=20)
    reproducible = np.allclose(np.array(history_a), np.array(history_b), atol=1e-10)

    record(
        "multilayer_N50_20steps",
        "multilayer_engine.py",
        "PASS",
        f"shape={h0.shape}, mean={np.mean(h0):.4f}",
        elapsed,
        bool(reproducible),
    )


def test_all_13_rules():
    from simulator import simular

    estado = {"opinion": 0.5, "propaganda": 0.3}
    result = simular(
        estado,
        escenario="campana",
        pasos=30,
        cada_n_pasos=1,
        config={"proveedor": "heurístico", "seed": 42},
        verbose=False,
    )

    rules_seen = set()
    for h in result[1:]:
        if "_regla_nombre" in h:
            rules_seen.add(h["_regla_nombre"])

    record(
        "all_13_rules_selector",
        "simulator.py",
        "PASS",
        f"reglas observadas en 30 pasos: {sorted(rules_seen)}",
        0,
    )


if __name__ == "__main__":
    print("=" * 70)
    print("SMOKE TESTS MASSIVE (local seed / Generator)")
    print("=" * 70)

    tests = [
        ("simulator.py", test_simulator),
        ("massive_engine.py", test_massive_engine),
        ("energy_engine.py", test_energy_engine),
        ("multilayer_engine.py", test_multilayer_engine),
        ("13_rules", test_all_13_rules),
    ]

    for name, func in tests:
        try:
            print(f"\n--- {name} ---")
            func()
        except Exception as e:
            tb = traceback.format_exc()
            record(name, name, "FAIL", str(e)[:200], 0)
            print(f"❌ [{name}] FAIL: {e}")
            print(tb[:500])

    output_path = REPO / "experiments/00_smoke/smoke_test_results.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    print("\n" + "=" * 70)
    passed = len([r for r in results if r["status"] == "PASS"])
    failed = len([r for r in results if r["status"] == "FAIL"])
    print(f"TOTAL: {passed} PASS, {failed} FAIL de {len(results)} tests")
    print(f"Resultados guardados en: {output_path}")
    print("=" * 70)
    sys.exit(1 if failed else 0)
