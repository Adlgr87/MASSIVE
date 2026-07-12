#!/usr/bin/env python3
"""
FASE 3 — VALIDACIÓN DE INVARIANTES MATEMÁTICOS

Verifica que el sistema obedece propiedades matemáticas conocidas a priori
desde la literatura académica.
"""
import sys, os, json, time, traceback
import numpy as np

REPO = "/home/adlg/Escritorio/Proyectos/MASSIVE"
sys.path.insert(0, REPO)
os.environ.setdefault("PYTHONHASHSEED", "42")

results = []

def record(name, status, detail, delta="N/A"):
    results.append({"invariante": name, "resultado": status,
                    "delta_observado": str(delta), "detail": detail})
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"{icon} {name}: {status} — {detail} (delta={delta})")

# ============================================================================
# [3.1] CONSERVACIÓN DE RANGO
# ============================================================================
def test_rango_unipolar():
    """Todas las reglas deben mantener opinión en [0, 1] en rango unipolar."""
    from simulator import (regla_lineal, regla_umbral, regla_memoria,
                            regla_backlash, regla_polarizacion, regla_hk,
                            regla_contagio_competitivo, regla_umbral_heterogeneo,
                            regla_homofilia, regla_replicador)
    from massive.core.extended_models import regla_nash, regla_bayesiana, regla_sir

    cfg_u = {"rango": "[0, 1] — Probabilístico", "hk_epsilon": 0.3,
             "ruido_base": 0.0, "alpha_blend": 0.8}

    reglas = [
        ("lineal", regla_lineal, {"a": 0.7, "b": 0.3}),
        ("umbral", regla_umbral, {"umbral": 0.5, "incremento": 0.15}),
        ("memoria", regla_memoria, {"lambda": 0.3}),
        ("backlash", regla_backlash, {"penalizacion": 0.15}),
        ("polarizacion", regla_polarizacion, {"fuerza": 0.1}),
        ("hk", regla_hk, {"epsilon": 0.3}),
        ("contagio_comp", regla_contagio_competitivo, {"beta_a": 0.3, "beta_b": 0.2}),
        ("umbral_hetero", regla_umbral_heterogeneo, {"umbral_media": 0.25}),
        ("homofilia", regla_homofilia, {"tasa": 0.05}),
        ("replicador", regla_replicador, {"fitness_coop": 1.2, "fitness_def": 0.8}),
        ("nash", regla_nash, {"c_same": 1.0, "c_diff": 0.0, "intensity": 0.3}),
        ("bayesiana", regla_bayesiana, {"confianza": 0.5}),
        ("sir", regla_sir, {"beta": 0.3, "gamma": 0.1, "dt": 0.2}),
    ]

    failures = []
    for nombre, regla, params in reglas:
        np.random.seed(42)
        estado = {"opinion": 0.5, "propaganda": 0.7,
                  "opinion_grupo_a": 0.8, "opinion_grupo_b": 0.2,
                  "pertenencia_grupo": 0.6, "historial": [0.5]}
        for step in range(100):
            try:
                estado = regla(estado, params, cfg_u)
                val = estado["opinion"]
                if not (0.0 <= val <= 1.0):
                    failures.append(f"{nombre}: step {step}, opinion={val:.4f} fuera de [0,1]")
                    break
            except Exception as e:
                failures.append(f"{nombre}: EXCEPCIÓN: {e}")
                break

    if failures:
        record("Conservación rango [0,1] (unipolar)", "FAIL",
               f"{len(failures)} violaciones: {failures[:3]}")
    else:
        record("Conservación rango [0,1] (unipolar)", "PASS",
               f"13 reglas × 100 pasos = 1300 evaluaciones sin violaciones")

