# FASE 2 — Calibración

> **Orquestador:** OMNISCIENT
> **Fecha:** 2026-10-14
> **Commit HEAD:** `2390bd0`
> **Entorno:** Python 3.14.8 (venv), `pip install -e .` completado
> **Objetivo:** Verificar el proceso de calibración (Tier 1), validar que los
> parámetros calibrados existen y son reproducibles, y confirmar que el
> protocolo de walk-forward no permite leakage.

---

## 1. Tier 1 Calibration Pipeline

**Capacity Tier 1** (< 500 observations): baselines + aggregate physics parameters
with strong priors only. Neural correctors and per-segment/per-edge parameters are
**forbidden** by protocol — only 169 observations across 12 historical cases exist.

### Pipeline components

| Component | Description | Where | Estado |
|---|---|---|---|
| **G0 baselines** | 6 baselines × 12 cases via walk-forward CV | `scripts/run_baselines.py` → `reports/baselines_12cases.json` | ✅ Verificado |
| **ABC-SMC calibration** | ABC-SMC on 3 aggregate params (σ, ε, λ) | `massive/core/abcsbi.py` | ✅ Existe; v1.0.0 en `configs/calibrated/physics_params_v1.0.0.yaml` |
| **PVU backtests** | Day-0 blind backtests through G1–G4 gates | `scripts/run_backtests.py` → `reports/backtest_results.json` | ✅ Verificado (4 cases) |
| **Convergence certifier** | Deterministic planning certificate | `massive/core/convergence_certifier.py` | ✅ Existe |
| **Data provenance** | Hash-verified dataset registry, sealed splits | `massive/core/data_provenance.py`, `ground_truth/` | ✅ Existe |

### Calibrated parameters (Tier 1) — v1.0.0

```yaml
sigma: 0.1001          # diffusion coefficient
epsilon: 0.2525        # external noise injection
lambda_social: 0.521   # social coupling strength
```

Fuente: `configs/calibrated/physics_params_v1.0.0.yaml` (367 líneas, traceability model).

---

## 2. Baseline Results (12 cases, walk-forward)

Command: `python scripts/run_baselines.py --cases 12`

### Resultados agregados

| Baseline | Mean MAE | Mean RMSE |
|---|---|---|
| **persistence** (best) | **0.0482** | 0.0482 |
| mean_reverting | 0.0816 | 0.0816 |
| moving_average | 0.1068 | 0.1068 |
| train_mean | 0.1223 | 0.1223 |
| linear | 0.1274 | 0.1274 |
| seasonal_naive | 0.1440 | 0.1440 |

**Any model that does not beat persistence (MAE=0.0482) is not published.**

### Per-case best baseline

| Case | Best baseline | MAE |
|---|---|---|
| brazil_election_2022 | persistence | 0.0389 |
| brexit_referendum_2016 | persistence | 0.0500 |
| chile_estallido_2019 | persistence | 0.0575 |
| colombia_paro_2021 | persistence | 0.0425 |
| egypt_arab_spring_2011 | persistence | 0.1064 |
| france_gilets_jaunes_2018 | persistence | 0.0467 |
| germany_pegida_2014 | persistence | 0.0267 |
| hong_kong_protests_2019 | persistence | 0.0408 |
| iran_mahsa_amini_2022 | persistence | 0.0636 |
| myanmar_coup_cdm_2021 | persistence | 0.0567 |
| south_korea_candlelight_2016 | persistence | 0.0291 |
| us_election_2020 | linear | 0.0161 |

> 💡 US 2020 es el único caso donde Linear supera a Persistence (MAE=0.0161 vs
> 0.0482). En los otros 11 casos, Persistence (el naive forecast) es el mejor
> baseline.

---

## 3. PVU Backtest Results (G3 + G4 gates)

Command: `python scripts/run_backtests.py` (4 casos, seed=42)

| Case | Wasserstein | 90% CI coverage | G3 | G4 | Status |
|---|---|---|---|---|---|
| us_election_2020 | 0.0331 | 0.929 | ✅ | ✅ | **Published** |
| brexit_referendum_2016 | 0.0339 | 0.636 | ❌ | ❌ | Fails G4 coverage |
| chile_estallido_2019 | 0.0796 | 0.267 | ❌ | ❌ | Fails G3+W2 |
| south_korea_candlelight_2016 | 0.0513 | 0.357 | ❌ | ❌ | Fails G3+W2 |

**1/4 cases pass all PVU gates (G1+G2+G3+G4)** — US 2020 is the only case
clearing all thresholds.

Thresholds (de `configs/calibrated/backtest_thresholds.yaml`):

| Gate | Métrica | Threshold |
|---|---|---|
| G1 | DTW-RMSE | < 0.05 |
| G2 | Wasserstein | < 0.05 |
| G3 | KL divergence | < 0.5 |
| G4 | 90% CI coverage | > 0.7 |

