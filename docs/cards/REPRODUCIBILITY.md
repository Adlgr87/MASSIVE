# Reproducibility Card — MASSIVE (real engine)

Environment
- Python 3.12
- OS: Linux x86_64
- Dependencies: see requirements.txt (added: statsmodels, scikit-learn)
- Determinism: PYTHONHASHSEED=42; MASSIVE seeds internal RNGs; EnKF seeds ensemble RNG

Data
- datasets/real_cases/<case>/{meta.json, timeseries.csv, interventions.json}
- 12 cases: Chile 2019, USA 2020, Brexit 2016, Brazil 2022, Hong Kong 2019, France 2018, Colombia 2021, Egypt 2011, Iran 2022, South Korea 2016, Germany 2014, Myanmar 2021

Commands
```bash
export PYTHONHASHSEED=42
# Baselines (real engine)
python -m benchmarks.runner --cases datasets/real_cases --real --out reports/sota_baselines --seed 42
# EnKF full run
PYTHONPATH=. python3 experiments/08_enkf_delta/exp_003_enkf.py --cases datasets/real_cases \
  --out reports/enkf_full_i3_s002 --seed 42 --n-ensemble 32 --sigma-obs 0.02 --interval 3
```

Artifacts
- reports/sota_baselines/{metrics.json, report.md}
- reports/enkf_full_i3_s002/{metrics_pre.json, metrics_post.json, delta.json, report.md}
- experiments/11_consolidation/CONSOLIDATED_REPORT.md

Assurance
- No network calls in --real mode (heurístico); CI uses --offline proxy explicitly
- Mapping train-only (no leakage); paired tests with significance reported
- All scripts idempotent; outputs versioned by folder
