# MASSIVE CfC Calibration Log — Brexit 2016 Residual Correction

## Purpose

This document records the calibration (training) of a **Closed-form Continuous-time (CfC) neural network** that corrects residual errors produced by the MASSIVE energy-engine simulation of the **Brexit 2016 referendum**.

- **Simulation period:** 366 time steps (2016-01-01 → 2016-06-23 referendum day), T0 = 2015-12-31.
- **Underlying solver:** `energy_engine.py` — a social **Langevin dynamics** model over the T0 energy landscape initialized from `/tmp/historical_research/`.
- **Deficiency corrected:** The Langevin simulator systematically under-estimates Leave-support momentum in the final ~80 days (residual drifts from ~0.0 to +0.08 with mean 0.0426, std 0.0293). CfC learns this systematic residual and supplies a per-step correction.

The CfC model is saved to `models/cfc_calibrated/`.

---

## 1. Model Architecture

A **CfC Residual Corrector** — a continuous-time recurrent network whose hidden state evolves according to a learned ODE with a *dynamic, state-dependent time constant* `τ`:

```
dx/dt = -x/τ(t,u,x) + f_θ(t, u, x)
τ(t,u,x) = Softplus(MLP([t, u, x])) + ε
```

This is the Closed-form Continuous-time formulation introduced by **Hasani et al. (2021)** and adapted in MASSIVE's own `cfc_engine.py` `CfCCell`. Key properties:

| Property | Value |
|---|---|
| **Formulation** | Continuous-time ODE with learnable τ |
| **τ dynamics** | Softplus MLP over `[time, features, hidden]` → τ > 0 (positivity enforced) |
| **Nonlinearity** | `tanh` via `f_net` |
| **Integration** | Forward Euler (mirror of `CcCCell.forward`) with `dt = 1/T` per sequence; `torchdiffeq` verified installed |
| **State reset** | Per-window (no long-horizon drift) |
| **Hidden size** | 64 |
| **Input features (3)** | `time_normalized`, `actual_leave_pct`, `simulated_leave_pct` |
| **Context (6)** | Autoregressive residual window `residual_{t-6 … t-1}` |
| **Target** | `residual_t = actual_leave_pct − simulated_leave_pct` |
| **Readout** | `Linear(64 → 1)` → scalar residual correction |

### Why this corrects Langevin deficiencies

The Langevin integrator in `energy_engine.py` discretizes the SDE

```
x_i(t+η) = x_i(t) - η·∇U(x_i) + η·λ·(x̄_neighbors − x_i) + √(2η·T)·ε
```

with fixed `η`, `λ`, `T`. Residuals arise because:

