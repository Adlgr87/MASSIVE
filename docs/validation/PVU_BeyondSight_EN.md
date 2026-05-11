# BeyondSight Protocol of Validated Use (PVU-BS) — English

> **Version:** 1.0 · **Status:** Active  
> **Spanish version:** [PVU_BeyondSight_ES.md](PVU_BeyondSight_ES.md)

---

## 1. Purpose

The **Protocol of Validated Use (PVU-BS)** establishes the minimum evidence standard required to claim that BeyondSight provides *validated* predictive performance on real-world opinion dynamics data.  
It distinguishes clearly between:

- **Sample cases** (`datasets/pvu_cases/sample_case_*`): synthetic data used only to verify the pipeline runs correctly. No scientific claims may be drawn from them.
- **Real validation**: N ≥ 10 independent cases with held-out test sets, run under this protocol.

---

## 2. Operational Definitions

### 2.1 Independent Case

A **case** is the tuple `{network, time_series, interventions, metadata}` described in a PVU case folder.

Two cases are considered **independent** if **both** of the following hold:

1. **Network non-overlap:** the sets of nodes (users/communities) share fewer than 10 % of their members, OR the graph structures are drawn from genuinely distinct populations.
2. **Temporal non-overlap:** their time windows do not coincide with the same unmodelled global shock (e.g., a worldwide pandemic event).  
   If they do share a shock, they must share a common `cluster_id` in `meta.json` and evaluation must be done at the **cluster level** (one DM test per cluster, not per case), correcting for the reduced effective sample size.

### 2.2 `cluster_id` Usage

`cluster_id` groups cases affected by the same structural or temporal confound.  
Rules:

- Set `cluster_id` in `meta.json` when cases share a platform, regional event, or overlapping time window.
- Statistical tests and effect sizes are computed **per cluster** when N_cluster > 1; individual case results are reported as supplementary.
- Cluster-level metrics are the weighted mean of per-case metrics (weight = N_test of each case).

### 2.3 Target Variable

BeyondSight is validated on a **compound target** that captures both level and dynamics of opinion polarization:

| Component | Definition | Metric |
|-----------|-----------|--------|
| **Polarization Index P(t)** | Variance of the opinion distribution + fraction of agents at extremes (|opinion| > 0.7 on [−1, 1]) | MAE, RMSE, MAPE, Directional Accuracy |
| **Turning-Point Skill (TPS)** | Ability to predict *when* a regime transition occurs (local extremum in P) | Precision, Recall, F1, Mean Timing Error |

### 2.4 Train / Validation / Test Split

| Split | Fraction | Purpose |
|-------|----------|---------|
| Train | 70 % | Model calibration, parameter selection |
| Validation | — | (optional) hyperparameter tuning |
| Test | 30 % | **Held-out; must not be touched before final evaluation** |

---

## 3. Anti-Leakage Rules

The following actions constitute **test leakage** and invalidate the validation run:

1. Looking at test-split metrics (even in aggregate) before the model configuration is frozen.
2. Adjusting prompts, temperature, model provider, regime rules, or any parameter **after seeing test results**, even informally.
3. Selecting or discarding cases *post-hoc* to improve reported scores.
4. Running the model multiple times on the same test set and reporting the best run (unless explicitly doing a LLM consistency check under § 6).
5. Using test-split observations as training context in the LLM prompt.

**Logging:** A pre-registration document (see `preregistration_template_EN.md`) must be committed to the repository **before** breaking the test seal.

---

## 4. Statistical Criterion

### 4.1 Primary Hypothesis

> BeyondSight produces significantly lower MAE on the held-out test set compared to the naive baseline (last-value persistence), after Holm–Bonferroni correction.

### 4.2 Test Procedure

1. Compute forecasts for **all** baselines and BeyondSight on the test split of **each** case.
2. For each case, run a two-sided **Diebold–Mariano (DM) test** of BeyondSight vs each baseline using squared-error loss.
3. Collect the M raw p-values per case (one per baseline).
4. Apply **Holm–Bonferroni correction** across the M × N comparisons (M baselines × N cases). Use `benchmarks/metrics.py::holm_bonferroni`.
5. Report both raw and adjusted p-values.

### 4.3 Effect Sizes (mandatory alongside p-values)