def test_rango_bipolar():
    """Todas las reglas deben mantener opinión en [-1, 1] en rango bipolar."""
    from simulator import (regla_lineal, regla_umbral, regla_memoria,
                            regla_backlash, regla_polarizacion, regla_hk,
                            regla_contagio_competitivo, regla_umbral_heterogeneo,
                            regla_homofilia, regla_replicador)
    from massive.core.extended_models import regla_nash, regla_bayesiana, regla_sir

    cfg_b = {"rango": "[-1, 1] — Bipolar", "hk_epsilon": 0.3,
             "ruido_base": 0.0, "alpha_blend": 0.8}

    reglas = [
        ("lineal", regla_lineal, {"a": 0.7, "b": 0.3}),
        ("umbral", regla_umbral, {"umbral": 0.4, "incremento": 0.15}),
        ("memoria", regla_memoria, {"lambda": 0.3}),
        ("backlash", regla_backlash, {"penalizacion": 0.15}),
        ("polarizacion", regla_polarizacion, {"fuerza": 0.1}),
        ("hk", regla_hk, {"epsilon": 0.3}),
        ("contagio_comp", regla_contagio_competitivo, {"beta_a": 0.3, "beta_b": 0.2}),
        ("umbral_hetero", regla_umbral_heterogeneo, {"umbral_media": 0.25}),
        ("homofilia", regla_homofilia, {"tasa": 0.05}),
        ("replicador", regla_replicador, {"fitness_coop": 1.2, "fitness_def": 0.8}),
        ("nash", regla_nash, {"c_same": 1.0, "c_diff": 0.0, "intensity": 0.3}),
        ("bayesiana", regla_bayesiana, {"confianza": 0.5}),
        ("sir", regla_sir, {"beta": 0.3, "gamma": 0.1, "dt": 0.2}),
    ]

    failures = []
    for nombre, regla, params in reglas:
        np.random.seed(42)
        estado = {"opinion": 0.0, "propaganda": 0.5,
                  "opinion_grupo_a": 0.8, "opinion_grupo_b": -0.8,
                  "pertenencia_grupo": 0.5, "historial": [0.0]}
        for step in range(100):
            try:
                estado = regla(estado, params, cfg_b)
                val = estado["opinion"]
                if not (-1.0 <= val <= 1.0):
                    failures.append(f"{nombre}: step {step}, opinion={val:.4f} fuera de [-1,1]")
                    break
            except Exception as e:
                failures.append(f"{nombre}: EXCEPIÓN: {e}")
                break

    if failures:
        record("Conservación rango [-1,1] (bipolar)", "FAIL",
               f"{len(failures)} violaciones: {failures[:3]}")
    else:
        record("Conservación rango [-1,1] (bipolar)", "PASS",
               f"13 reglas × 100 pasos = 1300 evaluaciones sin violaciones")

# ============================================================================
# [3.2] CONVERGENCIA DE DEGROOT (regla "lineal")
# ============================================================================
def test_degrool_convergence():
    """DeGroot con propaganda constante debe converger a punto fijo."""
    from simulator import regla_lineal

    cfg = {"rango": "[0, 1] — Probabilístico", "ruido_base": 0.0}
    params = {"a": 0.7, "b": 0.3}
    estado = {"opinion": 0.5, "propaganda": 0.8,
              "opinion_grupo_a": 0.8, "opinion_grupo_b": 0.2,
              "pertenencia_grupo": 0.6, "historial": [0.5]}

    opinions = [estado["opinion"]]
    for _ in range(500):
        estado = regla_lineal(estado, params, cfg)
        opinions.append(estado["opinion"])

    final_std = np.std(opinions[-50:])
    # Punto fijo teórico: o* = b*prop / (1 - a) = 0.3*0.8 / 0.3 = 0.8
    fixed_point = 0.3 * 0.8 / (1 - 0.7)
    final_mean = np.mean(opinions[-10:])

    if final_std < 0.001 and abs(final_mean - fixed_point) < 0.01:
        record("Convergencia DeGroot (lineal)", "PASS",
               f"std_final={final_std:.6f}, fixed_point={fixed_point:.4f}, "
               f"observed={final_mean:.4f}", final_std)
    else:
        record("Convergencia DeGroot (lineal)", "FAIL",
               f"std_final={final_std:.6f} (esperado <0.001), "
               f"fixed_point={fixed_point:.4f}, observed={final_mean:.4f}", final_std)

