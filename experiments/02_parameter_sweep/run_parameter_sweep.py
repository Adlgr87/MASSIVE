#!/usr/bin/env python3
"""
FASE 4 — BARRIDO SISTEMÁTICO DE PARÁMETROS

Explora la sensibilidad del sistema a cada parámetro crítico y detecta
comportamientos no documentados, saturaciones, o singularidades.
"""
import sys, os, json, time, csv
import numpy as np
from itertools import product

REPO = "/home/adlg/Escritorio/Proyectos/MASSIVE"
sys.path.insert(0, REPO)
os.environ.setdefault("PYTHONHASHSEED", "42")

RESULTS = []

def run_simular_sweep(param_name, param_values, seeds=[42, 43, 44, 45, 46]):
    """Barrer un parámetro a través de simular() con múltiples seeds."""
    from simulator import simular

    for val in param_values:
        for seed in seeds:
            np.random.seed(seed)
            estado = {"opinion": 0.5, "propaganda": 0.3}

            cfg = {"proveedor": "heurístico", "ruido_base": 0.03, "hk_epsilon": 0.3}

            # Override del parámetro
            if param_name == "propaganda":
                estado["propaganda"] = val
            elif param_name == "alpha_blend":
                cfg["alpha_blend"] = val
            elif param_name == "ruido_base":
                cfg["ruido_base"] = val
            elif param_name == "hk_epsilon":
                cfg["hk_epsilon"] = val
            elif param_name == "homofilia_tasa":
                cfg["homofilia_tasa"] = val
            elif param_name == "umbral_media":
                cfg["umbral_media"] = val

            t0 = time.time()
            try:
                result = simular(estado, escenario="campana", pasos=50,
                                  cada_n_pasos=5, config=cfg, verbose=False)
                elapsed = (time.time() - t0) * 1000

                final = result[-1]
                opinions = [h["opinion"] for h in result]
                mean_final = np.mean(opinions[-5:])
                std_final = np.std(opinions[-5:])
                # Polarization index = std of final opinions
                pol_idx = std_final
                # Convergencia: std < 0.05 en últimos 5 pasos
                converged = std_final < 0.05

                RESULTS.append({
                    "motor": "simulator", "param": param_name,
                    "value": val, "seed": seed,
                    "mean_opinion_final": round(mean_final, 6),
                    "std_opinion_final": round(std_final, 6),
                    "polarization_index": round(pol_idx, 6),
                    "convergencia": converged,
                    "tiempo_ms": round(elapsed, 1)
                })
            except Exception as e:
                RESULTS.append({
                    "motor": "simulator", "param": param_name,
                    "value": val, "seed": seed,
                    "error": str(e)[:200], "tiempo_ms": 0
                })

def run_massive_sweep(param_name, param_values, seeds=[42, 43, 44, 45, 46]):
    """Barrer un parámetro a través de MassiveSimEngine."""
    from massive_engine import MassiveSimEngine

    for val in param_values:
        for seed in seeds:
            np.random.seed(seed)
            kwargs = {"N": 1000, "quantize": False, "event_driven": False, "seed": seed}

            if param_name == "layer_weights":
                # val es una tupla de 3
                kwargs["layer_weights"] = val
            elif param_name == "coupling":
                kwargs["coupling"] = val
            elif param_name == "sleep_threshold":
                kwargs["sleep_threshold"] = val
            else:
                # Parámetros que no aplican a MassiveSimEngine directamente
                pass

            t0 = time.time()
            try:
                engine = MassiveSimEngine(**kwargs)
                r = engine.run(steps=20)
                elapsed = (time.time() - t0) * 1000

                RESULTS.append({
                    "motor": "massive_engine", "param": param_name,
                    "value": str(val), "seed": seed,
                    "mean_opinion_final": round(r.get("mean_opinion", 0), 6),
                    "std_opinion_final": round(r.get("std_opinion", 0), 6),
                    "polarization_index": round(r.get("std_opinion", 0), 6),
                    "convergencia": r.get("std_opinion", 1) < 0.05,
                    "tiempo_ms": round(elapsed, 1)
                })
            except Exception as e:
                RESULTS.append({
                    "motor": "massive_engine", "param": param_name,
                    "value": str(val), "seed": seed,
                    "error": str(e)[:200], "tiempo_ms": 0
                })

