# ROADMAP SOTA — MASSIVE v1.0

> **De "aceptable" a "SOTA defendible" en un nicho acotado:**
> Simulación social mecanística con captura de atractor, asimilación de
> observaciones y validación empírica multi-caso.

**Fecha:** 2026-06-30
**Estado actual:** v0.9 (aceptable con gaps documentados)
**Estado objetivo:** v1.0 SOTA-defendible
**Autor del roadmap:** Agente de programación + investigación aplicada
**Branch de trabajo:** `sota-roadmap/v1`

---

## ⚠️ HALLAZGO CRÍTICO (leer antes de planear)

Durante la auditoría previa a este roadmap se descubrió que **la evaluación
emprírica de los 12 casos reales NO se ejecutó contra el motor MASSIVE real,
sino contra un PROXY determinista**. El proxy está implementado en
`benchmarks/runner.py:51-82` (`_massive_offline_forecast`) y consiste en:

```
AR(1) trend + ruido gausiano con std amortiguado
   ↓
(nada del motor real: ni HK, ni Sznajd, ni energy engine, ni multilayer, ni EnKF)
```

El motor real (`simulator.py` + `massive_engine.py` + `multilayer_engine.py`)
solo se invoca si la variable `OPENROUTER_API_KEY` u `OPENAI_API_KEY` está
presente. En modo offline (el usado en los 12 casos) se usa el proxy.

**Implicaciones:**
1. Las 11/12 derrotas frente a naive en MAE son del PROXY, no del motor real.
2. El EnKF (`massive_core/data_assimilation/kalman.py`, 289 líneas) existe
   pero **nunca se ejecutó** sobre los 12 casos.
3. La directional accuracy "9/12" tampoco es de MASSIVE real, es del proxy.
4. El `cluster_id` está en `unknown` para los 12 casos — el régimen dinámico
   no se propaga al runner.

**Decisión:** este roadmap parte de cero en lo que respecta a validación del
motor real. El proxy se mantiene como baseline de control (degradación
graceful cuando no hay LLM), pero el benchmark principal usa el motor real.

---

## 1. Resumen ejecutivo

| Concepto | Estado actual | Estado objetivo |
|---|---|---|
| Motor MASSIVE evaluado empíricamente | ❌ Solo proxy | ✅ Motor real + EnKF + ablations |
| MAE vs naive (n=12 reales) | +0.064 peor (p=0.0012) | Empate o superior en 8/12 |
| Directional accuracy | 0.36 (proxy) | ≥0.45 (motor real + asimilación) |
| Baselines comparados | 4 (naive, AR1, MA, random) | 7+ (añadir ETS, ARIMA, threshold, ML) |
| Asimilación (EnKF) en benchmark | ❌ No integrado | ✅ Δ pre/post medido en 12 casos |
| Ablations componentes | ❌ No hechas | ✅ 7 ablations con efecto medido |
| Calibración cuantitativa | Manual por región | CMA-ES / Optuna en 5-8 parámetros |
| Out-of-sample validation | Train/test split fijo | Walk-forward k-fold |

**Nicho SOTA defendible propuesto:**
> "ABM social con asimilación de observaciones para captura temprana de
> cambio de régimen en series de polarización de longitud media (10-30
> timesteps), con calibración automática restringida y benchmarks contra
> baselines estadísticos estándar."

**Lo que NO se afirma:**
- ❌ "Mejor predictor general" — el proxy no lo es, y MASSIVE tampoco.
- ❌ "SOTA en MAE" — no realista para ABM sin observations frecuentes.
- ❌ "Sustituye a encuestas reales" — no, las encuestas son ground truth.

---

## 2. Roadmap 3 horizontes

### Horizonte 1 — "Cimientos SOTA" (4 semanas, P0)
**Objetivo:** benchmark del motor real comparable y honesto.

| # | Ticket | Semana |
|---|---|---|
| 1.1 | Integrar `simulator.simular()` como predictor real en `runner.py` (no solo proxy) | S1 |
| 1.2 | Propagar `cluster_id` desde `interventions.json` al runner | S1 |
| 1.3 | Añadir baselines ETS, ARIMA, threshold logistic, ML tabular (Ridge con lags) | S1-S2 |
| 1.4 | Métricas: añadir CRPS, interval score, energy distance (no solo MAE) | S2 |
| 1.5 | Calibrar el motor real con `seed=42` y documentar sensibilidad cross-seed | S2 |
| 1.6 | Benchmark honesto: motor real vs 7 baselines en 12 casos → tabla paper-ready | S3 |
| 1.7 | **DECISIÓN GO/NO-GO** basada en resultados de 1.6 | S4 |