# ============================================================================
# [3.3] CLUSTERING HEGSELMANN-KRAUSE (regla "hk")
# ============================================================================
def test_hk_clustering():
    """HK con epsilon pequeño debe mantener clusters separados;
    con epsilon=1.0 debe converger a consenso."""
    from simulator import regla_hk

    cfg = {"rango": "[0, 1] — Probabilístico", "ruido_base": 0.0}

    # Épsilon pequeño: opinion cerca de grupo_a no debe saltar a grupo_b
    estado_small = {"opinion": 0.7, "propaganda": 0.0,
                     "opinion_grupo_a": 0.8, "opinion_grupo_b": 0.2,
                     "pertenencia_grupo": 0.6, "historial": [0.7]}
    params_small = {"epsilon": 0.1, "alpha": 0.3}
    for _ in range(100):
        estado_small = regla_hk(estado_small, params_small, cfg)

    # Con epsilon=0.1, opinion debería acercarse a grupo_a (0.8) pero no a grupo_b (0.2)
    stayed_near_a = abs(estado_small["opinion"] - 0.8) < abs(estado_small["opinion"] - 0.2)

    # Épsilon grande: debe converger hacia consenso entre ambos grupos
    estado_large = {"opinion": 0.5, "propaganda": 0.0,
                     "opinion_grupo_a": 0.8, "opinion_grupo_b": 0.2,
                     "pertenencia_grupo": 0.5, "historial": [0.5]}
    params_large = {"epsilon": 1.0, "alpha": 0.3}
    for _ in range(100):
        estado_large = regla_hk(estado_large, params_large, cfg)

    # Con epsilon=1.0, ambos grupos están en radio → consenso ≈ promedio ponderado
    consensus_expected = 0.5 * 0.8 + 0.5 * 0.2  # = 0.5
    reached_consensus = abs(estado_large["opinion"] - consensus_expected) < 0.1

    if stayed_near_a and reached_consensus:
        record("Clustering HK (epsilon pequeño vs grande)", "PASS",
               f"eps=0.1: opinion={estado_small['opinion']:.4f} (cerca de A=0.8), "
               f"eps=1.0: opinion={estado_large['opinion']:.4f} (consenso≈{consensus_expected})",
               f"Δ_A={abs(estado_small['opinion']-0.8):.4f}")
    else:
        record("Clustering HK (epsilon pequeño vs grande)", "FAIL",
               f"stayed_near_a={stayed_near_a}, reached_consensus={reached_consensus}. "
               f"eps=0.1→{estado_small['opinion']:.4f}, eps=1.0→{estado_large['opinion']:.4f}")

# ============================================================================
# [3.4] EFECTO BACKLASH (regla "backlash")
# ============================================================================
def test_backlash():
    """Propaganda alta con opinión baja → opinión se aleja (backlash)."""
    from simulator import regla_backlash

    cfg = {"rango": "[0, 1] — Probabilístico", "ruido_base": 0.0}
    params = {"penalizacion": 0.15, "umbral_inferior": 0.35}

    estado = {"opinion": 0.2, "propaganda": 0.9,
              "opinion_grupo_a": 0.8, "opinion_grupo_b": 0.2,
              "pertenencia_grupo": 0.6, "historial": [0.2]}
    initial = estado["opinion"]

    for _ in range(50):
        estado = regla_backlash(estado, params, cfg)

    final = estado["opinion"]
    moved_away = final < initial  # Debe haberse alejado de la propaganda (disminuido)

    if moved_away:
        record("Efecto Backlash", "PASS",
               f"opinion: {initial:.4f} → {final:.4f} (se alejó de propaganda=0.9)",
               f"Δ={final-initial:.4f}")
    else:
        record("Efecto Backlash", "FAIL",
               f"opinion: {initial:.4f} → {final:.4f} (NO se alejó de propaganda=0.9)",
               f"Δ={final-initial:.4f}")

