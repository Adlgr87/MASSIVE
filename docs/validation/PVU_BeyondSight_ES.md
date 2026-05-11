# BeyondSight — Protocolo de Uso Validado (PVU-BS) — Español

> **Version:** 1.0 · **Estado:** Activo  
> **Versión en inglés:** [PVU_BeyondSight_EN.md](PVU_BeyondSight_EN.md)

---

## 1. Propósito

El **Protocolo de Uso Validado (PVU-BS)** establece el estándar mínimo de evidencia requerido para afirmar que BeyondSight ofrece desempeño predictivo *validado* sobre datos reales de dinámica de opinión.  
Distingue claramente entre:

- **Casos de muestra** (`datasets/pvu_cases/sample_case_*`): datos sintéticos usados únicamente para verificar que el pipeline funciona correctamente. **No se pueden derivar afirmaciones científicas de ellos.**
- **Validación real**: N ≥ 10 casos independientes con conjuntos de prueba bloqueados, ejecutados bajo este protocolo.

---

## 2. Definiciones Operativas

### 2.1 Caso Independiente

Un **caso** es la tupla `{red, serie_temporal, intervenciones, metadatos}` descrita en una carpeta de caso PVU.

Dos casos se consideran **independientes** si se cumplen **ambas** condiciones:

1. **No solapamiento de red:** los conjuntos de nodos (usuarios/comunidades) comparten menos del 10 % de sus miembros, O las estructuras de grafo provienen de poblaciones genuinamente distintas.
2. **No solapamiento temporal:** sus ventanas temporales no coinciden con el mismo shock global no modelado (p.ej., una pandemia mundial).  
   Si comparten un shock, deben compartir un `cluster_id` común en `meta.json` y la evaluación debe hacerse a **nivel de cluster** (un test DM por cluster, no por caso), corrigiendo el tamaño de muestra efectivo reducido.

### 2.2 Uso de `cluster_id`

`cluster_id` agrupa casos afectados por el mismo confundidor estructural o temporal.  
Reglas:

- Definir `cluster_id` en `meta.json` cuando los casos comparten plataforma, evento regional o ventana temporal superpuesta.
- Los tests estadísticos y tamaños de efecto se calculan **por cluster** cuando N_cluster > 1; los resultados individuales se reportan como suplementarios.
- Las métricas a nivel de cluster son la media ponderada de métricas por caso (peso = N_test de cada caso).

### 2.3 Variable Objetivo

BeyondSight se valida sobre un **objetivo compuesto** que captura tanto el nivel como la dinámica de la polarización de opinión:

| Componente | Definición | Métrica |
|-----------|-----------|---------|
| **Índice de Polarización P(t)** | Varianza de la distribución de opinión + fracción de agentes en extremos (|opinion| > 0.7 en [−1, 1]) | MAE, RMSE, MAPE, Exactitud Direccional |
| **Habilidad en Puntos de Giro (TPS)** | Capacidad de predecir *cuándo* ocurre una transición de régimen (extremo local en P) | Precisión, Recall, F1, Error Medio de Timing |

### 2.4 División Train / Validación / Test

| División | Fracción | Propósito |
|----------|----------|-----------|
| Train | 70 % | Calibración del modelo, selección de parámetros |
| Validación | — | (opcional) ajuste de hiperparámetros |
| Test | 30 % | **Bloqueado; no debe tocarse antes de la evaluación final** |

---

## 3. Reglas Anti-Leakage (Anti-Filtración)

Las siguientes acciones constituyen **filtración del test** e invalidan la corrida de validación:

1. Mirar métricas del test (incluso agregadas) antes de congelar la configuración del modelo.
2. Ajustar prompts, temperatura, proveedor de modelo, reglas de régimen o cualquier parámetro **después de ver resultados del test**, incluso informalmente.
3. Seleccionar o descartar casos *post-hoc* para mejorar los resultados reportados.
4. Correr el modelo múltiples veces sobre el mismo conjunto de test y reportar la mejor corrida (salvo que se haga explícitamente un chequeo de consistencia LLM bajo § 6).
5. Usar observaciones del test como contexto de entrenamiento en el prompt del LLM.

**Registro:** Un documento de pre-registro (ver `preregistration_template_ES.md`) debe commitearse al repositorio **antes** de romper el sello del test.

---

## 4. Criterio Estadístico

### 4.1 Hipótesis Principal

> BeyondSight produce un MAE significativamente menor en el conjunto de test bloqueado comparado con el baseline naive (persistencia del último valor), tras corrección Holm–Bonferroni.

### 4.2 Procedimiento de Test

1. Calcular predicciones de **todos** los baselines y BeyondSight sobre el split de test de **cada** caso.
2. Para cada caso, ejecutar un **test de Diebold–Mariano (DM)** bilateral de BeyondSight vs cada baseline usando pérdida cuadrática.
3. Recopilar los M p-valores crudos por caso (uno por baseline).
4. Aplicar **corrección Holm–Bonferroni** sobre las M × N comparaciones (M baselines × N casos). Usar `benchmarks/metrics.py::holm_bonferroni`.
5. Reportar tanto p-valores crudos como ajustados.

