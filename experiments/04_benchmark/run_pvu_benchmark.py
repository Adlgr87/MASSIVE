#!/usr/bin/env python3
"""
FASE 6 — BENCHMARKS FORMALES PVU-BS

Ejecuta el runner de benchmarks existente en modo offline y captura métricas.
"""
import sys, os, json, time, subprocess, traceback
import numpy as np

REPO = "/home/adlg/Escritorio/Proyectos/MASSIVE"
sys.path.insert(0, REPO)
os.environ.setdefault("PYTHONHASHSEED", "42")

results = {"phase": "FASE 6 - PVU-BS", "runs": [], "summary": {}}

# ============================================================================
# [6.1] EJECUCIÓN DEL RUNNER EXISTENTE
# ============================================================================
def run_pvu_runner():
    """Ejecutar benchmarks/runner.py en modo offline."""
    print("\n[6.1] Ejecutando benchmarks/runner.py en modo offline...")

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(REPO, f"reports/validation/run_{timestamp}")

    # Probar CLI del runner
    cmd = [
        sys.executable, "-m", "benchmarks.runner",
        "--cases", "datasets/pvu_cases",
        "--offline",
        "--out", output_dir,
        "--seed", "42",
    ]

    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
            cwd=REPO, env={**os.environ, "PYTHONHASHSEED": "42"}
        )
        elapsed = (time.time() - t0) * 1000

        run_data = {
            "run_id": f"pvu_{timestamp}",
            "seed": 42,
            "provider": "heurístico (offline)",
            "command": " ".join(cmd),
            "exit_code": proc.returncode,
            "elapsed_ms": round(elapsed, 1),
            "stdout": proc.stdout[-2000:] if len(proc.stdout) > 2000 else proc.stdout,
            "stderr": proc.stderr[-1000:] if len(proc.stderr) > 1000 else proc.stderr,
        }

        if proc.returncode == 0:
            run_data["status"] = "PASS"
            print(f"  ✅ Runner completado en {elapsed:.0f}ms")
        else:
            run_data["status"] = "FAIL"
            print(f"  ❌ Runner falló (exit={proc.returncode})")
            print(f"  stderr: {proc.stderr[:500]}")

    except Exception as e:
        run_data = {
            "run_id": f"pvu_{timestamp}", "status": "ERROR",
            "error": str(e)[:500], "elapsed_ms": (time.time() - t0) * 1000
        }
        print(f"  ❌ Excepción: {e}")

    results["runs"].append(run_data)

    # Si el runner CLI falla, ejecutar directamente via Python
    if run_data.get("status") != "PASS":
        print("\n  Intentando ejecución directa via Python API...")
        try:
            from benchmarks.runner import main as runner_main
            t0 = time.time()
            output = runner_main()
            elapsed = (time.time() - t0) * 1000
            run_data2 = {
                "run_id": f"pvu_direct_{timestamp}",
                "seed": 42, "provider": "heurístico (offline)",
                "method": "python_api_direct",
                "status": "PASS" if output else "PARTIAL",
                "elapsed_ms": round(elapsed, 1),
                "output": str(output)[:2000],
            }
            results["runs"].append(run_data2)
            print(f"  ✅ Ejecución directa completada en {elapsed:.0f}ms")
        except Exception as e:
            print(f"  ❌ Ejecución directa también falló: {e}")
            results["runs"].append({
                "run_id": f"pvu_direct_{timestamp}",
                "status": "ERROR", "error": str(e)[:500]
            })

# ============================================================================
# [6.2] BENCHMARK MANUAL CON MÉTRICAS COMPLETAS
# ============================================================================
def run_manual_benchmark():
    """Ejecutar benchmark manual con captura de métricas detalladas."""
    print("\n[6.2] Benchmark manual con métricas completas...")

    from simulator import simular
    from massive_engine import MassiveSimEngine
    from multilayer_engine import MultilayerEngine

    benchmark_configs = [
        # (motor, config, N_steps)
        ("simulator_lineal", {
            "estado": {"opinion": 0.5, "propaganda": 0.3},
            "cfg": {"proveedor": "heurístico", "ruido_base": 0.03},
            "pasos": 50
        }),
        ("simulator_hk", {
            "estado": {"opinion": 0.5, "propaganda": 0.3},
            "cfg": {"proveedor": "heurístico", "hk_epsilon": 0.2, "ruido_base": 0.03},
            "pasos": 50
        }),
        ("massive_engine_N10k", {
            "N": 10000, "quantize": True, "event_driven": True,
            "seed": 42, "steps": 20
        }),
        ("multilayer_engine", {
            "N": 100, "layer_weights": (0.4, 0.3, 0.3),
            "coupling": 0.3, "seed": 42, "steps": 50
        }),
    ]

    for name, config in benchmark_configs:
        np.random.seed(42)
        t0 = time.time()

        try:
            if name.startswith("simulator"):
                result = simular(config["estado"], pasos=config["pasos"],
                                  cada_n_pasos=5, config=config["cfg"], verbose=False)
                opinions = [h["opinion"] for h in result]
                mean_final = np.mean(opinions[-5:])
                std_final = np.std(opinions[-5:])
                pol_idx = std_final
                # Regime changes
                regime_changes = len(set(h.get("_regla_nombre", "") for h in result[1:]))
                # Convergence step
                conv_step = -1
                for i in range(len(opinions)-5):
                    if np.std(opinions[i:i+5]) < 0.05:
                        conv_step = i
                        break

            elif name.startswith("massive"):
                engine = MassiveSimEngine(N=config["N"], quantize=config["quantize"],
                                           event_driven=config["event_driven"], seed=config["seed"])
                result = engine.run(steps=config["steps"])
                mean_final = result.get("mean_opinion", 0)
                std_final = result.get("std_opinion", 0)
                pol_idx = std_final
                regime_changes = 0  # N/A for massive engine
                conv_step = -1

            elif name.startswith("multilayer"):
                engine = MultilayerEngine(N=config["N"], layer_weights=config["layer_weights"],
                                           coupling=config["coupling"], seed=config["seed"])
                history = engine.run(steps=config["steps"])
                arr = np.array(history[-1])
                mean_final = float(np.mean(arr))
                std_final = float(np.std(arr))
                pol_idx = std_final
                regime_changes = 0
                conv_step = -1

            elapsed = (time.time() - t0) * 1000
            import psutil
            mem_mb = psutil.Process().memory_info().rss / 1024 / 1024

            run_data = {
                "run_id": f"manual_{name}_{int(time.time())}",
                "motor": name, "seed": 42,
                "provider": "heurístico (offline)",
                "N": config.get("N", 1), "steps": config.get("steps", config.get("pasos", 0)),
                "mean_opinion_final": round(mean_final, 6),
                "std_opinion_final": round(std_final, 6),
                "polarization_index": round(pol_idx, 6),
                "n_regime_changes": regime_changes,
                "convergencia_step": conv_step,
                "tiempo_ejecucion_ms": round(elapsed, 1),
                "memory_peak_MB": round(mem_mb, 1),
            }
            results["runs"].append(run_data)
            print(f"  ✅ {name}: mean={mean_final:.4f}, std={std_final:.4f}, {elapsed:.0f}ms, {mem_mb:.0f}MB")

        except Exception as e:
            elapsed = (time.time() - t0) * 1000
            results["runs"].append({
                "run_id": f"manual_{name}_{int(time.time())}",
                "motor": name, "status": "ERROR",
                "error": str(e)[:300], "tiempo_ejecucion_ms": round(elapsed, 1)
            })
            print(f"  ❌ {name}: {e}")