---

## 4. CfC Neural Corrector — Walk-Forward Disqualification

### Audit protocol

`scripts/validate_cfc_walkforward.py` — standalone audit script that:
1. Uses **pre-registered** label-leakage audit (anti-leakage guard at module level)
2. Runs with `PYTHONHASHSEED=42` for determinism
3. Uses **10 seeds** (0–9) not in training set
4. Compares against 5 baselines: persistence, oracle_mean, train_mean, cfc_model, zero

### Resultados

```
strategy            RMSE       MAE       R^2   note
--------------------------------------------------
persistence      0.00457   0.00381     0.709   repeat the last observed residual
oracle_mean      0.00847   0.00629     0.000   best possible constant
train_mean       0.03184   0.03069   -13.128   a single constant from training
cfc_model        0.03763   0.03653   -18.732   the shipped corrector
zero             0.07373   0.07325   -74.779   apply no correction at all
```

**VERDICT: NOT FIT FOR PURPOSE** — the model reduces error versus doing nothing
(RMSE 0.03763), but is beaten out-of-sample by: train_mean, oracle_mean, persistence.

### Smoking gun: validation.json

`models/cfc_calibrated/validation.json` shows:

```json
{
  "corrected_metrics": {
    "correction_method": "Model-guided adaptive bias correction (50% toward target)",
    "improvement_percent": 50.0
  },
  "stress_test_stats": {
    "mean_improvement": 0.0464,
    "positive_count": 10,
    "total_seeds": 10
  }
}
```

**Exactly 50.0% improvement on all 10 seeds** is the signature of label leakage —
the `correct_residual(actual=...)` call was doing `correction = 0.5 * baseline_error`,
which interpolates halfway between the simulation and the ground truth.

This has been **fixed** in FASE 1:
- `brexit_calibration.py`: removed `actual=` parameter from `correct_residual()` call
- `cfc_router.py`: added quality gate (`_check_residual_quality()`) that reads
  `validation.json`, detects `test_r2 = -18.73 < 0`, and suppresses the model

---

## 5. Reproducible Calibration Workflow

### Prerequisites

```bash
pip install -e ".[full]"  # installs all extras including dev tools
PYTORCH_AVAILABLE = true  # for running backtests with the (qualified) model
```

### Run the full Tier 1 calibration pipeline

```bash
# 1. G0: Baselines (12 cases, 6 baselines)
PYTHONHASHSEED=42 python scripts/run_baselines.py --cases 12

# 2. G4: Backtests (blind day-0 predictions)
PYTHONHASHSEED=42 python scripts/run_backtests.py

# 3. Walk-forward validation of the CfC corrector
PYTHONHASHSEED=42 python scripts/validate_cfc_walkforward.py

# 4. Verify calibration gate passes
PYTHONHASHSEED=42 python scripts/verify_harness.py --calibration
```

### Seeded reproducibility

| Seed | Purpose |
|---|---|
| 42 | Tier 1 calibration (physics params, seed in `physics_params_v1.0.0.yaml`) |
| 42 | PVU backtests |
| 42 | Brexcal end-to-end (energy engine) |
| 0–9 | CfC walk-forward (disqualified) |

All seeds are pre-registered in `configs/calibrated/pre_registration/`.

---

## 6. Calibrated artifacts summary

| Artifact | Path | Estado |
|---|---|---|
| Physics params | `configs/calibrated/physics_params_v1.0.0.yaml` | ✅ Present, seeded |
| Pre-registrations | `configs/calibrated/pre_registration/prereg_*.yaml` (×12) | ✅ Present |
| Backtest thresholds | `configs/calibrated/backtest_thresholds.yaml` | ✅ Present |
| Baseline results | `reports/baselines_12cases.json` | ✅ Regenerable |
| Backtest results | `reports/backtest_results.json` | ✅ Regenerable (4 casos) |
| CFC validation metrics | `models/cfc_calibrated/validation.json` | ✅ Present (disqualified) |
| CFC model weights | `models/cfc_calibrated/cfc_residual.pt` | ✅ Present (suppressed by quality gate) |

---

## GATE — FASE 2

### ✅ CUMPLIDO

- ✅ Tier 1 calibration artifacts exist and are versioned.
- ✅ Baseline protocol (6 baselines × 12 cases, walk-forward) reproduces.
- ✅ PVU backtest pipeline runs without errors, writes structured JSON.
- ✅ CfC model is properly disqualified by walk-forward validation (R²=-18.7).
- ✅ Quality gate suppresses the disqualified model (verified via tests in FASE 1).
- ✅ All seeds are pre-registered (no post-hoc seed shopping).
- ✅ `PYTHONHASHSEED=42` enforced for deterministic reproducibility.
- ✅ No calibration artifact uses test-set data for fitting.
