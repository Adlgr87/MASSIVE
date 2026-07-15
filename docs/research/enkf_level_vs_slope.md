# EnKF: level vs slope (B12 research note)

Source: `docs/cards/BENCHMARK.md` (EnKF v0 on 12 real cases).

## Observed behavior

- EnKF post-process improves **MAE** (level / absolute error):
  mean ΔMAE ≈ +0.0063; 11/12 cases improve; paired t-test p≈0.0389.
- **Directional accuracy** (slope / trend sign) remains essentially stable —
  EnKF v0 corrects level bias more than trajectory slope.

## Implications

1. Do **not** claim EnKF improves trend forecasts without a dedicated metric
   (e.g. directional accuracy, slope MAE on first differences).
2. Future assimilation work should experiment with:
   - observing increments / first differences,
   - stronger process models for slope,
   - walk-forward evaluation of directional scores.
3. Linear observation map `a*opinion+b` remains a major bias source.

## Tracking

- Status: **documented research finding** (not a code defect).
- Next engineering: optional metric harness in `benchmarks/` for directional
  accuracy when extending EnKF (out of FASE 5 closeout scope).
