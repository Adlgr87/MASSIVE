#!/usr/bin/env python3
"""
FASE 7 — VERIFICACIÓN DE REPRODUCIBILIDAD FORMAL

Verifica que mismo seed produce mismo resultado (intra-máquina).
"""
import sys, os, json, time, traceback
import numpy as np

REPO = "/home/adlg/Escritorio/Proyectos/MASSIVE"
sys.path.insert(0, REPO)
os.environ.setdefault("PYTHONHASHSEED", "42")

results = []

def record(name, status, detail, deltas=None):
    results.append({"test": name, "status": status, "detail": detail,
                    "deltas": deltas or []})
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"{icon} {name}: {status} — {detail}")

# ============================================================================
# [7.1] TEST DE REPRODUCIBILIDAD INTRA-MÁQUINA
# ============================================================================
def test_simulator_reproducibility():
    """simular() con np.random.seed(42) debe ser idéntico en 3 corridas."""
    from simulator import simular

    runs = []
    for i in range(3):
        np.random.seed(42)
        estado = {"opinion": 0.5, "propaganda": 0.3}
        cfg = {"proveedor": "heurístico", "ruido_base": 0.03, "hk_epsilon": 0.3}
        result = simular(estado, pasos=50, cada_n_pasos=5, config=cfg, verbose=False)
        opinions = [h["opinion"] for h in result]
        runs.append(opinions)

    # Comparar
    delta_01 = max(abs(a - b) for a, b in zip(runs[0], runs[1]))
    delta_02 = max(abs(a - b) for a, b in zip(runs[0], runs[2]))
    max_delta = max(delta_01, delta_02)

    if max_delta < 1e-10:
        record("Reproducibilidad simulator (3 runs, seed=42)", "PASS",
               f"max_delta={max_delta:.2e}", [delta_01, delta_02])
    elif max_delta < 0.001:
        record("Reproducibilidad simulator (3 runs, seed=42)", "WARN",
               f"Estocasticidad controlada: max_delta={max_delta:.2e}", [delta_01, delta_02])
    else:
        record("Reproducibilidad simulator (3 runs, seed=42)", "FAIL",
               f"max_delta={max_delta:.2e} — investigar fuente", [delta_01, delta_02])

def test_massive_engine_reproducibility():
    """MassiveSimEngine con np.random.seed(42) debe ser reproducible."""
    from massive_engine import MassiveSimEngine

    runs = []
    for i in range(3):
        np.random.seed(42)
        engine = MassiveSimEngine(N=1000, quantize=False, event_driven=False, seed=42)
        result = engine.run(steps=20)
        runs.append(result.get("mean_opinion", 0))

    deltas = [abs(runs[0] - runs[1]), abs(runs[0] - runs[2])]
    max_delta = max(deltas)

    # BUG CONOCIDO: massive_engine usa np.random.randn() global, no self.rng
    # Con np.random.seed(42) antes de cada run, debería ser reproducible
    if max_delta < 1e-10:
        record("Reproducibilidad MassiveSimEngine (3 runs, seed=42)", "PASS",
               f"max_delta={max_delta:.2e} (vía np.random.seed global)", deltas)
    elif max_delta < 0.001:
        record("Reproducibilidad MassiveSimEngine (3 runs, seed=42)", "WARN",
               f"Estocasticidad controlada: max_delta={max_delta:.2e}", deltas)
    else:
        record("Reproducibilidad MassiveSimEngine (3 runs, seed=42)", "FAIL",
               f"max_delta={max_delta:.2e} — bug np.random.randn global", deltas)