def run_factorial_2k():
    """Diseño factorial 2^3 con 3 parámetros más influyentes."""
    from simulator import simular

    # factor_A: propaganda (bajo=0.1, alto=0.8)
    # factor_B: ruido_base (bajo=0.0, alto=0.2)
    # factor_C: hk_epsilon (bajo=0.1, alto=0.4)
    levels = {"A": (0.1, 0.8), "B": (0.0, 0.2), "C": (0.1, 0.4)}

    for a_idx, b_idx, c_idx in product([0, 1], repeat=3):
        a_val = levels["A"][a_idx]
        b_val = levels["B"][b_idx]
        c_val = levels["C"][c_idx]
        for seed in [42, 43, 44, 45, 46]:
            np.random.seed(seed)
            estado = {"opinion": 0.5, "propaganda": a_val}
            cfg = {"proveedor": "heurístico", "ruido_base": b_val, "hk_epsilon": c_val}

            t0 = time.time()
            try:
                result = simular(estado, pasos=50, cada_n_pasos=5,
                                  config=cfg, verbose=False)
                elapsed = (time.time() - t0) * 1000
                opinions = [h["opinion"] for h in result]
                mean_final = np.mean(opinions[-5:])
                std_final = np.std(opinions[-5:])

                RESULTS.append({
                    "motor": "factorial_2k", "param": "AxBxC",
                    "value": f"A={a_val},B={b_val},C={c_val}",
                    "seed": seed,
                    "mean_opinion_final": round(mean_final, 6),
                    "std_opinion_final": round(std_final, 6),
                    "factorial_A": a_val, "factorial_B": b_val, "factorial_C": c_val,
                    "tiempo_ms": round(elapsed, 1)
                })
            except Exception as e:
                RESULTS.append({
                    "motor": "factorial_2k", "param": "AxBxC",
                    "value": f"A={a_val},B={b_val},C={c_val}",
                    "seed": seed, "error": str(e)[:200], "tiempo_ms": 0
                })

# ============================================================================
# EJECUCIÓN
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("FASE 4 — BARRIDO SISTEMÁTICO DE PARÁMETROS")
    print("=" * 70)

    # 4.1 — Barrido de parámetros críticos
    print("\n[4.1] Barrido de parámetros críticos...")

    # propaganda: 0.0 → 1.0, 11 valores
    run_simular_sweep("propaganda", np.linspace(0.0, 1.0, 11))
    print(f"  propaganda: {len(RESULTS)} corridas acumuladas")

    # alpha_blend: 0.0 → 1.0, 11 valores
    run_simular_sweep("alpha_blend", np.linspace(0.0, 1.0, 11))
    print(f"  alpha_blend: {len(RESULTS)} corridas acumuladas")

    # ruido_base (sigma_base): 0.0 → 0.5, 11 valores
    run_simular_sweep("ruido_base", np.linspace(0.0, 0.5, 11))
    print(f"  ruido_base: {len(RESULTS)} corridas acumuladas")

    # hk_epsilon: 0.05 → 0.5, 10 valores
    run_simular_sweep("hk_epsilon", np.linspace(0.05, 0.5, 10))
    print(f"  hk_epsilon: {len(RESULTS)} corridas acumuladas")

    # homofilia_tasa: 0.0 → 1.0, 11 valores
    run_simular_sweep("homofilia_tasa", np.linspace(0.0, 1.0, 11))
    print(f"  homofilia_tasa: {len(RESULTS)} corridas acumuladas")

    # layer_weights: 9 combinaciones
    lw_combos = [(1, 0, 0), (0, 1, 0), (0, 0, 1),
                 (0.5, 0.5, 0), (0.5, 0, 0.5), (0, 0.5, 0.5),
                 (0.4, 0.3, 0.3), (0.33, 0.33, 0.34), (0.2, 0.4, 0.4)]
    run_massive_sweep("layer_weights", lw_combos)
    print(f"  layer_weights: {len(RESULTS)} corridas acumuladas")

    # 4.2 — Factorial 2^3
    print("\n[4.2] Diseño factorial 2^3...")
    run_factorial_2k()
    print(f"  factorial: {len(RESULTS)} corridas acumuladas")

    # Guardar JSON primero (más robusto)
    json_path = os.path.join(REPO, "experiments/02_parameter_sweep/parameter_sweep_results.json")
    with open(json_path, 'w') as f:
        json.dump(RESULTS, f, indent=2, default=str)

    # Guardar CSV: usar union de todas las keys
    csv_path = os.path.join(REPO, "experiments/02_parameter_sweep/parameter_sweep_results.csv")
    all_keys = set()
    for r in RESULTS:
        all_keys.update(r.keys())
    all_keys = sorted(all_keys)
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=all_keys)
        writer.writeheader()
        for r in RESULTS:
            row = {k: r.get(k, '') for k in all_keys}
            writer.writerow(row)

    print(f"\n{'='*70}")
    print(f"TOTAL: {len(RESULTS)} corridas")
    errors = len([r for r in RESULTS if "error" in r])
    print(f"Errores: {errors}")
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")
    print(f"{'='*70}")