**Criterio de éxito H1:**
- MASSIVE real ejecutado y comparado vs 7 baselines en los 12 casos
- Al menos 1 baseline estadístico estándar (ETS/ARIMA) está en la comparación
- MAE del motor real < MAE del proxy (porque el proxy es solo AR(1))

### Horizonte 2 — "Asimilación y Calibración" (6 semanas, P1)
**Objetivo:** demostrar que la asimilación mejora MASSIVE real.

| # | Ticket | Semana |
|---|---|---|
| 2.1 | Integrar `EnsembleKalmanFilter` con `simulator.simular()` como `model_step` | S5 |
| 2.2 | Protocolo de asimilación: observar cada K pasos, inyectar ruido obs. | S5-S6 |
| 2.3 | Δ pre/post asimilación en los 12 casos (paired t-test + bootstrap CI) | S6 |
| 2.4 | Sensibilidad al ruido observacional (σ_obs ∈ {0.01, 0.05, 0.10, 0.20}) | S7 |
| 2.5 | Calibración restringida con CMA-ES sobre 5-8 parámetros top-sensitivity | S7-S8 |
| 2.6 | Walk-forward k-fold validation (k=3) en lugar de split fijo 70/30 | S8 |
| 2.7 | **DECISIÓN GO/NO-GO** basada en asimilación | S9 |

**Criterio de éxito H2:**
- EnKF + MASSIVE real mejora MAE vs MASSIVE sin EnKF en ≥8/12 casos
- Mejora estadísticamente significativa (p<0.05 con Holm-Bonferroni)
- Direccional accuracy con EnKF ≥0.45 en 8/12 casos

### Horizonte 3 — "Ablations y claims" (4 semanas, P2)
**Objetivo:** empaquetado científico defendible.

| # | Ticket | Semana |
|---|---|---|
| 3.1 | Ablations: {sin LLM selector, sin homofilia, sin confirmation bias, sin energy engine, sin multilayer, sin Factbook, sin EnKF} | S10-S11 |
| 3.2 | Contribución marginal por componente (shap value o leave-one-out) | S11 |
| 3.3 | Model card + benchmark card + reproducibility card | S12 |
| 3.4 | Tabla paper-ready + figuras (matplotlib publication style) | S12 |
| 3.5 | Threat model y error taxonomy | S13 |
| 3.6 | Release v1.0 con tag y CHANGELOG | S13 |

**Criterio de éxito H3:**
- Cada componente tiene un % de contribución medido
- Hay un componente cuya remoción **empeora significativamente** (≥1 componente)
- Cards públicos en `docs/cards/`
- Release v1.0 taggeado en git

---

## 3. Matriz de brechas: Estado actual vs SOTA

| # | Brecha | Estado actual | Estado SOTA | Severidad | Esfuerzo |
|---|---|---|---|---|---|
| G1 | Motor real no evaluado | Proxy AR(1) | `simulator.simular()` en runner | **CRÍTICA** | Bajo (2-3 días) |
| G2 | EnKF no integrado al benchmark | Código existe, no usado | Δ pre/post medido en 12 casos | **CRÍTICA** | Medio (1 sem) |
| G3 | cluster_id no se propaga | "unknown" en 12/12 | Régimen dinámico en runner | Alta | Bajo (1 día) |
| G4 | Baseline débil contra naive | 4 baselines simples | 7+ incluyendo ETS/ARIMA | Alta | Bajo (3 días) |
| G5 | Solo MAE/RMSE/mape | Sin CRPS ni interval score | Distribución completa de predicción | Media | Bajo (2 días) |
| G6 | Calibración manual | 43 parámetros hard-coded | CMA-ES sobre 5-8 sensibles | Media | Medio (2 sem) |
| G7 | Sin walk-forward CV | Split 70/30 fijo | k-fold con ventana móvil | Media | Bajo (3 días) |
| G8 | Sin ablations | No medidas | Cada componente medido | Media | Medio (1 sem) |
| G9 | Sin claim defendible | "Publishable" (eliminado) | Nicho acotado y honesto | Baja | Bajo (ya hecho) |
| G10 | Sin cards públicos | README + docs dispersos | Model/Benchmark/Repro cards | Baja | Bajo (1 sem) |

