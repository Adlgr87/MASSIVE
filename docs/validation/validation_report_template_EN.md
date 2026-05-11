# PVU-BS Validation Report Template (English)

> Complete this document after the run.  
> Spanish version: [validation_report_template_ES.md](validation_report_template_ES.md)

---

## 1. Run Identification

| Field | Value |
|-------|-------|
| Run ID | `<!-- e.g. pvu_run_001 -->` |
| Pre-registration ref | `<!-- link/SHA to pre-reg commit -->` |
| Run date | `<!-- YYYY-MM-DD -->` |
| Git commit (codebase) | `<!-- SHA at run time -->` |
| Mode | `<!-- offline / llm -->` |
| Seed / PYTHONHASHSEED | `<!-- both values -->` |
| `metrics.json` path | `reports/validation/<run_id>/metrics.json` |

---

## 2. Cases Summary

| Case | N_total | N_train | N_test | Cluster | Skipped |
|------|---------|---------|--------|---------|---------|
| sample_case_001 | — | — | — | — | — |
| sample_case_002 | — | — | — | — | — |

> Replace with actual values from `metrics.json`.

---

## 3. Baseline Metrics (aggregate across all cases)

| Baseline | Mean MAE | Mean RMSE | Mean Dir. Acc. |
|----------|---------|-----------|----------------|
| naive | | | |
| moving_average | | | |
| ar1 | | | |
| random_regime | | | |

---

## 4. MASSIVE Metrics

| Metric | Value |
|--------|-------|
| Mean MAE | |
| Mean RMSE | |
| Mean MAPE (%) | |
| Mean Directional Accuracy | |
| ΔMAE vs naive | |
| ΔRMSE vs naive | |

---

## 5. Statistical Tests (Holm–Bonferroni adjusted)

| vs Baseline | Cases significant (p_adj < 0.05) | Mean p_adj |
|-------------|----------------------------------|-----------|
| naive | / N | |
| moving_average | / N | |
| ar1 | / N | |
| random_regime | / N | |

**Primary hypothesis:** `<!-- SUPPORTED / NOT SUPPORTED -->`  
_Justification:_

---

## 6. Turning-Point Skill

| Metric | Value |
|--------|-------|
| Mean Precision | |
| Mean Recall | |
| Mean F1 | |
| Mean Timing Error (steps) | |

---

## 7. LLM Consistency (if LLM mode)

| Metric | Value |
|--------|-------|
| N independent runs | |
| CV of MAE across runs | |
| Result flagged (CV > 0.15)? | |

---

## 8. PVU Level Achieved

- [ ] Bronze (N ≥ 10, DM vs naive p_adj < 0.05, ΔMAE > 0)
- [ ] Silver (N ≥ 20, DM vs all baselines p_adj < 0.05, TPS F1 ≥ 0.50)
- [ ] Gold (N ≥ 30, external replication, TPS F1 ≥ 0.70)
- [ ] None

---

## 9. Deviations from Pre-Registration

| Deviation | Reason | Impact on conclusions |
|-----------|--------|----------------------|
| (none) | — | — |

---

## 10. Conclusions

_Summarise the main findings and whether the validation supports use of MASSIVE for the stated target variable._

---

## 11. Artifacts

- `reports/validation/<run_id>/metrics.json`
- `reports/validation/<run_id>/report.md`
- `configs/pvu.yaml` (frozen)
- `pip freeze` output

---

_This report follows PVU-BS v1.0 — see [PVU_BeyondSight_EN.md](PVU_BeyondSight_EN.md)_