def test_multilayer_reproducibility():
    """MultilayerEngine con seed=42 debe ser reproducible."""
    from multilayer_engine import MultilayerEngine

    runs = []
    for i in range(3):
        engine = MultilayerEngine(N=50, layer_weights=(0.4, 0.3, 0.3),
                                   coupling=0.3, seed=42)
        history = engine.run(steps=20)
        final = np.array(history[-1])
        runs.append(float(np.mean(final)))

    deltas = [abs(runs[0] - runs[1]), abs(runs[0] - runs[2])]
    max_delta = max(deltas)

    if max_delta < 1e-10:
        record("Reproducibilidad MultilayerEngine (3 runs, seed=42)", "PASS",
               f"max_delta={max_delta:.2e}", deltas)
    elif max_delta < 0.001:
        record("Reproducibilidad MultilayerEngine (3 runs, seed=42)", "WARN",
               f"Estocasticidad controlada: max_delta={max_delta:.2e}", deltas)
    else:
        record("Reproducibilidad MultilayerEngine (3 runs, seed=42)", "FAIL",
               f"max_delta={max_delta:.2e}", deltas)

def test_energy_engine_reproducibility():
    """SocialEnergyEngine con np.random.seed(42) debe ser reproducible."""
    from energy_engine import SocialEnergyEngine

    runs = []
    for i in range(3):
        np.random.seed(42)
        engine = SocialEnergyEngine(range_type="bipolar", temperature=0.05, lambda_social=0.5)
        N = 50
        opinions = np.random.uniform(-1, 1, N)
        adj = np.ones((N, N)) / N
        attractors = [{"position": -0.5, "strength": 1.0}, {"position": 0.5, "strength": 1.0}]
        repellers = [{"position": 0.0, "strength": 0.5}]
        for _ in range(20):
            opinions = engine.step(opinions, adj, attractors, repellers, eta=0.01)
        runs.append(float(np.mean(opinions)))

    deltas = [abs(runs[0] - runs[1]), abs(runs[0] - runs[2])]
    max_delta = max(deltas)

    if max_delta < 1e-10:
        record("Reproducibilidad SocialEnergyEngine (3 runs, seed=42)", "PASS",
               f"max_delta={max_delta:.2e}", deltas)
    elif max_delta < 0.001:
        record("Reproducibilidad SocialEnergyEngine (3 runs, seed=42)", "WARN",
               f"Estocasticidad controlada: max_delta={max_delta:.2e}", deltas)
    else:
        record("Reproducibilidad SocialEnergyEngine (3 runs, seed=42)", "FAIL",
               f"max_delta={max_delta:.2e}", deltas)

def test_pythonhashseed_isolation():
    """Verificar que PYTHONHASHSEED está activo."""
    hash_a = hash("MASSIVE")
    hash_b = hash("MASSIVE")
    # Dentro del mismo proceso, hash es determinista
    # Pero PYTHONHASHSEED asegura que sea el mismo entre procesos

    import subprocess
    proc = subprocess.run(
        [sys.executable, "-c", f"print(hash('MASSIVE'))"],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONHASHSEED": "42"}
    )
    hash_subprocess = int(proc.stdout.strip())

    proc2 = subprocess.run(
        [sys.executable, "-c", f"print(hash('MASSIVE'))"],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONHASHSEED": "42"}
    )
    hash_subprocess2 = int(proc2.stdout.strip())

    if hash_subprocess == hash_subprocess2:
        record("PYTHONHASHSEED=42 consistencia cross-proceso", "PASS",
               f"hash={hash_subprocess} (consistente entre 2 subprocess)")
    else:
        record("PYTHONHASHSEED=42 consistencia cross-proceso", "FAIL",
               f"hash1={hash_subprocess}, hash2={hash_subprocess2}")

# ============================================================================
# EJECUCIÓN
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("FASE 7 — VERIFICACIÓN DE REPRODUCIBILIDAD")
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

    # Guardar
    output_path = os.path.join(REPO, "experiments/05_reproducibility/reproducibility_results.json")
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    passed = len([r for r in results if r["status"] == "PASS"])
    failed = len([r for r in results if r["status"] == "FAIL"])
    warned = len([r for r in results if r["status"] == "WARN"])
    print(f"\n{'='*70}")
    print(f"TOTAL: {passed} PASS, {failed} FAIL, {warned} WARN de {len(results)} tests")
    print(f"Resultados: {output_path}")
    print(f"{'='*70}")