**Leyenda severidad:** CRÍTICA = bloquea H1; Alta = bloquea H2; Media = nice-to-have.

---

## 4. Backlog priorizado (Impacto × Esfuerzo × Riesgo)

### Ticket 1 — P0, IMPACTO MÁXIMO, esfuerzo bajo
**Congelar benchmark del motor real en los 12 casos**
- **Diagnóstico:** El benchmark actual usa proxy (AR(1) + ruido). Las cifras no
  son honestas sobre MASSIVE.
- **Hipótesis:** El motor real (`simulator.simular()`) tiene acceso a la
  estructura completa de cada caso (cultural profile, intervention schedule,
  Factbook data). Por lo tanto, debería ganar al proxy trivial.
- **Plan:**
  - Modificar `_massive_offline_forecast` para invocar `simular()` con
    parámetros derivados del case meta
  - Mantener proxy como fallback cuando el motor falle
  - Re-ejecutar 12 casos con motor real
- **Experimento:**
  - Dataset: `datasets/real_cases/*` (12 casos)
  - Seed: 42
  - Baselines: 4 actuales + motor real
  - Métrica: MAE, RMSE, MAPE, dir_acc
  - Test: paired t-test MASSIVE_real vs MASSIVE_proxy
  - **Criterio de éxito:** MASSIVE_real MAE < MASSIVE_proxy MAE en ≥9/12 casos
- **Riesgo de regresión:** Bajo — es un benchmark nuevo, no toca simulador.
- **Riesgo de no-determinismo:** Bajo — `simular()` ya es determinista con seed.
- **Esfuerzo:** 2-3 días.
- **Reversión:** Trivial (mantener `--proxy` flag).

### Ticket 2 — P0, IMPACTO ALTO, esfuerzo bajo
**Propagar cluster_id del case meta al runner**
- **Diagnóstico:** `cluster_id` está en `unknown` para los 12 casos. El régimen
  dinámico (polarization_spike, contagion_sir, etc.) no se usa.
- **Hipótesis:** Si el runner sabe el régimen, puede ajustar hiperparámetros
  del motor (e.g., β en SIR, ε en HK) sin reentrenar.
- **Plan:**
  - Asegurar que `generate_real_cases.py` escribe `cluster_id` en `meta.json`
  - `evaluate_case` lee `cluster_id` y lo pasa al predictor MASSIVE
- **Criterio de éxito:** `cluster_id` no es "unknown" en los 12 casos.
- **Esfuerzo:** 1 día.
- **Impacto marginal esperado:** Bajo por sí solo, pero habilita Ticket 5.

### Ticket 3 — P1, IMPACTO ALTO, esfuerzo medio
**Añadir baselines estadísticos estándar (ETS, ARIMA, threshold)**
- **Diagnóstico:** Las 4 baselines actuales (naive, AR(1), MA, random) son
  demasiado simples. Falta comparación con métodos estándar.
- **Hipótesis:** ETS y ARIMA pueden ganar a MASSIVE real en MAE. Si pasan, el
  claim SOTA debe ser sobre dirección, no MAE.
- **Plan:**
  - Añadir `ETSBaseline` (statsmodels ExponentialSmoothing)
  - Añadir `ARIMABaseline` (auto_arima o (1,1,1) fijo)
  - Añadir `ThresholdLogisticBaseline` (ajuste sigmoid a ventana de 3 puntos)
  - Documentar parámetros de cada baseline
- **Criterio de éxito:** 7 baselines ejecutan sin error en 12 casos.
- **Esfuerzo:** 3-4 días.
- **Dependencia:** statsmodels en requirements.

### Ticket 4 — P1, IMPACTO CRÍTICO, esfuerzo medio
**Integrar EnKF y medir Δ asimilación en 12 casos**
- **Diagnóstico:** EnKF existe (289 líneas) pero no se usa nunca en benchmark.
- **Hipótesis:** Inyectar observaciones cada 3-5 pasos reduce MAE en ≥8/12
  casos respecto a no-asimilar.