# ============================================================================
# [6.3] TESTS ESTADÍSTICOS
# ============================================================================
def run_statistical_tests():
    """Comparar reglas hk vs lineal con test de Wilcoxon."""
    print("\n[6.3] Tests estadísticos (Wilcoxon)...")

    from simulator import simular
    from scipy.stats import wilcoxon

    # Recolectar 20 runs para cada regla
    hk_final_opinions = []
    lineal_final_opinions = []

    for seed in range(42, 62):
        np.random.seed(seed)
        estado = {"opinion": 0.5, "propaganda": 0.3}

        # HK
        cfg_hk = {"proveedor": "heurístico", "hk_epsilon": 0.2, "ruido_base": 0.03}
        result_hk = simular(estado, pasos=50, config=cfg_hk, verbose=False)
        hk_final_opinions.append(result_hk[-1]["opinion"])

        # Lineal
        np.random.seed(seed)
        cfg_lin = {"proveedor": "heurístico", "ruido_base": 0.03}
        result_lin = simular(estado, pasos=50, config=cfg_lin, verbose=False)
        lineal_final_opinions.append(result_lin[-1]["opinion"])

    # Wilcoxon signed-rank test
    try:
        stat, p_value = wilcoxon(hk_final_opinions, lineal_final_opinions)
        # Effect size: ΔMAE
        delta_mae = np.mean(np.abs(np.array(hk_final_opinions) - np.array(lineal_final_opinions)))
        delta_rmse = np.sqrt(np.mean((np.array(hk_final_opinions) - np.array(lineal_final_opinions))**2))

        stat_data = {
            "test": "Wilcoxon signed-rank",
            "comparison": "hk_vs_lineal",
            "n_runs": 20,
            "statistic": round(stat, 4),
            "p_value": round(p_value, 6),
            "significant": p_value < 0.05,
            "delta_MAE": round(delta_mae, 6),
            "delta_RMSE": round(delta_rmse, 6),
            "hk_mean": round(np.mean(hk_final_opinions), 6),
            "lineal_mean": round(np.mean(lineal_final_opinions), 6),
        }
        results["statistical_tests"] = stat_data
        print(f"  ✅ Wilcoxon: stat={stat:.4f}, p={p_value:.6f}, "
              f"significant={p_value < 0.05}, ΔMAE={delta_mae:.4f}")
    except Exception as e:
        print(f"  ❌ Wilcoxon falló: {e}")
        results["statistical_tests"] = {"error": str(e)[:300]}

# ============================================================================
# EJECUCIÓN
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("FASE 6 — BENCHMARKS FORMALES PVU-BS")
    print("=" * 70)

    print("\n⚠️  ADVERTENCIA: Los casos en datasets/pvu_cases/ son SINTÉTICOS.")
    print("   Esto es pipeline test, no evidencia empírica real.")

    run_pvu_runner()
    run_manual_benchmark()
    run_statistical_tests()

    # Summary
    passed = len([r for r in results["runs"] if r.get("status") == "PASS" or r.get("mean_opinion_final") is not None])
    failed = len([r for r in results["runs"] if r.get("status") in ("FAIL", "ERROR")])
    results["summary"] = {
        "total_runs": len(results["runs"]),
        "passed": passed, "failed": failed,
        "cases_synthetic": True,
        "note": "Todos los casos PVU son sintéticos. No hay validación empírica real."
    }

    output_path = os.path.join(REPO, "experiments/04_benchmark/pvu_bs_results.json")
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n{'='*70}")
    print(f"TOTAL: {passed} PASS, {failed} FAIL de {len(results['runs'])} runs")
    print(f"Resultados: {output_path}")
    print(f"{'='*70}")
