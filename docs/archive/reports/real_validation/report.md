# PVU-BS Benchmark Report

**Run timestamp:** 2026-06-30T19:22:50Z  
**Mode:** `offline`  
**Seed:** `42`  
**Cases evaluated:** 12  

> ⚠️ **Sample-case disclaimer:** results from `sample_case_*` are
> synthetic and do NOT constitute PVU real-validation evidence.
> Real validation requires N ≥ 10 independent cases
> (see `docs/validation/PVU_MASSIVE_EN.md`).

---

## Case: `brazil_election_2022`
- **N total / train / test:** 12 / 8 / 4
- **Cluster ID:** `n/a`

### Baseline metrics (test split)

| Baseline | MAE | RMSE | MAPE (%) | Dir. Acc. |
|----------|-----|------|----------|-----------|
| naive | 0.0850 | 0.0892 | 12.9673 | 0.0000 |
| moving_average | 0.0975 | 0.1011 | 14.8501 | 0.0000 |
| ar1 | 0.1126 | 0.1183 | 17.1870 | 0.0000 |
| random_regime | 0.0901 | 0.1002 | 13.8197 | 0.3333 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.1146 | 0.1224 | 17.5093 | 0.3333 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.1068 | 0.3205 | ✗ |
| moving_average | 0.1875 | 0.3750 | ✗ |
| ar1 | 0.6027 | 0.6027 | ✗ |
| random_regime | 0.0235 | 0.0940 | ✗ |

### Turning-point skill

- Precision: N/A
- Recall:    N/A
- F1:        0.0000
- Mean timing error: N/A steps
- GT turning points: 0 | Predicted: 0

## Case: `brexit_referendum_2016`
- **N total / train / test:** 11 / 7 / 4
- **Cluster ID:** `n/a`

### Baseline metrics (test split)

| Baseline | MAE | RMSE | MAPE (%) | Dir. Acc. |
|----------|-----|------|----------|-----------|
| naive | 0.0325 | 0.0391 | 5.8612 | 0.0000 |
| moving_average | 0.1000 | 0.1066 | 17.2724 | 0.0000 |
| ar1 | 0.3259 | 0.3867 | 60.0401 | 0.0000 |
| random_regime | 0.0428 | 0.0503 | 7.8055 | 0.3333 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.2175 | 0.2784 | 40.4726 | 0.0000 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.1689 | 0.4999 | ✗ |
| moving_average | 0.2455 | 0.4999 | ✗ |
| ar1 | 0.1015 | 0.4059 | ✗ |
| random_regime | 0.1666 | 0.4999 | ✗ |

### Turning-point skill

- Precision: N/A
- Recall:    N/A
- F1:        0.0000
- Mean timing error: N/A steps
- GT turning points: 0 | Predicted: 0

## Case: `chile_estallido_2019`
- **N total / train / test:** 15 / 10 / 5
- **Cluster ID:** `n/a`

### Baseline metrics (test split)

| Baseline | MAE | RMSE | MAPE (%) | Dir. Acc. |
|----------|-----|------|----------|-----------|
| naive | 0.1180 | 0.1251 | 25.3918 | 0.0000 |
| moving_average | 0.1880 | 0.1926 | 40.0209 | 0.0000 |
| ar1 | 0.1672 | 0.1766 | 35.9378 | 0.0000 |
| random_regime | 0.1095 | 0.1304 | 23.3820 | 0.5000 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.1717 | 0.1917 | 37.2792 | 0.5000 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.0806 | 0.3222 | ✗ |
| moving_average | 0.9660 | 0.9660 | ✗ |
| ar1 | 0.3890 | 0.7780 | ✗ |
| random_regime | 0.1494 | 0.4482 | ✗ |

### Turning-point skill

- Precision: N/A
- Recall:    N/A
- F1:        0.0000
- Mean timing error: N/A steps
- GT turning points: 0 | Predicted: 0

## Case: `colombia_paro_2021`
- **N total / train / test:** 15 / 10 / 5
- **Cluster ID:** `n/a`

### Baseline metrics (test split)

| Baseline | MAE | RMSE | MAPE (%) | Dir. Acc. |
|----------|-----|------|----------|-----------|
| naive | 0.0940 | 0.1005 | 18.4043 | 0.0000 |
| moving_average | 0.1365 | 0.1411 | 26.5207 | 0.0000 |
| ar1 | 0.1316 | 0.1402 | 25.7512 | 0.0000 |
| random_regime | 0.0890 | 0.1014 | 17.3584 | 0.5000 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.1659 | 0.1679 | 31.9694 | 0.5000 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.0007 | 0.0029 | ✓ |
| moving_average | 0.0166 | 0.0332 | ✓ |
| ar1 | 0.0435 | 0.0435 | ✓ |
| random_regime | 0.0093 | 0.0280 | ✓ |