- **Plan:**
  - Envolver `simular()` como `model_step` callable del EnsembleKalmanFilter
  - Estrategia: ensemble de 32 miembros, observación cada 5 pasos, σ_obs=0.05
  - Ejecutar 12 casos × 2 modos (con/sin EnKF)
  - Comparar MAE, RMSE, dir_acc, turning_point F1
- **Experimento:**
  - n_ensemble: {16, 32, 64} (sweep)
  - σ_obs: {0.01, 0.05, 0.10} (sweep)
  - observation_interval: {3, 5, 10} pasos
  - **Criterio de éxito:** ΔMAE = MAE_noEnKF - MAE_EnKF > 0 en ≥8/12 casos,
    paired t-test p<0.05 con Holm-Bonferroni
- **Esfuerzo:** 1 semana.
- **Riesgo de no-determinismo:** Medio — EnKF añade ruido. Usar seed fija.
- **Dependencia:** Que Ticket 1 (motor real en runner) esté hecho.

### Ticket 5 — P2, IMPACTO ALTO, esfuerzo alto
**Calibración restringida con CMA-ES sobre top-sensitivity params**
- **Diagnóstico:** Los 43 parámetros empíricos están calibrados manualmente.
  No hay evidencia de que sean los valores óptimos.
- **Hipótesis:** Optimización sobre 5-8 parámetros top-sensibles (β, σ, α_HK,
  α_Sznajd, etc.) puede mejorar MAE out-of-sample ≥10%.
- **Plan:**
  - Análisis de sensibilidad global (Sobol o Morris) sobre 43 parámetros
  - Seleccionar top 5-8
  - CMA-ES (cma library) con walk-forward k-fold (k=3) en los 12 casos
  - Train: primeros 8 timesteps, test: restantes
- **Criterio de éxito:** MAE out-of-sample calibrado < MAE hard-coded
  en ≥7/12 casos
- **Esfuerzo:** 2 semanas.
- **Riesgo:** Overfitting a los 12 casos. Mitigación: k-fold + reservar 2
  casos como holdout final.
- **Dependencia:** Tickets 1, 2, 3 completos.

### Ticket 6 — P2, IMPACTO MEDIO, esfuerzo medio
**Ablations de componentes**
- **Diagnóstico:** No se sabe qué componente aporta qué.
- **Hipótesis:** Cada componente (LLM selector, homofilia, confirmation bias,
  energy engine, multilayer, Factbook, EnKF) tiene una contribución medible
  y al menos uno es >5% del MAE.
- **Plan:**
  - 7 ablations: quitar uno por uno
  - Métrica: ΔMAE vs MASSIVE full
  - Test: leave-one-out + ranking de importancia
- **Criterio de éxito:** Hay ≥1 componente con ΔMAE > 5% al removerlo.
- **Esfuerzo:** 1 semana.

### Ticket 7 — P2, IMPACTO BAJO, esfuerzo bajo
**Métricas: CRPS, interval score, energy distance**
- **Diagnóstico:** Solo MAE/RMSE/mape. Para distribuciones de ensemble
  (con EnKF) se necesitan métricas probabilísticas.
- **Plan:** Añadir `properscoring` o implementación propia de CRPS.
- **Criterio de éxito:** MASSIVE+EnKF reporta CRPS ≤ ETS en ≥6/12 casos.
- **Esfuerzo:** 2 días.

### Ticket 8 — P3, IMPACTO BAJO, esfuerzo bajo
**Cards públicos: Model / Benchmark / Reproducibility**
- **Diagnóstico:** No hay cards estandarizados.
- **Plan:** Escribir `docs/cards/{MODEL,BENCHMARK,REPRODUCIBILITY}.md` siguiendo
  plantillas de Mitchell et al. 2019.
- **Esfuerzo:** 1 semana.

---

## 5. Primeros 5 experimentos (orden de ejecución)

