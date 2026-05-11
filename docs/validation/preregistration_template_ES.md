# Plantilla de Pre-Registro PVU-BS (Español)

> Completar este documento y commitear al repositorio **antes** de romper el sello del test.  
> Versión en inglés: [preregistration_template_EN.md](preregistration_template_EN.md)

---

## 1. Identificación

| Campo | Valor |
|-------|-------|
| ID de corrida | `<!-- ej. pvu_run_001 -->` |
| Fecha de pre-registro | `<!-- YYYY-MM-DD -->` |
| Registrado por | `<!-- usuario GitHub -->` |
| Commit Git (código) | `<!-- SHA en el momento del registro -->` |

---

## 2. Hipótesis

> Copiar de PVU-BS § 4.1 o declarar una variante más específica:

_MASSIVE produce un MAE significativamente menor en el conjunto de test bloqueado comparado con el baseline naive, tras corrección Holm–Bonferroni (α = 0.05)._

Métrica primaria: `<!-- MAE / RMSE / TPS F1 / … -->`

---

## 3. Datos

| Campo | Valor |
|-------|-------|
| Carpeta de casos | `datasets/pvu_cases/` |
| N casos | `<!-- total -->` |
| IDs de cluster | `<!-- lista o "ninguno" -->` |
| Rango de fechas | `<!-- inicio – fin -->` |
| Fuente | `<!-- synthetic / Reddit / … -->` |
| Licencia | `<!-- CC0 / CC-BY / … -->` |

**Verificación de independencia:**  
_Explicar cómo los casos satisfacen el criterio de independencia (§ 2.1)._

---

## 4. Configuración del Modelo (congelada)

| Parámetro | Valor |
|-----------|-------|
| SHA de `configs/pvu.yaml` | `<!-- hash git del archivo de configuración -->` |
| Semilla | `<!-- entero -->` |
| PYTHONHASHSEED | `<!-- entero -->` |
| Modo | `<!-- offline / llm -->` |
| Proveedor LLM + modelo | `<!-- si modo llm; si no "n/a" -->` |
| Temperatura | `<!-- si modo llm; si no "n/a" -->` |
| Versión de Python | `<!-- ej. 3.11.x -->` |
| Versiones de paquetes clave | `<!-- numpy X.Y, scipy X.Y, … -->` |

---

## 5. Plan de Análisis

- Proporción train/test: `<!-- ej. 70/30 -->` (definida en `configs/pvu.yaml`)
- Test estadístico: Diebold–Mariano, bilateral, pérdida cuadrática
- Corrección por comparaciones múltiples: Holm–Bonferroni sobre todas las comparaciones baseline × caso
- Tamaños de efecto a reportar: ΔMAE, ΔRMSE, lift de exactitud direccional, TPS F1
- Detección de puntos de giro: `order=__`, `min_prominence=__`, `tolerance=__`

**Criterios de exclusión** (pre-especificados; ningún caso puede excluirse después de ver métricas del test):

- _ej. los casos con menos de 10 observaciones en el test son omitidos automáticamente por el runner_

---

## 6. Declaración Anti-Filtración

Confirmo que al momento del pre-registro:

- [ ] No he visto métricas ni gráficos del split de test.
- [ ] Los parámetros del modelo y los prompts están congelados (ver SHA arriba).
- [ ] Ningún caso fue seleccionado ni excluido basándose en el desempeño esperado.
- [ ] El runner se ejecutará una vez; los resultados se reportarán tal cual.

---

## 7. Registro de Desviaciones

_Completar tras la corrida si algo difirió del pre-registro:_

| Desviación | Razón | Impacto |
|-----------|-------|---------|
| (ninguna) | — | — |

---

_Esta plantilla sigue PVU-BS v1.0 — ver [PVU_BeyondSight_ES.md](PVU_BeyondSight_ES.md)_
