# PVU-BS Benchmark Report

**Run timestamp:** 2026-07-01T06:36:10Z  
**Mode:** `real`  
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
| ets | 0.0400 | 0.0495 | 6.2006 | 1.0000 |
| arima | 0.0147 | 0.0208 | 2.2956 | 1.0000 |
| ridge_lags | 0.0987 | 0.1023 | 15.0358 | 0.6667 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.0425 | 0.0524 | 6.3459 | 0.6667 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.1734 | 0.6934 | ✗ |
| moving_average | 0.1031 | 0.6343 | ✗ |
| ar1 | 0.0906 | 0.6343 | ✗ |
| random_regime | 0.2408 | 0.6934 | ✗ |
| ets | 0.8976 | 0.8976 | ✗ |
| arima | 0.2083 | 0.6934 | ✗ |
| ridge_lags | 0.0981 | 0.6343 | ✗ |

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
| ets | 0.1625 | 0.1929 | 29.9474 | 0.0000 |
| arima | 0.0632 | 0.0739 | 11.6100 | 0.0000 |
| ridge_lags | 0.0571 | 0.0680 | 9.6724 | 0.3333 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.0314 | 0.0365 | 5.5935 | 0.6667 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.7971 | 0.9991 | ✗ |
| moving_average | 0.0842 | 0.5891 | ✗ |
| ar1 | 0.1360 | 0.7569 | ✗ |
| random_regime | 0.4995 | 0.9991 | ✗ |
| ets | 0.1261 | 0.7569 | ✗ |
| arima | 0.2119 | 0.8477 | ✗ |
| ridge_lags | 0.2619 | 0.8477 | ✗ |

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
| ets | 0.2013 | 0.2169 | 43.4946 | 0.0000 |
| arima | 0.1672 | 0.1766 | 35.9408 | 0.0000 |
| ridge_lags | 0.2029 | 0.2074 | 43.1502 | 0.5000 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.0853 | 0.1048 | 18.2241 | 0.7500 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.3824 | 0.7649 | ✗ |
| moving_average | 0.0134 | 0.0803 | ✗ |
| ar1 | 0.0415 | 0.1735 | ✗ |
| random_regime | 0.6413 | 0.7649 | ✗ |
| ets | 0.0347 | 0.1735 | ✗ |
| arima | 0.0415 | 0.1735 | ✗ |
| ridge_lags | 0.0096 | 0.0675 | ✗ |

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
| ets | 0.0080 | 0.0089 | 1.5097 | 1.0000 |
| arima | 0.0610 | 0.0668 | 12.0006 | 1.0000 |
| ridge_lags | 0.1455 | 0.1499 | 28.2451 | 0.5000 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.0640 | 0.0927 | 12.7151 | 0.7500 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.7699 | 1.0000 | ✗ |
| moving_average | 0.0751 | 0.4508 | ✗ |
| ar1 | 0.0811 | 0.4508 | ✗ |
| random_regime | 0.8525 | 1.0000 | ✗ |
| ets | 0.2510 | 1.0000 | ✗ |
| arima | 0.4825 | 1.0000 | ✗ |
| ridge_lags | 0.0455 | 0.3185 | ✗ |

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
| ets | 0.0460 | 0.0674 | 47.5000 | 1.0000 |
| arima | 0.0885 | 0.1003 | 74.1532 | 1.0000 |
| ridge_lags | 0.3587 | 0.3728 | 270.0906 | 0.2500 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.2266 | 0.2357 | 144.1491 | 0.5000 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.5415 | 1.0000 | ✗ |
| moving_average | 0.0466 | 0.2329 | ✗ |
| ar1 | 0.1545 | 0.4636 | ✗ |
| random_regime | 0.6792 | 1.0000 | ✗ |
| ets | 0.0233 | 0.1632 | ✗ |
| arima | 0.0373 | 0.2237 | ✗ |
| ridge_lags | 0.0826 | 0.3306 | ✗ |

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
| ets | 0.0046 | 0.0059 | 1.0666 | 1.0000 |
| arima | 0.0707 | 0.0820 | 16.5715 | 1.0000 |
| ridge_lags | 0.1607 | 0.1665 | 36.5925 | 0.5000 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.0677 | 0.0773 | 14.9978 | 0.7500 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.2601 | 0.7804 | ✗ |
| moving_average | 0.0293 | 0.1870 | ✗ |
| ar1 | 0.0757 | 0.3029 | ✗ |
| random_regime | 0.4627 | 0.9254 | ✗ |
| ets | 0.0328 | 0.1870 | ✗ |
| arima | 0.8099 | 0.9254 | ✗ |
| ridge_lags | 0.0267 | 0.1870 | ✗ |

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
| ets | 0.0623 | 0.0629 | 17.0935 | 1.0000 |
| arima | 0.0293 | 0.0371 | 7.6657 | 1.0000 |
| ridge_lags | 0.0330 | 0.0387 | 9.4255 | 0.2500 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.0123 | 0.0172 | 3.2537 | 0.7500 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.1416 | 0.4748 | ✗ |
| moving_average | 0.1249 | 0.4748 | ✗ |
| ar1 | 0.0854 | 0.4268 | ✗ |
| random_regime | 0.0409 | 0.2456 | ✗ |
| ets | 0.0009 | 0.0063 | ✓ |
| arima | 0.2014 | 0.4748 | ✗ |
| ridge_lags | 0.1187 | 0.4748 | ✗ |