| Metric | Interpretation |
|--------|---------------|
| ΔMAE = MAE_baseline − MAE_BS | Absolute improvement in MAE |
| ΔRMSE | Absolute improvement in RMSE |
| Directional accuracy lift | BS dir. acc. − naive dir. acc. |
| TPS F1 | Precision–Recall balance on turning points |

### 4.4 Acceptance Criteria (by PVU level)

| Level | Min cases | DM vs naive | Effect size | TPS F1 |
|-------|-----------|-------------|-------------|--------|
| Bronze | 10 | p_adj < 0.05 | ΔMAE > 0 | — |
| Silver | 20 | p_adj < 0.05 vs **all** baselines | ΔMAE > 5 % | ≥ 0.50 |
| Gold | 30 | p_adj < 0.05 vs all + external replication | ΔMAE > 10 % | ≥ 0.70 |

---

## 5. Baselines (mandatory)

All of the following must be included in every validation run:

| ID | Name | Description |
|----|------|-------------|
| B1 | Naive | Last observed value persisted for all forecast steps |
| B2 | Moving Average | Mean of last 4 observations |
| B3 | AR(1) | First-order autoregression fitted by OLS |
| B4 | Random Regime | Random walk with training-calibrated noise |

Implemented in `benchmarks/baselines.py`.

---

## 6. LLM Consistency Check

When BeyondSight is run in LLM mode:

1. Run the same forecast **5 times** with different random seeds.
2. Compute the coefficient of variation (CV = std / mean) of the reported MAE across runs.
3. If CV > 0.15 (15 %), flag the result and report it; do not suppress it.

---

## 7. Reproducibility Requirements

Every validation run must produce and archive:

- `configs/pvu.yaml` (frozen copy with all parameters).
- `reports/validation/<run_id>/metrics.json` (all per-case metrics).
- `reports/validation/<run_id>/report.md` (human-readable summary).
- Git commit SHA of the codebase.
- Python package versions (`pip freeze`).
- LLM provider + model name + temperature (if LLM mode).
- `PYTHONHASHSEED` and `--seed` value.

The runner (`benchmarks/runner.py`) writes `metrics.json` and `report.md` automatically.

---

## 8. How to Run

```bash
# Offline mode (no API key required — CI default):
PYTHONHASHSEED=42 python -m benchmarks.runner \
    --cases datasets/pvu_cases \
    --offline \
    --out reports/validation/ci \
    --seed 42

# LLM mode (requires OPENROUTER_API_KEY or OPENAI_API_KEY):
PYTHONHASHSEED=42 python -m benchmarks.runner \
    --cases datasets/pvu_cases \
    --llm \
    --out reports/validation/llm_run \
    --seed 42
```

---

## 9. Case File Format

Each case lives in its own sub-folder under `datasets/pvu_cases/`:

```
sample_case_001/
├── timeseries.csv        # required: columns date, P (+ optional)
├── interventions.json    # list of {date, label, source}
└── meta.json             # case metadata
```

### `timeseries.csv` columns

| Column | Type | Description |
|--------|------|-------------|
| `date` | string (ISO 8601) | Observation date |
| `P` | float [0, 1] | Polarization index |
| `volume` | float (optional) | Activity volume proxy |

### `meta.json` required fields

| Field | Type | Description |
|-------|------|-------------|
| `case_id` | string | Unique identifier |
| `domain` | string | e.g. `political_opinion` |
| `source` | string | Data origin (or `synthetic`) |
| `cluster_id` | string \| null | Cluster for grouped tests |
| `license` | string | Data license |
| `note` | string | Free-text notes |

---

## 10. Glossary

| Term | Definition |
|------|-----------|
| PVU-BS | Protocol of Validated Use — BeyondSight |
| DM test | Diebold–Mariano test of equal predictive accuracy |
| Holm–Bonferroni | Step-down multiple-comparison correction |
| TPS | Turning-Point Skill (F1 on detected local extrema) |
| EWS | Early Warning Signal (Critical Slowing Down) |
| Test leakage | Any information flow from test split to model design |
| Sample case | Synthetic case for pipeline testing only |

---

*See also: [Preregistration template](preregistration_template_EN.md) · [Validation report template](validation_report_template_EN.md)*