### Experimento 1 — `EXP-001: MASSIVE_REAL_BENCHMARK_v0`
**Objetivo:** cuantificar el delta entre MASSIVE real y el proxy.
**Setup:**
- Dataset: 12 casos
- Predictor: `simulator.simular()` con parámetros derivados del case meta
- Baselines: 4 actuales
- Seeds: {42, 43, 44} (3 seeds para varianza)
- Salida: `experiments/06_real_benchmark_v0/{metrics.json, report.md}`
- Comando: `python3 -m benchmarks.runner --cases datasets/real_cases --real --seeds 42 43 44 --out reports/sota_v0`
**Criterio de éxito:** MASSIVE_real MAE < MASSIVE_proxy MAE en ≥9/12.
**Riesgo de fallo:** Medio — si la API de `simular()` no acepta los inputs del runner.

### Experimento 2 — `EXP-002: BASELINE_EXPANSION`
**Objetivo:** añadir ETS, ARIMA, threshold logistic, ML tabular.
**Setup:**
- Dataset: 12 casos
- Baselines nuevos: 4
- Salida: `experiments/07_baseline_expansion/baselines_comparison.csv`
- Comando: `python3 -m benchmarks.runner --cases datasets/real_cases --baselines all --out reports/baselines`
**Criterio de éxito:** 7 baselines ejecutan sin error.
**Riesgo de fallo:** Bajo — usar implementaciones estándar de statsmodels.

### Experimento 3 — `EXP-003: ENKF_DELTA_MEASUREMENT`
**Objetivo:** medir Δ pre/post asimilación.
**Setup:**
- Dataset: 12 casos
- Predictores: MASSIVE_real_sin_EnKF, MASSIVE_real_con_EnKF
- Parámetros EnKF: n_ensemble=32, σ_obs=0.05, interval=5
- Salida: `experiments/08_enkf_delta/{metrics.json, plot.png}`
- Comando: `python3 experiments/sota_roadmap/exp_003_enkf.py`
**Criterio de éxito:** ΔMAE > 0 en ≥8/12 casos, p<0.05.
**Riesgo de fallo:** Alto — EnKF puede no converger con el simulador caótico.

### Experimento 4 — `EXP-004: REGIME_CONDITIONED_BENCHMARK`
**Objetivo:** ¿mejora MASSIVE si se le da el cluster_id correcto?
**Setup:**
- Dataset: 12 casos con cluster_id propagado
- Predictor: MASSIVE con hiperparámetros adaptados al régimen
- Comparar: MASSIVE con/sin cluster_id
- Salida: `experiments/09_regime_conditioned/`
**Criterio de éxito:** MAE con cluster_id ≤ MAE sin cluster_id en ≥10/12.
**Riesgo de fallo:** Bajo — Ticket 2 ya hecho.

### Experimento 5 — `EXP-005: WALK_FORWARD_CV`
**Objetivo:** validar robustez out-of-sample con ventana móvil.
**Setup:**
- Dataset: 12 casos
- Esquema: train en [0, k], test en [k, k+3], avanzar k
- Repetir para k ∈ {0.5, 0.6, 0.7} del total
- Salida: `experiments/10_walk_forward/`
**Criterio de éxito:** La mejora MASSIVE>naive se mantiene en ≥2/3 splits.
**Riesgo de fallo:** Medio — series cortas (11-15 timesteps) dan splits
de test muy pequeños (3-5 puntos).

---

## 6. Niveles de éxito realistas

| Nivel | Criterio | Probabilidad estimada |
|---|---|---|
| **N1** | MASSIVE real supera a proxy en ≥9/12 casos (Experimento 1) | 80% — el motor tiene acceso a más info que el proxy. |
| **N2** | MASSIVE+EnKF mejora MASSIVE sin EnKF en ≥8/12 (Exp 3) | 50% — depende de convergencia EnKF. |
| **N3** | MASSIVE+EnKF gana o empata vs ETS en dirección (≥6/12) | 40% — ETS es fuerte en series suaves. |
| **N4** | Calibración CMA-ES mejora out-of-sample ≥10% (Exp 5) | 30% — riesgo de overfitting alto. |
| **N5** | Claim SOTA-defendible publicable | 20% — requiere N1+N2+N3. |

**Si no se llega a N3**, redefinir el nicho: "mejor ABM con asimilación
para captura temprana de régimen" en vez de "mejor predictor".

---

## 7. Honestidad científica: lo que NO se afirma

- ❌ "MASSIVE predice mejor que cualquier modelo" — el proxy pierde vs naive.
- ❌ "MASSIVE es SOTA en polarización social" — no se ha comparado vs SOTA real.
- ❌ "Las 39 fuentes académicas revisadas por pares" — son referencias
  documentadas, no una afirmación de que MASSIVE mismo haya pasado revisión.
