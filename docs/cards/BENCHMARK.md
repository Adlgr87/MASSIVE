# Benchmark Card — MASSIVE (real engine + assimilation)

Summary
- Task: Forecast polarization trajectories on 12 real-world social phenomena.
- Engine: MASSIVE real (heurístico, sin LLM) with optional Ensemble Kalman Filter (EnKF) post-process.
- Baselines: naive, moving_average, AR(1), ridge(lags), ETS, ARIMA.
- Split: 70/30 (train/test), seed=42, PYTHONHASHSEED=42.
- Dataset: datasets/real_cases/* (12 cases, meta.json + timeseries.csv + interventions.json)

Key results (n=12)
- MASSIVE real vs MASSIVE+EnKF: ΔMAE medio +0.0063; 11/12 mejoran; paired t-test p=0.0389.
- Frente a baselines (wins/losses; ratio MAE MASSIVE/baseline):
  - naive: 9/3; 1.06 (EnKF) — mejora vs 1.13 (sin EnKF)
  - moving_average: 9/3; 0.67 (mejora vs 0.71)
  - AR1: 9/3; 0.75 (mejora vs 0.80)
  - ridge_lags: 10/2; 0.66 (mejora vs 0.71)
  - ETS: 4/8; 4.96 (mejora vs 5.26)
  - ARIMA: 5/7; 1.81 (mejora vs 1.95)

Reproducibility
```bash
export PYTHONHASHSEED=42
# Baselines (real engine)
python -m benchmarks.runner --cases datasets/real_cases --real --out reports/sota_baselines --seed 42
# EnKF full run
PYTHONPATH=. python3 experiments/08_enkf_delta/exp_003_enkf.py --cases datasets/real_cases \
  --out reports/enkf_full_i3_s002 --seed 42 --n-ensemble 32 --sigma-obs 0.02 --interval 3
```

Limitations
- Series cortas favorecen ETS/ARIMA; MASSIVE prioriza dinámica mecanística.
- EnKF v0 corrige nivel, no pendiente (directional accuracy estable).
- Mapeo lineal a*opinion+b es simple; calibración más rica podría reducir sesgo.
- Falta walk-forward CV (planeado).

Claims
- Benchmark comparativo honesto y reproducible; sin autodenominar “SOTA”.
- Mejoras significativas con EnKF en MAE; reducción de brecha frente a ETS/ARIMA.