### Turning-point skill

- Precision: N/A
- Recall:    N/A
- F1:        0.0000
- Mean timing error: N/A steps
- GT turning points: 0 | Predicted: 0

## Case: `egypt_arab_spring_2011`
- **N total / train / test:** 14 / 9 / 5
- **Cluster ID:** `n/a`

### Baseline metrics (test split)

| Baseline | MAE | RMSE | MAPE (%) | Dir. Acc. |
|----------|-----|------|----------|-----------|
| naive | 0.2540 | 0.2716 | 199.2143 | 0.0000 |
| moving_average | 0.3915 | 0.4031 | 290.6409 | 0.0000 |
| ar1 | 0.3323 | 0.3542 | 259.6510 | 0.0000 |
| random_regime | 0.2432 | 0.2703 | 183.8673 | 0.5000 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.3844 | 0.3964 | 287.5700 | 0.7500 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.0061 | 0.0242 | ✓ |
| moving_average | 0.6492 | 0.6492 | ✗ |
| ar1 | 0.0371 | 0.1113 | ✗ |
| random_regime | 0.0828 | 0.1656 | ✗ |

### Turning-point skill

- Precision: N/A
- Recall:    N/A
- F1:        0.0000
- Mean timing error: N/A steps
- GT turning points: 0 | Predicted: 0

## Case: `france_gilets_jaunes_2018`
- **N total / train / test:** 15 / 10 / 5
- **Cluster ID:** `n/a`

### Baseline metrics (test split)

| Baseline | MAE | RMSE | MAPE (%) | Dir. Acc. |
|----------|-----|------|----------|-----------|
| naive | 0.0960 | 0.1051 | 22.2054 | 0.0000 |
| moving_average | 0.1560 | 0.1617 | 35.5369 | 0.0000 |
| ar1 | 0.1378 | 0.1489 | 31.7803 | 0.0000 |
| random_regime | 0.0905 | 0.1063 | 20.8512 | 0.5000 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.1227 | 0.1379 | 28.5508 | 0.2500 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.1105 | 0.3315 | ✗ |
| moving_average | 0.0330 | 0.1321 | ✗ |
| ar1 | 0.1227 | 0.3315 | ✗ |
| random_regime | 0.3124 | 0.3315 | ✗ |

### Turning-point skill

- Precision: N/A
- Recall:    N/A
- F1:        0.0000
- Mean timing error: N/A steps
- GT turning points: 0 | Predicted: 0

## Case: `germany_pegida_2014`
- **N total / train / test:** 15 / 10 / 5
- **Cluster ID:** `n/a`

### Baseline metrics (test split)

| Baseline | MAE | RMSE | MAPE (%) | Dir. Acc. |
|----------|-----|------|----------|-----------|
| naive | 0.0280 | 0.0346 | 7.5862 | 0.0000 |
| moving_average | 0.0380 | 0.0431 | 10.9377 | 0.0000 |
| ar1 | 0.0344 | 0.0398 | 9.6413 | 0.0000 |
| random_regime | 0.0298 | 0.0351 | 8.0020 | 0.5000 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.0478 | 0.0531 | 13.6203 | 0.5000 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.1708 | 0.4002 | ✗ |
| moving_average | 0.0592 | 0.2369 | ✗ |
| ar1 | 0.1334 | 0.4002 | ✗ |
| random_regime | 0.2017 | 0.4002 | ✗ |

### Turning-point skill

- Precision: 0.0000
- Recall:    N/A
- F1:        0.0000
- Mean timing error: N/A steps
- GT turning points: 0 | Predicted: 1

## Case: `hong_kong_protests_2019`
- **N total / train / test:** 15 / 10 / 5
- **Cluster ID:** `n/a`

### Baseline metrics (test split)

| Baseline | MAE | RMSE | MAPE (%) | Dir. Acc. |
|----------|-----|------|----------|-----------|
| naive | 0.0960 | 0.1097 | 14.7524 | 0.0000 |
| moving_average | 0.1160 | 0.1276 | 17.6947 | 0.0000 |
| ar1 | 0.1352 | 0.1507 | 20.6798 | 0.0000 |
| random_regime | 0.0921 | 0.1070 | 14.0819 | 0.5000 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.1363 | 0.1580 | 20.9413 | 0.5000 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.0422 | 0.1687 | ✗ |
| moving_average | 0.0705 | 0.2114 | ✗ |
| ar1 | 0.3029 | 0.3029 | ✗ |
| random_regime | 0.0788 | 0.2114 | ✗ |

### Turning-point skill