- ❌ "EnKF funciona automáticamente con MASSIVE" — el código existe, la
  integración no se ha validado empíricamente.
- ❌ "Las simulaciones son ground truth" — son interpretaciones de mecanismos
  basadas en literatura.

## 8. Lo que SÍ se afirma (con evidencia)

- ✅ MASSIVE tiene 4 motores, 43 parámetros, 7 perfiles culturales, 12 casos
  reales — verificable en `experiments/`.
- ✅ El simulador es determinista con `seed=42` y `PYTHONHASHSEED=42` — verificado
  en tests 6.
- ✅ MASSIVE captura dirección de cambio (proxy: 9/12) — verificable.
- ✅ 3 casos tienen Diebold-Mariano significativo — verificable.

---

## 9. Estructura de carpetas propuesta

```
experiments/
├── 06_real_benchmark_v0/        # Exp 1: motor real vs proxy
├── 07_baseline_expansion/        # Exp 2: 7 baselines
├── 08_enkf_delta/                # Exp 3: Δ asimilación
├── 09_regime_conditioned/        # Exp 4: cluster_id propagation
├── 10_walk_forward/              # Exp 5: validación out-of-sample
├── 11_sensitivity/               # Sobol/Morris sobre 43 params
├── 12_cma_es_calibration/        # Calibración automática
├── 13_ablations/                 # Leave-one-out de componentes
└── sota_roadmap/
    ├── ROADMAP_SOTA_MASSIVE.md   # este documento
    ├── exp_001_real_benchmark.py
    ├── exp_002_baselines.py
    ├── exp_003_enkf.py
    ├── exp_004_regime.py
    └── exp_005_walk_forward.py

docs/
└── cards/
    ├── MODEL_CARD.md             # Mitchell et al. 2019 style
    ├── BENCHMARK_CARD.md
    └── REPRODUCIBILITY_CARD.md
```

---

## 10. Workflow operativo (regla estricta)

Para cada ticket:
```
A. Diagnóstico    →  qué problema exacto resuelve + evidencia
B. Hipótesis      →  mecanismo plausible + qué parte del sistema toca
C. Plan           →  archivos a modificar + cambios mínimos + riesgos
D. Experimento    →  dataset + seeds + métricas + criterio de éxito
E. Benchmark      →  ejecutar + guardar artifacts
F. Ablation       →  qué pasa si quitas el cambio
G. Decisión       →  CONSERVAR (commit) / REVERTIR (revert) / ITERAR (siguiente ronda)
```

**No avanzar a la siguiente etapa sin evidencia de la anterior.**

---

## 11. Comandos clave

```bash
# H1 — Benchmark del motor real
python3 -m benchmarks.runner --cases datasets/real_cases --real --seeds 42 43 44 \
    --out reports/sota_v0 --config configs/sota_v0.yaml

# H2 — EnKF delta
python3 experiments/sota_roadmap/exp_003_enkf.py \
    --cases datasets/real_cases --n_ensemble 32 --sigma_obs 0.05

# H3 — Ablations
python3 experiments/sota_roadmap/exp_006_ablations.py \
    --component {llm_selector,homofilia,confirmation_bias,energy_engine,multilayer,factbook,enkf}
```

---

## 12. Riesgos globales y mitigación

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| EnKF no converge con simulador caótico | Media | Usar inflación de covarianza + localization |
| CMA-ES sobreajusta a 12 casos | Alta | Walk-forward k-fold + 2 casos holdout |
| Motor real más lento que proxy | Baja | Cachear simulación por (seed, config) |
| Claims inflados que dañan credibilidad | Media (ya pasada) | Política de honestidad escrita, código la aplica |
| Dependencia de statsmodels / pmdarima | Baja | Fallback a (1,1,1) fijo si no hay auto_arima |

---

**Mantra del roadmap:**
> "Ningún número se reporta sin benchmark reproducible. Ningún claim se hace
> sin significancia estadística. Ningún feature se añade sin cerrar una
> brecha validada."

---

**Próximo paso inmediato:** ejecutar Experimento 1 (EXP-001) y reportar
resultados en 1 semana. Si N1 falla, replantear.
