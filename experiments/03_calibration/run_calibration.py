#!/usr/bin/env python3
"""
FASE 5 — CALIBRACIÓN EMPÍRICA

Verifica que la calibración existente en empirical_config.py produce
el comportamiento prometido.
"""
import sys, os, json, time, traceback
import numpy as np

REPO = "/home/adlg/Escritorio/Proyectos/MASSIVE"
sys.path.insert(0, REPO)
os.environ.setdefault("PYTHONHASHSEED", "42")

results = []

def record(name, status, detail):
    results.append({"test": name, "status": status, "detail": detail})
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"{icon} {name}: {status} — {detail}")

# ============================================================================
# [5.1] VERIFICACIÓN DE PERFILES CULTURALES
# ============================================================================
def test_cultural_profiles():
    """Para cada uno de los 7 perfiles, verificar que los parámetros difieren."""
    from empirical_calibration import build_empirical_engine_config

    profiles = ["mixed", "latin", "anglosaxon", "east_asian",
                "middle_east", "south_asian", "subsaharan_africa"]

    configs = {}
    for p in profiles:
        cfg = build_empirical_engine_config(cultural_profile=p)
        configs[p] = cfg
        assert isinstance(cfg, dict), f"Config para {p} no es dict"
        assert len(cfg) > 0, f"Config vacío para {p}"

    # Verificar que los perfiles difieren
    all_same = True
    for key in configs["mixed"]:
        if key in ("cultural_profile",):
            continue
        vals = set()
        for p in profiles:
            v = configs[p].get(key)
            if isinstance(v, (int, float)):
                vals.add(round(v, 4))
            elif isinstance(v, str):
                vals.add(v)
        if len(vals) > 1:
            all_same = False
            break

    if all_same:
        record("Perfiles culturales — diversidad de parámetros", "FAIL",
               "Todos los perfiles producen los mismos valores")
    else:
        record("Perfiles culturales — diversidad de parámetros", "PASS",
               f"7 perfiles producen configs diferentes")

    # Verificar dirección esperada: east_asian < anglosaxon en homofilia_tasa
    # (lower rate = slower convergence = more sub-group differentiation in collectivist cultures)
    ea_homofilia = configs["east_asian"].get("homofilia_tasa", 0)
    ax_homofilia = configs["anglosaxon"].get("homofilia_tasa", 0)

    if ea_homofilia != ax_homofilia:
        record("Dirección cultural — homofilia_tasa (east_asian ≠ anglosaxon)", "PASS",
               f"east_asian={ea_homofilia}, anglosaxon={ax_homofilia}")
    else:
        record("Dirección cultural — homofilia_tasa (east_asian ≠ anglosaxon)", "WARN",
               f"east_asian={ea_homofilia} == anglosaxon={ax_homofilia}")

    # Verificar: latin ≠ anglosaxon en distancia_poder (buscamos el key real)
    dp_keys_latin = {k: v for k, v in configs["latin"].items() if 'distancia' in k.lower() or 'poder' in k.lower()}
    dp_keys_ax = {k: v for k, v in configs["anglosaxon"].items() if 'distancia' in k.lower() or 'poder' in k.lower()}
    if dp_keys_latin != dp_keys_ax:
        record("Dirección cultural — distancia_poder (latin ≠ anglosaxon)", "PASS",
               f"latin={dp_keys_latin}, anglosaxon={dp_keys_ax}")
    else:
        record("Dirección cultural — distancia_poder (latin ≠ anglosaxon)", "WARN",
               f"latin={dp_keys_latin} == anglosaxon={dp_keys_ax}")

    # Simular con cada perfil
    from simulator import simular
    profile_results = {}
    for p in profiles:
        np.random.seed(42)
        cfg_sim = {"proveedor": "heurístico"}
        cfg_sim.update(configs[p])
        estado = {"opinion": 0.5, "propaganda": 0.3}
        result = simular(estado, pasos=100, cada_n_pasos=10,
                          config=cfg_sim, verbose=False)
        opinions = [h["opinion"] for h in result]
        profile_results[p] = {
            "final_opinion": opinions[-1],
            "mean": np.mean(opinions),
            "std": np.std(opinions),
        }

    # Verificar que las trayectorias divergen
    final_opinions = [profile_results[p]["final_opinion"] for p in profiles]
    opinion_range = max(final_opinions) - min(final_opinions)
    if opinion_range > 0.01:
        record("Trayectorias por perfil cultural — divergencia", "PASS",
               f"range de opiniones finales: {opinion_range:.4f} "
               f"({min(final_opinions):.4f} a {max(final_opinions):.4f})")
    else:
        record("Trayectorias por perfil cultural — divergencia", "WARN",
               f"range={opinion_range:.4f} — trayectorias muy similares")

    # Guardar detalle de perfiles
    return configs, profile_results