### 4.3 Tamaños de Efecto (obligatorios junto con p-valores)

| Métrica | Interpretación |
|---------|---------------|
| ΔMAE = MAE_baseline − MAE_BS | Mejora absoluta en MAE |
| ΔRMSE | Mejora absoluta en RMSE |
| Lift de exactitud direccional | Dir. acc. BS − dir. acc. naive |
| TPS F1 | Balance Precisión–Recall en puntos de giro |

### 4.4 Criterios de Aceptación (por nivel PVU)

| Nivel | Min casos | DM vs naive | Tamaño de efecto | TPS F1 |
|-------|-----------|-------------|------------------|--------|
| Bronce | 10 | p_adj < 0.05 | ΔMAE > 0 | — |
| Plata | 20 | p_adj < 0.05 vs **todos** los baselines | ΔMAE > 5 % | ≥ 0.50 |
| Oro | 30 | p_adj < 0.05 vs todos + replicación externa | ΔMAE > 10 % | ≥ 0.70 |

---

## 5. Baselines (obligatorios)

Todos los siguientes deben incluirse en cada corrida de validación:

| ID | Nombre | Descripción |
|----|--------|-------------|
| B1 | Naive | Último valor observado persistido para todos los pasos de forecast |
| B2 | Media Móvil | Media de las últimas 4 observaciones |
| B3 | AR(1) | Autorregresión de primer orden ajustada por MCO |
| B4 | Régimen Aleatorio | Paseo aleatorio con ruido calibrado desde el entrenamiento |

Implementados en `benchmarks/baselines.py`.

---

## 6. Chequeo de Consistencia LLM

Cuando BeyondSight se corre en modo LLM:

1. Correr el mismo forecast **5 veces** con distintas semillas aleatorias.
2. Calcular el coeficiente de variación (CV = std / media) del MAE reportado entre corridas.
3. Si CV > 0.15 (15 %), marcar el resultado y reportarlo; no suprimirlo.

---

## 7. Requisitos de Reproducibilidad

Cada corrida de validación debe producir y archivar:

- `configs/pvu.yaml` (copia congelada con todos los parámetros).
- `reports/validation/<run_id>/metrics.json` (métricas por caso).
- `reports/validation/<run_id>/report.md` (resumen legible).
- SHA del commit del código.
- Versiones de paquetes Python (`pip freeze`).
- Proveedor LLM + nombre del modelo + temperatura (si modo LLM).
- `PYTHONHASHSEED` y valor `--seed`.

El runner (`benchmarks/runner.py`) escribe `metrics.json` y `report.md` automáticamente.

---

## 8. Cómo Correr

```bash
# Modo offline (sin clave de API — por defecto en CI):
PYTHONHASHSEED=42 python -m benchmarks.runner \
    --cases datasets/pvu_cases \
    --offline \
    --out reports/validation/ci \
    --seed 42

# Modo LLM (requiere OPENROUTER_API_KEY o OPENAI_API_KEY):
PYTHONHASHSEED=42 python -m benchmarks.runner \
    --cases datasets/pvu_cases \
    --llm \
    --out reports/validation/llm_run \
    --seed 42
```

---

## 9. Formato de Archivos de Caso

Cada caso vive en su propia subcarpeta bajo `datasets/pvu_cases/`:

```
sample_case_001/
├── timeseries.csv        # requerido: columnas date, P (+ opcionales)
├── interventions.json    # lista de {date, label, source}
└── meta.json             # metadatos del caso
```

### Columnas de `timeseries.csv`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `date` | string (ISO 8601) | Fecha de observación |
| `P` | float [0, 1] | Índice de polarización |
| `volume` | float (opcional) | Proxy de volumen de actividad |

### Campos requeridos de `meta.json`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `case_id` | string | Identificador único |
| `domain` | string | p.ej. `political_opinion` |
| `source` | string | Origen de datos (o `synthetic`) |
| `cluster_id` | string \| null | Cluster para tests agrupados |
| `license` | string | Licencia de los datos |
| `note` | string | Notas en texto libre |

---

## 10. Glosario

| Término | Definición |
|---------|-----------|
| PVU-BS | Protocolo de Uso Validado — BeyondSight |
| Test DM | Test de Diebold–Mariano de igual exactitud predictiva |
| Holm–Bonferroni | Corrección escalonada para comparaciones múltiples |
| TPS | Habilidad en Puntos de Giro (F1 sobre extremos locales detectados) |
| EWS | Señal de Alerta Temprana (Desaceleración Crítica) |
| Filtración de test | Cualquier flujo de información del split de test al diseño del modelo |
| Caso de muestra | Caso sintético solo para pruebas del pipeline |

---

*Ver también: [Plantilla de pre-registro](preregistration_template_ES.md) · [Plantilla de reporte de validación](validation_report_template_ES.md)*
