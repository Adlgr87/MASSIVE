# Plantilla de Reporte de Validación PVU-BS (Español)

> Completar este documento tras la corrida.  
> Versión en inglés: [validation_report_template_EN.md](validation_report_template_EN.md)

---

## 1. Identificación de la Corrida

| Campo | Valor |
|-------|-------|
| ID de corrida | `<!-- ej. pvu_run_001 -->` |
| Ref de pre-registro | `<!-- link/SHA al commit de pre-reg -->` |
| Fecha de corrida | `<!-- YYYY-MM-DD -->` |
| Commit Git (código) | `<!-- SHA en el momento de la corrida -->` |
| Modo | `<!-- offline / llm -->` |
| Semilla / PYTHONHASHSEED | `<!-- ambos valores -->` |
| Ruta `metrics.json` | `reports/validation/<run_id>/metrics.json` |

---

## 2. Resumen de Casos

| Caso | N_total | N_train | N_test | Cluster | Omitido |
|------|---------|---------|--------|---------|---------|
| sample_case_001 | — | — | — | — | — |
| sample_case_002 | — | — | — | — | — |

> Reemplazar con los valores reales de `metrics.json`.

---

## 3. Métricas de Baselines (agregadas sobre todos los casos)

| Baseline | MAE Medio | RMSE Medio | Exactitud Dir. Media |
|----------|---------|-----------|----------------|
| naive | | | |
| moving_average | | | |
| ar1 | | | |
| random_regime | | | |

---

## 4. Métricas de MASSIVE

| Métrica | Valor |
|---------|-------|
| MAE Medio | |
| RMSE Medio | |
| MAPE Medio (%) | |
| Exactitud Direccional Media | |
| ΔMAE vs naive | |
| ΔRMSE vs naive | |

---

## 5. Tests Estadísticos (ajustados por Holm–Bonferroni)

| vs Baseline | Casos significativos (p_adj < 0.05) | p_adj Medio |
|-------------|-------------------------------------|-----------|
| naive | / N | |
| moving_average | / N | |
| ar1 | / N | |
| random_regime | / N | |

**Hipótesis principal:** `<!-- SOPORTADA / NO SOPORTADA -->`  
_Justificación:_

---

## 6. Habilidad en Puntos de Giro (TPS)

| Métrica | Valor |
|---------|-------|
| Precisión Media | |
| Recall Medio | |
| F1 Medio | |
| Error Medio de Timing (pasos) | |

---

## 7. Consistencia LLM (si modo LLM)

| Métrica | Valor |
|---------|-------|
| N corridas independientes | |
| CV del MAE entre corridas | |
| Resultado marcado (CV > 0.15)? | |

---

## 8. Nivel PVU Alcanzado

- [ ] Bronce (N ≥ 10, DM vs naive p_adj < 0.05, ΔMAE > 0)
- [ ] Plata (N ≥ 20, DM vs todos los baselines p_adj < 0.05, TPS F1 ≥ 0.50)
- [ ] Oro (N ≥ 30, replicación externa, TPS F1 ≥ 0.70)
- [ ] Ninguno

---

## 9. Desviaciones del Pre-Registro

| Desviación | Razón | Impacto en conclusiones |
|-----------|-------|------------------------|
| (ninguna) | — | — |

---

## 10. Conclusiones

_Resumir los hallazgos principales y si la validación respalda el uso de MASSIVE para la variable objetivo declarada._

---

## 11. Artefactos

- `reports/validation/<run_id>/metrics.json`
- `reports/validation/<run_id>/report.md`
- `configs/pvu.yaml` (congelado)
- Salida de `pip freeze`

---

_Este reporte sigue PVU-BS v1.0 — ver [PVU_BeyondSight_ES.md](PVU_BeyondSight_ES.md)_