# ============================================================================
# [3.5] INVARIANTE DE CONTAGIO SIR (S + I + R = N)
# ============================================================================
def test_sir_conservation():
    """S(t) + I(t) + R(t) = 1 para todo t."""
    from massive.core.extended_models import regla_sir

    cfg = {"rango": "[0, 1] — Probabilístico", "ruido_base": 0.0}
    params = {"beta": 0.3, "gamma": 0.1, "dt": 0.2}

    estado = {"opinion": 0.1, "propaganda": 0.5}
    max_violation = 0.0

    for step in range(100):
        estado = regla_sir(estado, params, cfg)
        S = estado.get("_sir_S", 0)
        I = estado.get("_sir_I", 0)
        R = estado.get("_sir_R", 0)
        total = S + I + R
        violation = abs(total - 1.0)
        max_violation = max(max_violation, violation)
        if violation > 0.01:
            record("Invariante SIR (S+I+R=N)", "FAIL",
                   f"step {step}: S={S:.4f}+I={I:.4f}+R={R:.4f}={total:.4f} (Δ={violation:.4f})",
                   violation)
            return

    if max_violation < 0.01:
        record("Invariante SIR (S+I+R=N)", "PASS",
               f"100 pasos, max_violation={max_violation:.6f}", max_violation)
    else:
        record("Invariante SIR (S+I+R=N)", "FAIL",
               f"max_violation={max_violation:.6f}", max_violation)

# ============================================================================
# [3.6] EQUILIBRIO DE NASH (regla "nash")
# ============================================================================
def test_nash_equilibrium():
    """Nash debe converger a un valor estable."""
    from massive.core.extended_models import regla_nash

    cfg = {"rango": "[0, 1] — Probabilístico", "ruido_base": 0.0}
    params = {"c_same": 1.0, "c_diff": 0.0, "intensity": 0.3}

    estado = {"opinion": 0.5, "propaganda": 0.0,
              "opinion_grupo_a": 0.8, "opinion_grupo_b": 0.2,
              "pertenencia_grupo": 0.5, "historial": [0.5]}

    opinions = [estado["opinion"]]
    for _ in range(200):
        estado = regla_nash(estado, params, cfg)
        opinions.append(estado["opinion"])

    final_std = np.std(opinions[-50:])
    if final_std < 0.01:
        record("Equilibrio Nash (convergencia)", "PASS",
               f"std_final={final_std:.6f}, valor={np.mean(opinions[-10:]):.4f}",
               final_std)
    else:
        record("Equilibrio Nash (convergencia)", "FAIL",
               f"std_final={final_std:.6f} (esperado <0.01)", final_std)

# ============================================================================
# EJECUCIÓN PRINCIPAL
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("FASE 3 — VALIDACIÓN DE INVARIANTES MATEMÁTICOS")
    print("=" * 70)

    tests = [
        test_rango_unipolar,
        test_rango_bipolar,
        test_degrool_convergence,
        test_hk_clustering,
        test_backlash,
        test_sir_conservation,
        test_nash_equilibrium,
    ]

    for test in tests:
        print(f"\n--- {test.__name__} ---")
        try:
            test()
        except Exception as e:
            tb = traceback.format_exc()
            record(test.__name__, "FAIL", f"EXCEPCIÓN: {str(e)[:200]}")
            print(tb[:500])

    # Guardar
    output_path = os.path.join(REPO, "experiments/01_unit/invariant_validation_results.json")
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    passed = len([r for r in results if r["resultado"] == "PASS"])
    failed = len([r for r in results if r["resultado"] == "FAIL"])
    print(f"\n{'='*70}")
    print(f"TOTAL: {passed} PASS, {failed} FAIL de {len(results)} invariantes")
    print(f"Resultados: {output_path}")
    print(f"{'='*70}")
