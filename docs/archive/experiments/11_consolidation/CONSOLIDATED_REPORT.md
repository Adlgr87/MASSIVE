# Consolidated Benchmark — MASSIVE real vs baselines and EnKF
## Dataset
12 real-world cases in datasets/real_cases (same as prior runs).

## Configurations
- MASSIVE real (heurístico) as in reports/sota_baselines
- EnKF post-process: n_ensemble=32, sigma_obs=0.02, interval=3, seed=42 (reports/enkf_full_i3_s002)

## Aggregate results
- MASSIVE real → MASSIVE+EnKF: mean ΔMAE = +0.0063; paired t-test t=+2.344, p=0.0389 (n=12)
- vs naive: MASSIVE real W/L=9/3, ratio=1.13; MASSIVE+EnKF W/L=9/3, ratio=1.06
- vs moving_average: MASSIVE real W/L=9/3, ratio=0.71; MASSIVE+EnKF W/L=9/3, ratio=0.67
- vs ar1: MASSIVE real W/L=9/3, ratio=0.80; MASSIVE+EnKF W/L=9/3, ratio=0.75
- vs ridge_lags: MASSIVE real W/L=10/2, ratio=0.71; MASSIVE+EnKF W/L=10/2, ratio=0.66
- vs ets: MASSIVE real W/L=3/9, ratio=5.26; MASSIVE+EnKF W/L=4/8, ratio=4.96
- vs arima: MASSIVE real W/L=5/7, ratio=1.95; MASSIVE+EnKF W/L=5/7, ratio=1.81

## Per-case MAE
| Case | MASSIVE | MASSIVE+EnKF | naive | ets | arima | ridge |
|---|---:|---:|---:|---:|---:|---:|
| brazil_election_2022 | 0.0425 | 0.0376 | 0.0850 | 0.0400 | 0.0147 | 0.0987 |
| brexit_referendum_2016 | 0.0314 | 0.0301 | 0.0325 | 0.1625 | 0.0632 | 0.0571 |
| chile_estallido_2019 | 0.0853 | 0.0821 | 0.1180 | 0.2013 | 0.1672 | 0.2029 |
| colombia_paro_2021 | 0.0640 | 0.0658 | 0.0940 | 0.0080 | 0.0610 | 0.1455 |
| egypt_arab_spring_2011 | 0.2266 | 0.1936 | 0.2540 | 0.0460 | 0.0885 | 0.3587 |
| france_gilets_jaunes_2018 | 0.0677 | 0.0640 | 0.0960 | 0.0046 | 0.0707 | 0.1607 |
| germany_pegida_2014 | 0.0123 | 0.0118 | 0.0280 | 0.0623 | 0.0293 | 0.0330 |
| hong_kong_protests_2019 | 0.1610 | 0.1562 | 0.0960 | 0.0360 | 0.0654 | 0.1046 |
| iran_mahsa_amini_2022 | 0.0702 | 0.0675 | 0.1400 | 0.0200 | 0.1091 | 0.1960 |
| myanmar_coup_cdm_2021 | 0.0973 | 0.0865 | 0.1160 | 0.0080 | 0.0641 | 0.1652 |
| south_korea_candlelight_2016 | 0.1349 | 0.1336 | 0.0740 | 0.0160 | 0.0532 | 0.1400 |
| us_election_2020 | 0.1212 | 0.1105 | 0.0320 | 0.0235 | 0.0164 | 0.0691 |

## Limitations
- Short time series (11–15 steps): strong baselines like ETS/ARIMA excel; MASSIVE focuses on mechanistic dynamics, not pure time-series fitting.
- Directional accuracy unchanged in EnKF v0: this phase corrects level more than slope; next iterations may include regime-aware assimilation.
- Linear mapping (a*opinion+b): fair but simple; richer calibration (e.g., constrained regression or CMA-ES on 5–8 params) could reduce bias further.
- No walk-forward CV yet: current split is 70/30; rolling-window validation is planned to check robustness.

## Threat model (misuse/overclaim risks)
- Overclaiming predictive power: ABM is for mechanism/attractor; avoid implying point-forecast leadership.
- Data leakage: mapping/calibration must use train only; report scripts enforce this, but beware manual experiments.
- P-hacking via many knobs: all hyperparameters and outcomes must be pre-registered in the experiment report before large sweeps.
- External validity: wins on these 12 cases do not generalize automatically; document domain and assumptions per case.
