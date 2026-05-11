# PVU-BS Pre-Registration Template (English)

> Fill this document and commit it to the repository **before** breaking the test seal.  
> Spanish version: [preregistration_template_ES.md](preregistration_template_ES.md)

---

## 1. Identification

| Field | Value |
|-------|-------|
| Run ID | `<!-- e.g. pvu_run_001 -->` |
| Date pre-registered | `<!-- YYYY-MM-DD -->` |
| Registered by | `<!-- GitHub username -->` |
| Git commit (codebase) | `<!-- SHA at registration time -->` |

---

## 2. Hypothesis

> Copy from PVU-BS § 4.1 or state a more specific variant:

_MASSIVE produces significantly lower MAE on the held-out test set compared to the naive baseline, after Holm–Bonferroni correction (α = 0.05)._

Primary metric: `<!-- MAE / RMSE / TPS F1 / … -->`

---

## 3. Data

| Field | Value |
|-------|-------|
| Cases folder | `datasets/pvu_cases/` |
| N cases | `<!-- total number -->` |
| Cluster IDs | `<!-- list or "none" -->` |
| Date range | `<!-- start – end -->` |
| Source | `<!-- synthetic / Reddit / … -->` |
| License | `<!-- CC0 / CC-BY / … -->` |

**Independence verification:**  
_Explain how cases satisfy the independence criterion (§ 2.1)._

---

## 4. Model Configuration (frozen)

| Parameter | Value |
|-----------|-------|
| `configs/pvu.yaml` SHA | `<!-- git hash of config file -->` |
| Seed | `<!-- integer -->` |
| PYTHONHASHSEED | `<!-- integer -->` |
| Mode | `<!-- offline / llm -->` |
| LLM provider + model | `<!-- if llm mode; else "n/a" -->` |
| Temperature | `<!-- if llm mode; else "n/a" -->` |
| Python version | `<!-- e.g. 3.11.x -->` |
| Key package versions | `<!-- numpy X.Y, scipy X.Y, … -->` |

---

## 5. Analysis Plan

- Train/test split ratio: `<!-- e.g. 70/30 -->` (set in `configs/pvu.yaml`)
- Statistical test: Diebold–Mariano, two-sided, squared-error loss
- Multiple-comparison correction: Holm–Bonferroni across all baseline × case comparisons
- Effect sizes to report: ΔMAE, ΔRMSE, directional accuracy lift, TPS F1
- Turning-point detection: `order=__`, `min_prominence=__`, `tolerance=__`

**Exclusion criteria** (pre-specified; no cases may be excluded after looking at test metrics):

- _e.g. cases with fewer than 10 test observations are automatically skipped by the runner_

---

## 6. Anti-Leakage Declaration

I confirm that at the time of pre-registration:

- [ ] I have not looked at test-split metrics or plots.
- [ ] Model parameters and prompts are frozen (see SHA above).
- [ ] No cases were selected or excluded based on expected performance.
- [ ] The runner will be executed once; results will be reported as-is.

---

## 7. Deviations Log

_Fill after the run if anything deviated from the pre-registration:_

| Deviation | Reason | Impact |
|-----------|--------|--------|
| (none) | — | — |

---

_This template follows PVU-BS v1.0 — see [PVU_BeyondSight_EN.md](PVU_BeyondSight_EN.md)_