### Turning-point skill

- Precision: N/A
- Recall:    N/A
- F1:        0.0000
- Mean timing error: N/A steps
- GT turning points: 0 | Predicted: 0

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
| ets | 0.0360 | 0.0443 | 5.5988 | 1.0000 |
| arima | 0.0654 | 0.0788 | 10.1452 | 1.0000 |
| ridge_lags | 0.1046 | 0.1172 | 16.0154 | 0.7500 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.1610 | 0.2160 | 25.0303 | 0.7500 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.2435 | 1.0000 | ✗ |
| moving_average | 0.2854 | 1.0000 | ✗ |
| ar1 | 0.3537 | 1.0000 | ✗ |
| random_regime | 0.2858 | 1.0000 | ✗ |
| ets | 0.1940 | 1.0000 | ✗ |
| arima | 0.2073 | 1.0000 | ✗ |
| ridge_lags | 0.2591 | 1.0000 | ✗ |

### Turning-point skill

- Precision: N/A
- Recall:    N/A
- F1:        0.0000
- Mean timing error: N/A steps
- GT turning points: 0 | Predicted: 0

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
| ets | 0.0200 | 0.0210 | 6.3098 | 1.0000 |
| arima | 0.1091 | 0.1209 | 36.1442 | 1.0000 |
| ridge_lags | 0.1960 | 0.2052 | 63.0252 | 0.2500 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.0702 | 0.0789 | 19.8990 | 0.7500 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.1305 | 0.3916 | ✗ |
| moving_average | 0.0328 | 0.2087 | ✗ |
| ar1 | 0.0572 | 0.2289 | ✗ |
| random_regime | 0.1704 | 0.3916 | ✗ |
| ets | 0.0298 | 0.2087 | ✗ |
| arima | 0.2763 | 0.3916 | ✗ |
| ridge_lags | 0.0394 | 0.2087 | ✗ |

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
| ets | 0.0080 | 0.0110 | 3.3714 | 1.0000 |
| arima | 0.0641 | 0.0740 | 28.1550 | 1.0000 |
| ridge_lags | 0.1652 | 0.1742 | 69.4535 | 0.2500 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.0973 | 0.1002 | 37.6142 | 0.7500 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.3646 | 0.7292 | ✗ |
| moving_average | 0.0513 | 0.3076 | ✗ |
| ar1 | 0.1032 | 0.4127 | ✗ |
| random_regime | 0.4080 | 0.7292 | ✗ |
| ets | 0.0095 | 0.0665 | ✗ |
| arima | 0.2370 | 0.7109 | ✗ |
| ridge_lags | 0.0790 | 0.3949 | ✗ |

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
| ets | 0.0160 | 0.0190 | 6.3039 | 1.0000 |
| arima | 0.0532 | 0.0613 | 20.9157 | 1.0000 |
| ridge_lags | 0.1400 | 0.1438 | 52.9147 | 0.2500 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.1349 | 0.1394 | 51.1488 | 0.5000 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.0034 | 0.0218 | ✓ |
| moving_average | 0.0092 | 0.0369 | ✓ |
| ar1 | 0.0866 | 0.0866 | ✗ |
| random_regime | 0.0184 | 0.0369 | ✓ |
| ets | 0.0102 | 0.0369 | ✓ |
| arima | 0.0048 | 0.0240 | ✓ |
| ridge_lags | 0.0031 | 0.0218 | ✓ |

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
| ets | 0.0235 | 0.0334 | 3.2765 | 0.5000 |
| arima | 0.0164 | 0.0219 | 2.2723 | 0.5000 |
| ridge_lags | 0.0691 | 0.0712 | 9.5186 | 0.5000 |

### MASSIVE metrics (test split)

| MAE | RMSE | MAPE (%) | Dir. Acc. |
|-----|------|----------|-----------|
| 0.1212 | 0.1250 | 16.7178 | 0.5000 |

### Diebold–Mariano tests (Holm–Bonferroni adjusted)

| vs Baseline | p-raw | p-adj | Significant |
|-------------|-------|-------|-------------|
| naive | 0.0083 | 0.0579 | ✗ |
| moving_average | 0.0109 | 0.0587 | ✗ |
| ar1 | 0.0212 | 0.0587 | ✗ |
| random_regime | 0.0098 | 0.0587 | ✗ |
| ets | 0.0130 | 0.0587 | ✗ |
| arima | 0.0105 | 0.0587 | ✗ |
| ridge_lags | 0.0149 | 0.0587 | ✗ |

### Turning-point skill

- Precision: N/A
- Recall:    0.0000
- F1:        0.0000
- Mean timing error: N/A steps
- GT turning points: 1 | Predicted: 0

---

_Generated by `benchmarks.runner` — MASSIVE PVU-BS_