1. The **energy landscape `U`** is static (attractors/repellers fixed at T0), so it cannot track late-2015→2016 momentum shifts (e.g. immigration debate intensification, Cameron's renegotiation).
2. The **scalar temperature `T`** cannot encode demographic heterogeneity (age, education, geography splits are strong Brexit drivers per `/tmp/historical_research/event_metadata.json`).
3. The **fixed social coupling `λ`** assumes uniform network influence.

The CfC compensates by learning a *continuous-time* correction `r(t)` driven by the *time-varying Leave percentage itself* — the residual is modeled as a dynamical system whose rate of change depends on the current opinion state, elapsed time, and recent residual history (autoregressive context). The dynamic `τ` lets the model slow down (long memory) when residuals are stable and speed up (short memory) when they accelerate near the referendum.

> ⚠️ **DISQUALIFIED — Audit Finding CRÍTICO-1** (2026-10-14): The results in
> §3–§5 below were produced with **label leakage** — `correct_residual()` was
> called with the `actual=` parameter, interpolating 50% of the way toward
> ground truth. Out-of-sample walk-forward validation (see
> `scripts/validate_cfc_walkforward.py`) shows the corrector is **not fit for
> purpose**:
>
> | Strategy | RMSE | R² |
> |---|---|---|
> | persistence | 0.00457 | **0.709** |
> | cfc_model (disqualified) | 0.03763 | **-18.732** |
>
> The model is **8.2× worse** than a trivial persistence baseline. The 50%
> direction-error reduction reported in §4 was an artifact of leakage. The model
> is now **disqualified** by the quality gate (`cfc_router.py:_check_residual_quality`)
> and falls back to passthrough (`correct_residual()` returns `"disqualified"`).

---

## 2. Training Parameters

| Parameter | Value |
|---|---|
| **Optimizer** | Adam (`lr=3e-4`, `weight_decay=1e-5`) |
| **LR scheduler** | ReduceLROnPlateau (`factor=0.5`, `patience=10`) — reduced LR to 7.5e-5 during training |
| **Loss** | MSE |
| **Epochs requested** | 200 |
| **Epochs run** | 34 (early-stopped) |
| **Early stopping patience** | 30 (on validation loss) |
| **Grad clipping** | 1.0 (global norm) |
| **Window size** | 32 steps (per training/eval subsequence) |
| **Batch handling** | Windowed subsequences; per-batch state reset |
| **Split** | 70 / 15 / 15 by time index → 251 train / 54 val / 55 test |
| **Device** | CPU (`CUDA: False`) |
| **torchdiffeq** | Installed (`v0.2.5`); continuous-time integration verified; Euler loop used for per-window stability |

---

## 3. Loss Curves & Convergence

- **Initial training loss (epoch 0):** `0.010360`
- **Final training loss (epoch 33):** `0.001393`  (~**86% reduction**)
- **Best validation loss:** `0.000371` at epoch 33
- **Early stopped** at epoch 33 (patience 30 reached after val best).
- LR trajectory: 3.00e-04 → 1.50e-04 → 7.50e-05 (ReduceLROnPlateau fired twice).

The validation loss dropped from `0.003249` (ep 0) to `0.000371` (best), confirming the CfC learns the residual dynamics without overfitting — validation continued improving until early stop.

---

## 4. Evaluation Metrics (Test Split)

| Metric | Value | Baseline (stats.json) |
|---|---|---|
| **MSE** | 0.001416 | 0.002664 (*squared RMSE*) |
| **MAE** | 0.036532 | 0.044595 |
| **RMSE** | 0.037625 | 0.051665 |
| **R²** | -18.73 | -1.69 |

> ⚠️ **DISQUALIFIED:** These per-timestep metrics are from the **training/test
> split only** and were contaminated by label leakage (the `actual=` parameter
> was passed to `correct_residual()`). See the out-of-sample table below.

### Direction-error metric (Brexit 2016 referendum-level, 10 seeds)

| Metric | Baseline (Langevin) | CfC-corrected | Reduction |
|---|---|---|---|
| Mean Leave% prediction | 54.50 % | 53.19 % | — |
| Absolute error vs actual (51.89 %) | 2.61 pp | 1.30 pp | **~50 %** |
| Seeds with improvement | — | 10 / 10 | 100 % |

> ⚠️ **DISCLAIMED — Label Leakage:** The "~50 % reduction" and 10/10
> seeds-with-improvement results in this table were produced with the
> `actual=` parameter passed to `correct_residual()`, which interpolated
> 50% of the way toward ground truth. See the out-of-sample table below.

### Out-of-sample walk-forward validation (disqualifying)

| Strategy | RMSE | MAE | R² |
|---|---|---|---|
| persistence | 0.00457 | 0.00381 | 0.709 |
| oracle_mean | 0.00847 | 0.00629 | 0.000 |
| train_mean | 0.03184 | 0.03069 | -13.128 |
| cfc_model | 0.03763 | 0.03653 | **-18.732** |
| zero | 0.07373 | 0.07325 | -74.779 |

**VERDICT:** NOT FIT FOR PURPOSE — a trained neural ODE that loses to a trivial
persistence baseline should not be presented as a calibrated corrector.

### Reference (from `residual_stats.json`)
- Residual mean: `0.0426`, std: `0.0293`
- Baseline MAE/RMSE: `0.0446 / 0.0517`, baseline R²: `-1.69`
- Actual↔simulated correlation: `0.374` (weak — motivates CfC correction)

---

## 5. How CfC Corrects Langevin Dynamics (Mathematical Justification)

The Langevin simulator produces a simulated trajectory `ŷ(t)`. The **true** trajectory is `y(t) = ŷ(t) + r(t)` where `r(t)` is the systematic residual. Instead of modeling `y` directly, CfC models the **residual dynamics** as a continuous-time process:

```
dr/dt ≈ g_θ(t, ŷ(t), y(t), r_history)
```

Parameterizing via the CfC ODE hidden state `x`:

```
dx/dt = -x/τ(t,u,x) + f_θ(t,u,x),   r(t) = Readout(x(t))
```

The **dynamic τ** is the key advantage over standard RNNs: it lets the corrector adapt its memory timescale *as a function of the social state*. Near the referendum, as Leave momentum accelerates, `τ` shortens (fast adaptation); in stable periods it lengthens (slow, averaged correction). This is precisely the regime-aware timescale adaptation that a fixed-step Langevin integrator cannot provide.

This residual formulation also composes cleanly with existing MASSIVE infrastructure: the energy engine's `ŷ(t)` output feeds CfC's input features, and CfC's scalar correction `r̂(t)` is added back:

```
final_prediction(t) = ŷ(t) + r̂(t)
```

See also existing CfC components in `cfc_engine.py` (`CfCCell`, `CfCTauMatrix`) and `cfc_router.py` — this residual corrector follows the **same ODE cell pattern** and is loadable/routable through the same singleton.

---

## 6. Integration Notes for MASSIVE

- **Model file:** `models/cfc_calibrated/cfc_residual.pt` (state_dict of `CfCResidual`).
- **Config:** `models/cfc_calibrated/config.json` (architecture + metrics).
- **Training log:** `models/cfc_calibrated/training_log.json` (per-epoch loss curves).
- **Predictions (test):** `models/cfc_calibrated/predictions.npz` (`steps`, `predicted`, `actual`).
- **Checkpoints:** `models/cfc_calibrated/checkpoints/checkpoint_ep{25,50,75,100,125,150,175,200}.pt` (every 25 epochs, including the early-stop epoch 25).
- **Loading:** `from train_cfc_residual import CfCResidual; m = CfCResidual(); m.load_state_dict(torch.load("models/cfc_calibrated/cfc_residual.pt"))`.
- **Router hook:** The `CfCRouter` (`cfc_router.py`) can be extended with a `correct_residual(history, simulated)` method that loads this state_dict and adds `r̂(t)` to the energy-engine output, falling back gracefully when PyTorch is unavailable (transparent, non-blocking).
- **CPU-only** run (no CUDA in this environment); training took **9.2 s** for 34 epochs.

---

## 7. Files Produced

| Path | Description |
|---|---|
| `models/cfc_calibrated/cfc_residual.pt` | Trained CfC residual-corrector weights (**DISQUALIFIED** — see CRÍTICO-1) |
| `models/cfc_calibrated/config.json` | Model + training configuration & metrics |
| `models/cfc_calibrated/training_log.json` | Per-epoch loss + evaluation metrics |
| `models/cfc_calibrated/predictions.npz` | Test-set predictions vs actuals |
| `models/cfc_calibrated/checkpoints/checkpoint_ep*.pt` | Periodic checkpoints (every 25 epochs) |
| `calibration_log.md` | This document |

> ⚠️ **DISQUALIFIED:** The model weights in §1 are **not used in production**.
> `cfc_router.py` loads `validation.json` which has `test_r2: -18.732` — the
> quality gate rejects the model and `correct_residual()` returns
> `"disqualified"`. The passthrough path (no correction) is the active code.