- Precision: 0.0000
- Recall:    N/A
- F1:        0.0000
- Mean timing error: N/A steps
- GT turning points: 0 | Predicted: 1

## Case: `iran_mahsa_amini_2022`
- **N total / train / test:** 14 / 9 / 5
- **Cluster ID:** `n/a`

### Baseline metrics (test split)

| Baseline | MAE | RMSE | MAPE (%) | Dir. Acc. |
|----------|-----|------|----------|-----------|
| naive | 0.1400 | 0.1522 | 45.9489 | 0.0000 |
| moving_average | 0.2050 | 0.2135 | 65.7128 | 0.0000 |
| ar1 | 0.2032 | 0.2182 | 66.2386 | 0.0000 |
| random_regime | 0.1321 | 0.1522 | 42.5493 | 0.5000 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.2091 | 0.2389 | 69.4566 | 0.2500 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.0445 | 0.1778 | ✗ |
| moving_average | 0.2568 | 0.3979 | ✗ |
| ar1 | 0.1989 | 0.3979 | ✗ |
| random_regime | 0.0730 | 0.2190 | ✗ |

### Turning-point skill

- Precision: N/A
- Recall:    N/A
- F1:        0.0000
- Mean timing error: N/A steps
- GT turning points: 0 | Predicted: 0

## Case: `myanmar_coup_cdm_2021`
- **N total / train / test:** 15 / 10 / 5
- **Cluster ID:** `n/a`

### Baseline metrics (test split)

| Baseline | MAE | RMSE | MAPE (%) | Dir. Acc. |
|----------|-----|------|----------|-----------|
| naive | 0.1160 | 0.1282 | 49.9931 | 0.0000 |
| moving_average | 0.1810 | 0.1891 | 75.6498 | 0.0000 |
| ar1 | 0.1677 | 0.1830 | 71.8412 | 0.0000 |
| random_regime | 0.1102 | 0.1289 | 47.2605 | 0.5000 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.1978 | 0.2158 | 84.7464 | 0.0000 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.0322 | 0.1288 | ✗ |
| moving_average | 0.1633 | 0.1633 | ✗ |
| ar1 | 0.0424 | 0.1288 | ✗ |
| random_regime | 0.0551 | 0.1288 | ✗ |

### Turning-point skill

- Precision: N/A
- Recall:    N/A
- F1:        0.0000
- Mean timing error: N/A steps
- GT turning points: 0 | Predicted: 0

## Case: `south_korea_candlelight_2016`
- **N total / train / test:** 14 / 9 / 5
- **Cluster ID:** `n/a`

### Baseline metrics (test split)

| Baseline | MAE | RMSE | MAPE (%) | Dir. Acc. |
|----------|-----|------|----------|-----------|
| naive | 0.0740 | 0.0809 | 28.6431 | 0.0000 |
| moving_average | 0.1240 | 0.1282 | 47.0207 | 0.0000 |
| ar1 | 0.1236 | 0.1322 | 47.4921 | 0.0000 |
| random_regime | 0.0703 | 0.0809 | 27.0720 | 0.5000 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.1417 | 0.1472 | 53.7270 | 0.2500 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.0076 | 0.0283 | ✓ |
| moving_average | 0.0611 | 0.1222 | ✗ |
| ar1 | 0.0833 | 0.1222 | ✗ |
| random_regime | 0.0071 | 0.0283 | ✓ |

### Turning-point skill

- Precision: N/A
- Recall:    N/A
- F1:        0.0000
- Mean timing error: N/A steps
- GT turning points: 0 | Predicted: 0

## Case: `us_election_2020`
- **N total / train / test:** 14 / 9 / 5
- **Cluster ID:** `n/a`

### Baseline metrics (test split)

| Baseline | MAE | RMSE | MAPE (%) | Dir. Acc. |
|----------|-----|------|----------|-----------|
| naive | 0.0320 | 0.0363 | 4.3783 | 0.0000 |
| moving_average | 0.0570 | 0.0595 | 7.8429 | 0.0000 |
| ar1 | 0.0357 | 0.0494 | 4.9795 | 0.5000 |
| random_regime | 0.0329 | 0.0370 | 4.5058 | 0.5000 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.0291 | 0.0434 | 4.0687 | 0.5000 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.7500 | 1.0000 | ✗ |
| moving_average | 0.4312 | 1.0000 | ✗ |
| ar1 | 0.1048 | 0.4192 | ✗ |
| random_regime | 0.7603 | 1.0000 | ✗ |

### Turning-point skill

- Precision: N/A
- Recall:    0.0000
- F1:        0.0000
- Mean timing error: N/A steps
- GT turning points: 1 | Predicted: 0

---

_Generated by `benchmarks.runner` — MASSIVE PVU-BS_