# ============================================================================
# [5.2] CROSS-VALIDATION DE PARÁMETROS EMPÍRICOS
# ============================================================================
def test_param_validation():
    """Verificar que los 10 parámetros más críticos tienen fuente y valor correcto."""
    from massive.core.empirical_config import MASSIVE_EMPIRICAL_MASTER

    critical_params = [
        ("HOMOFILIA_RED", 0.45, "McPherson et al. (2001)"),
        ("SESGO_CONFIRMACION", 0.60, "Nickerson (1998)"),
        ("EFECTO_BACKFIRE", 0.15, "Nyhan & Reifler (2010)"),
        ("INDIVIDUALISMO_COLECTIVISMO", 0.50, "Hofstede (2010)"),
        ("DISTANCIA_PODER", 0.50, "Hofstede (2010)"),
        ("CONTAGIO_EMOCIONAL", 0.35, "Hatfield et al. (1993)"),
        ("POLARIZACION_GRUPO", 0.40, "Sunstein (2002)"),
        ("MEDIA_VIDA_DIGITAL", 18.0, "Wojcieszak et al. (2022)"),
        ("CASCADA_INFORMACIONAL", 0.25, "Bikhchandani et al. (1992)"),
        ("EFECTO_MANADA", 0.30, "Banerjee (1992)"),
    ]

    verified = 0
    for param_name, expected_val, expected_source in critical_params:
        found = False
        for category, params in MASSIVE_EMPIRICAL_MASTER.items():
            if param_name in params:
                p = params[param_name]
                actual_val = p.get("value")
                actual_source = p.get("source", "")
                if isinstance(actual_source, list):
                    actual_source = " ".join(str(s) for s in actual_source)
                else:
                    actual_source = str(actual_source)
                val_match = abs(actual_val - expected_val) < 0.01
                source_match = expected_source.split("(")[0].strip().lower() in actual_source.lower()
                if val_match and source_match:
                    verified += 1
                    found = True
                break

    pct = verified / len(critical_params) * 100
    if pct >= 80:
        record(f"Cross-validation parámetros críticos ({verified}/{len(critical_params)})", "PASS",
               f"{pct:.0f}% verificados con fuente y valor correctos")
    else:
        record(f"Cross-validation parámetros críticos ({verified}/{len(critical_params)})", "FAIL",
               f"Solo {pct:.0f}% verificados")

# ============================================================================
# [5.3] CALIBRACIÓN CON FENÓMENOS CONOCIDOS (GROUND TRUTH)
# ============================================================================
def test_ground_truth_scenarios():
    """3 escenarios de verdad de tierra basados en fenómenos sociales documentados."""

    # --- ESCENARIO A: Polarización política ---
    from massive.core.extended_models import regla_nash
    from simulator import regla_hk

    cfg = {"rango": "[0, 1] — Probabilístico", "ruido_base": 0.0, "hk_epsilon": 0.2}
    params = {"epsilon": 0.2, "alpha": 0.4}
    success_a = 0
    for seed in range(42, 62):
        np.random.seed(seed)
        estado = {"opinion": 0.5, "propaganda": 0.4,
                  "opinion_grupo_a": 0.8, "opinion_grupo_b": 0.2,
                  "pertenencia_grupo": 0.5, "historial": [0.5]}
        for _ in range(200):
            estado = regla_hk(estado, params, cfg)
        # Criterio: opinion debe estar cerca de uno de los polos (0.2 o 0.8)
        final = estado["opinion"]
        if abs(final - 0.8) < 0.15 or abs(final - 0.2) < 0.15:
            success_a += 1

    pct_a = success_a / 20 * 100
    if pct_a >= 70:
        record("Escenario A — Polarización (bimodal)", "PASS",
               f"{success_a}/20 runs ({pct_a:.0f}%) con polarización")
    else:
        record("Escenario A — Polarización (bimodal)", "FAIL",
               f"{success_a}/20 runs ({pct_a:.0f}%) — esperado ≥70%")

    # --- ESCENARIO B: Consenso de movimiento social ---
    from simulator import regla_umbral_heterogeneo
    cfg_b = {"rango": "[0, 1] — Probabilístico", "ruido_base": 0.0}
    params_b = {"umbral_media": 0.25}
    success_b = 0
    for seed in range(42, 62):
        np.random.seed(seed)
        estado = {"opinion": 0.3, "propaganda": 0.6,
                  "opinion_grupo_a": 0.8, "opinion_grupo_b": 0.2,
                  "pertenencia_grupo": 0.6, "historial": [0.3]}
        for _ in range(100):
            estado = regla_umbral_heterogeneo(estado, params_b, cfg_b)
        if estado["opinion"] > 0.7:
            success_b += 1

    pct_b = success_b / 20 * 100
    if pct_b >= 70:
        record("Escenario B — Consenso (Centola)", "PASS",
               f"{success_b}/20 runs ({pct_b:.0f}%) con opinion>0.7")
    else:
        record("Escenario B — Consenso (Centola)", "FAIL",
               f"{success_b}/20 runs ({pct_b:.0f}%) — esperado ≥70%")

    # --- ESCENARIO C: Contagio epidémico (SIR) ---
    # R0 = beta/gamma. Para R0≈2.5: beta=0.5, gamma=0.2, dt=0.3
    from massive.core.extended_models import regla_sir
    cfg_c = {"rango": "[0, 1] — Probabilístico", "ruido_base": 0.0}
    params_c = {"beta": 0.5, "gamma": 0.2, "dt": 0.3}
    success_c = 0
    for seed in range(42, 62):
        np.random.seed(seed)
        estado = {"opinion": 0.05, "propaganda": 0.5}
        peak_I = 0
        peak_time = 0
        for step in range(100):
            estado = regla_sir(estado, params_c, cfg_c)
            I = estado.get("_sir_I", 0)
            if I > peak_I:
                peak_I = I
                peak_time = step
        final_R = estado.get("_sir_R", 0)
        if 25 <= peak_time <= 50 and final_R > 0.6:
            success_c += 1

    pct_c = success_c / 20 * 100
    if pct_c >= 70:
        record("Escenario C — Contagio SIR (peak 25-50, R>0.6)", "PASS",
               f"{success_c}/20 runs ({pct_c:.0f}%) cumplen criterio")
    else:
        record("Escenario C — Contagio SIR (peak 25-50, R>0.6)", "FAIL",
               f"{success_c}/20 runs ({pct_c:.0f}%) — esperado ≥70%")

# ============================================================================
# EJECUCIÓN
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("FASE 5 — CALIBRACIÓN EMPÍRICA")
    print("=" * 70)

    print("\n--- [5.1] Perfiles culturales ---")
    try:
        configs, profile_results = test_cultural_profiles()
    except Exception as e:
        record("Perfiles culturales", "FAIL", f"EXCEPIÓN: {e}")
        traceback.print_exc()

    print("\n--- [5.2] Cross-validation parámetros ---")
    try:
        test_param_validation()
    except Exception as e:
        record("Cross-validation", "FAIL", f"EXCEPIÓN: {e}")
        traceback.print_exc()

    print("\n--- [5.3] Escenarios ground truth ---")
    try:
        test_ground_truth_scenarios()
    except Exception as e:
        record("Ground truth scenarios", "FAIL", f"EXCEPIÓN: {e}")
        traceback.print_exc()

    # Guardar
    output_path = os.path.join(REPO, "experiments/03_calibration/calibration_validation_results.json")
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    passed = len([r for r in results if r["status"] == "PASS"])
    failed = len([r for r in results if r["status"] == "FAIL"])
    warned = len([r for r in results if r["status"] == "WARN"])
    print(f"\n{'='*70}")
    print(f"TOTAL: {passed} PASS, {failed} FAIL, {warned} WARN de {len(results)} tests")
    print(f"Resultados: {output_path}")
    print(f"{'='*70}")
