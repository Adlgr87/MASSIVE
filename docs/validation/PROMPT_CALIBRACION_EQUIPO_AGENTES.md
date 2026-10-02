# PROMPT — Equipo de agentes: investigación, datos y calibración de MASSIVE

*Objetivo: que la simulación produzca resultados defendibles frente a la realidad,
no que parezca que los produce.*

---

## 0. CONTEXTO IMPRESCINDIBLE (leer antes de planificar nada)

MASSIVE ya es un sistema funcional: 837 tests en verde, API versionada `/v1`,
motores deterministas con semilla, y una capa científica opt-in. **Lo que falta
no es código: son datos y calibración.**

Un diagnóstico previo del repositorio dejó cuatro hechos que condicionan todo el
trabajo. No los reinvestiguéis: partid de ellos.

### Hecho 1 — El corpus real es minúsculo

`datasets/real_cases/` contiene **12 casos**, y cada uno tiene entre **11 y 15
puntos temporales**. En total, **~170 observaciones reales**.

| Caso | Puntos |
|---|---:|
| brazil_election_2022 | 12 |
| brexit_referendum_2016 | 11 |
| chile_estallido_2019 | 15 |
| colombia_paro_2021 | 15 |
| egypt_arab_spring_2011 | 14 |
| france_gilets_jaunes_2018 | 15 |
| germany_pegida_2014 | 15 |
| hong_kong_protests_2019 | 15 |
| iran_mahsa_amini_2022 | 14 |
| myanmar_coup_cdm_2021 | 15 |
| south_korea_candlelight_2016 | 14 |
| us_election_2020 | 14 |

### Hecho 2 — El corrector CfC falló, y se sabe exactamente por qué

El checkpoint de `models/cfc_calibrated/` tiene **10.177 parámetros** y se entrenó
sobre los **11 puntos reales** del caso Brexit, interpolados a 366 y divididos en
251/54/55. Eso es una ratio de **925 parámetros por observación real**. Interpolar
no crea información: crea pseudodatos autocorrelacionados que inflan el tamaño
muestral aparente.

Resultado medido fuera de muestra (reproducible con
`python scripts/validate_cfc_walkforward.py`):

| Estimador | RMSE | R² |
|---|---:|---:|
| Persistencia (último residuo observado) | **0,00457** | **+0,709** |
| Mejor constante posible | 0,00847 | 0,000 |
| Constante = media de entrenamiento | 0,03184 | −13,13 |
| **Modelo CfC** | 0,03763 | **−18,73** |
| Sin corrección | 0,07373 | −74,78 |

El modelo mejora sobre no corregir, pero **pierde contra repetir el último valor**.
Sus predicciones tienen std 0,00223 frente a una std real del residuo de 0,00847:
es una constante sesgada.

### Hecho 3 — La precisión que se publicaba era un artefacto aritmético

La versión anterior calculaba `corrected = 0,5·simulado + 0,5·observado`. Eso divide
el error a la mitad **por aritmética, con independencia del modelo**: por eso los
diez seeds del stress test reportaban una mejora de *exactamente* 50,000 %. La fuga
ya se eliminó y hay tests que la bloquean, pero **es el modo de fallo que debéis
vigilar en todo lo que hagáis**: si un resultado mejora de forma sospechosamente
redonda y estable, buscad la filtración antes de celebrarlo.

### Hecho 4 — La paridad de features ya se corrigió

`cfc_router.py` alimentaba al modelo con las features intercambiadas y la ventana de
lags invertida respecto a lo declarado en `models/cfc_calibrated/config.json`.
Corregido. Cualquier reentrenamiento parte ya de un pipeline coherente.

**Conclusión operativa:** el reentrenamiento del CfC **no es la primera tarea**. Con
170 observaciones no hay nada que reentrenar. La primera tarea es conseguir datos.

---

## 1. ROLES DEL EQUIPO

Organizaos en seis roles. Pueden solaparse, pero cada entregable tiene un
responsable único.

| Rol | Responsabilidad | Entregable principal |
|---|---|---|
| **A. Investigador de fuentes** | Localizar series temporales de opinión públicas, citables y relicenciables | `docs/validation/DATA_SOURCES.md` |
| **B. Ingeniero de datos** | Ingesta, normalización, control de calidad, versionado | `datasets/real_cases/` ampliado + esquema |
| **C. Calibrador de motores** | Estimar los parámetros físicos contra datos | `reports/engine_calibration.json` |
| **D. Entrenador de redes** | CfC y correctores, **solo cuando haya datos suficientes** | `models/` + `reports/cfc_validation.json` |
| **E. Validador independiente** | Protocolo, líneas base, pruebas de fuga. **No calibra nada** | `reports/validation_report.md` |
| **F. Documentalista** | Que lo publicado coincida con lo medido | README, `docs/` |

**Regla de independencia:** quien calibra no valida. El rol E debe poder tumbar el
trabajo de C y D, y su veredicto es vinculante. La razón es el Hecho 3: la precisión
inflada anterior sobrevivió porque nadie la auditó desde fuera.

---

## 2. FASE 1 — ADQUISICIÓN DE DATOS (bloqueante)

Nada de lo demás tiene sentido sin esto.

### 2.1 Qué buscar

Series temporales de opinión agregada, con **al menos 30 puntos por caso** (objetivo:
100+), de fuentes citables:

- **Encuestas electorales y de opinión**: Eurobarómetro, Latinobarómetro, Pew Research,
  Gallup, World Values Survey, ANES, CSES, CEP (Chile), INE/CIS (España), Ipsos,
  YouGov, Roper Center.
- **Agregadores de sondeos**: FiveThirtyEight (histórico), PollOfPolls, Wikipedia
  *opinion polling for X* (con las fuentes primarias, no el agregado).
- **Datos de protesta y movilización**: ACLED, GDELT, Mass Mobilization Project.
- **Opinión digital**: corpus académicos ya publicados y anonimizados; evitad el
  *scraping* de plataformas cuyos términos lo prohíban.
- **Indicadores estructurales**: World Bank (Gini, PIB), V-Dem, CIA World Factbook,
  OWID.

### 2.2 Criterios de aceptación de un caso

Un caso solo entra en `datasets/real_cases/` si cumple **todos**:

1. ≥ 30 observaciones temporales con fecha.
2. Fuente primaria citable y accesible (URL + fecha de consulta + licencia).
3. Licencia compatible con la del repositorio (Apache 2.0) o datos agregados de uso
   permitido. **Documentad la licencia; si es incompatible, no lo incluyáis: enlazad
   un script de descarga.**
4. Metodología de la medición documentada (tamaño muestral, margen de error, pregunta
   exacta formulada).
5. `meta.json` con la estructura actual + campos nuevos: `n_observations`,
   `source_license`, `sampling_error`, `question_wording`.

### 2.3 Trampa a evitar

**No interpoléis para "aumentar" el dataset.** Es lo que hundió el entrenamiento
anterior. Si una serie tiene 15 puntos, tiene 15 puntos. La interpolación es legítima
únicamente para alinear rejillas temporales *dentro* del modelo, y en ese caso el
recuento efectivo de observaciones sigue siendo el número de mediciones reales — así
debe reportarse en todos los cálculos de capacidad y significación.

### 2.4 Meta cuantitativa

Para que un modelo de ~10k parámetros sea defendible hacen falta, como orden de
magnitud, **miles de observaciones reales**. Objetivos escalonados:

- **Mínimo para recalibrar motores (Fase 3):** 500 observaciones, ≥ 10 casos.
- **Mínimo para reentrenar el CfC (Fase 4):** 2.000 observaciones, ≥ 25 casos,
  con diversidad cultural y de régimen político.
- **Si no se alcanza:** no se entrena. Se reduce la capacidad del modelo (ver §5.3).

---

## 3. FASE 2 — ESTRUCTURACIÓN Y CONTROL DE CALIDAD

1. **Esquema versionado.** Extended `meta.json` + `timeseries.csv` con columnas
   obligatorias `date,P` y opcionales `n_sample,margin_error,source_id`.
2. **Validador automático** (`scripts/validate_dataset.py`, a crear): comprueba
   esquema, monotonía de fechas, rango `P ∈ [0,1]`, huecos, duplicados y que el
   `n_observations` declarado coincida con las filas.
3. **Control de sesgos.** Documentad explícitamente: sesgo de selección (qué países
   tienen datos y cuáles no), sesgo de modo (teléfono vs online), efecto casa
   (*house effect*) entre encuestadoras, y cambios de formulación de pregunta.
4. **Partición pre-registrada.** Antes de mirar los datos de test, fijad la partición
   y registradla usando `docs/validation/preregistration_template_ES.md`. Esto ya
   existe en el repo: **usadlo, no lo reinventéis**.

---

## 4. FASE 3 — CALIBRACIÓN DE LOS MOTORES

Hay constantes fijadas por decreto que nadie ha estimado contra datos. Son el
objetivo principal, y probablemente den más mejora que cualquier red neuronal.

### 4.1 Parámetros candidatos (ubicaciones reales)

| Parámetro | Dónde | Valor actual | Qué gobierna |
|---|---|---|---|
| `_SIGMA` | `energy_engine.py:38` | 0,3 | Ancho del paisaje de energía |
| `_GINI_SIGMA_ANCHOR` | `energy_engine.py:92` | 0,35 | Gini de referencia |
| `_GINI_SIGMA_SENSITIVITY` | `energy_engine.py:95` | 0,5 | Pendiente Gini→σ |
| Doble pozo `0.49` | `multilayer_engine.py:283` | ±0,7 | Posición de los atractores de opinión |
| `coupling` | `multilayer_engine.py` | ~0,003 | Fuerza social entre capas |
| `temperature` | `energy_engine.py` | 0,05 | Ruido térmico / libre albedrío |
| `lambda_social` | `energy_engine.py` | 0,5 | Balance red ↔ paisaje |
| `eta` | `energy_runner.py` | 0,01 | Paso de integración |
| Mapeos Factbook | `massive/core/factbook/mappings.py` | varios | Gini→atractor, PIB→presupuesto, diversidad→presión |
| Inflación / localización EnKF | `massive_core/data_assimilation/kalman.py` | — | Estabilidad del filtro |

### 4.2 Antes de calibrar: análisis de identificabilidad

**Obligatorio y previo.** Con ~170–2.000 observaciones no todos los parámetros son
estimables. Haced:

1. **Análisis de sensibilidad global** (Sobol o Morris) sobre los parámetros de §4.1:
   ¿cuáles mueven realmente la salida?
2. **Matriz de correlación de parámetros**: detectad pares que se compensan entre sí
   (no identificables por separado).
3. **Decisión explícita**: calibrad solo los identificables; **fijad el resto con
   justificación documentada**. Un parámetro no identificable "calibrado" es ruido
   presentado como ciencia.

### 4.3 Método

- **Estimación bayesiana** preferida (ABC / SMC / emulador gaussiano), porque entrega
  **distribuciones posteriores** y no puntos. Con tan pocos datos, la incertidumbre
  *es* el resultado.
- Alternativa frecuentista aceptable: optimización + *bootstrap* para intervalos.
- **Prohibido** ajustar a ojo hasta que "se parezca". Si se hace manualmente, debe
  documentarse como tal y no llamarse calibración.

### 4.4 Preservar invariantes

La calibración **no puede** romper lo que ya está garantizado por tests:

- Determinismo con semilla fija (hay una huella de referencia; ver §7).
- `θ ≥ 0`, escalado `√dt` de la difusión, conservación de media/varianza en LOD.
- "Optional means optional": sin GPU, sin LLM, sin Factbook, todo sigue corriendo.
- Rangos de opinión: `bipolar [-1,1]`, `unipolar [0,1]`.

Si una calibración exige cambiar una ley física, eso es un cambio de modelo, no una
calibración: separadlo en su propia propuesta con su justificación.

---

## 5. FASE 4 — REDES NEURONALES

### 5.1 Puerta de entrada

**No entrenéis hasta que la Fase 1 alcance 2.000 observaciones reales y ≥ 25 casos.**
Si no se llega, documentadlo como resultado y pasad a §5.3.

### 5.2 Protocolo de entrenamiento

1. **Validación cruzada por casos** (*leave-one-case-out*), no por puntos. Partir una
   serie temporal por puntos filtra información del futuro al pasado.
2. **Walk-forward** dentro de cada caso: en el instante *t* solo se usan datos
   estrictamente anteriores a *t*.
3. **Líneas base obligatorias** en cada informe: persistencia, constante óptima, media
   de entrenamiento, y sin corrección. Están implementadas en `benchmarks/baselines.py`
   y `benchmarks/metrics.py`. **Un modelo que no las supere no se publica como
   corrector.**
4. **Significación estadística**: test de Diebold-Mariano (`benchmarks/metrics.py:67`)
   y corrección Holm-Bonferroni para comparaciones múltiples. Ya está implementado.
5. **Reportad R² además de RMSE.** Un RMSE bajo con R² negativo significa "constante
   razonable", no "modelo que entiende la dinámica" — exactamente el fallo actual.

### 5.3 Disciplina de capacidad

Elegid la capacidad según los datos, no al revés:

| Observaciones reales | Modelo defendible |
|---|---|
| < 500 | Ninguno. Usad persistencia; está documentada y funciona |
| 500 – 2.000 | Lineal regularizado / GP con pocos hiperparámetros (< 100 parámetros) |
| 2.000 – 10.000 | CfC pequeño (hidden 8–16, < 1.000 parámetros) |
| > 10.000 | CfC actual (hidden 64) justificable |

Reportad siempre la ratio **parámetros : observaciones reales** en el informe. Si
supera 1:10, justificadlo explícitamente o reducid el modelo.

### 5.4 Los tres modelos ausentes

`cfc_temperature.pt`, `cfc_lambda.pt` y `cfc_landscape.pt` se cargan opcionalmente
pero **no están publicados**: los motores caen siempre a las reglas heurísticas. O se
entrenan con el mismo protocolo, o se elimina su ruta de carga. No dejéis la
ambigüedad.

---

## 6. ÁREAS QUE NO ESTABAN EN EL ENCARGO Y SÍ IMPORTAN

Estas no se pidieron explícitamente, pero sin ellas la simulación no será
"completamente funcional" en ningún sentido defendible.

### 6.1 El léxico de sentimiento es el eslabón más débil

`social_connectors.py` puntúa texto con un diccionario de **37 palabras positivas y
36 negativas**, en inglés y español, **sin negación, sin ironía, sin intensificadores
y sin pesos**. "No es nada bueno" puntúa positivo. Todo el camino de sembrado desde
opinión real (`massive_core/opinion_sources.py`) descansa sobre esto.

**Tarea:** sustituidlo por un analizador validado (VADER, un modelo multilingüe
afinado, o un léxico con negación), y **medid su acuerdo con anotación humana** sobre
una muestra etiquetada. Reportad kappa de Cohen. Sin esa medición, no sabéis si estáis
sembrando opinión o ruido.

### 6.2 Cuantificación de incertidumbre de extremo a extremo

Una simulación que devuelve un número sin intervalo es inutilizable para decidir.
Propagad: incertidumbre de los datos → posterior de parámetros → ensemble de
simulaciones → **intervalos de credibilidad en la salida**. El envelope de respuesta
ya tiene sitio para ello (`summary`, `assumptions`).

### 6.3 Calibración de la propia incertidumbre

No basta con dar intervalos: hay que comprobar que son honestos. Medid **cobertura
empírica** (¿el intervalo al 90 % contiene el valor real el 90 % de las veces?),
*reliability diagrams* y CRPS. Un intervalo mal calibrado es peor que ninguno porque
transmite falsa confianza.

### 6.4 Ablación por mecanismo

Para cada mecanismo (fuerza social, paisaje, ruido, EnKF, corrector CfC, compresión
LOD): desactivadlo y medid cuánto se degrada la predicción. **Un mecanismo que no
mejora nada debe retirarse o documentarse como no verificado.** Esto es lo que
convierte el motor en ciencia en vez de folclore.

### 6.5 Validación fuera de distribución

Reservad casos enteros **nunca vistos** (p. ej. un régimen político o una región no
representada en entrenamiento). El rendimiento dentro de distribución no dice nada
sobre si el modelo generaliza a la siguiente crisis.

### 6.6 Zona muerta de la cuantización

`massive_engine.py` cuantiza a uint8. Queda sin medir a partir de qué `dt` la dinámica
se congela porque el incremento cae por debajo del paso de cuantización. Medidlo y
documentad el límite de validez: es una frontera dura de aplicabilidad del motor LOD.

### 6.7 Sesgo y ética de los datos de opinión

Documentad a quién representan y a quién no los datos (cobertura digital, sesgo
urbano, idioma, acceso). Una simulación calibrada sobre Twitter no modela una
población: modela a quienes tuitean. Debe decirse en la salida, no en una nota al pie.

### 6.8 Deriva y recalibración

Los parámetros sociales no son constantes universales. Definid cada cuánto se
revalida, con qué criterio se declara obsoleta una calibración, y dejadlo
automatizado en CI.

### 6.9 Reproducibilidad de la calibración

Todo el pipeline debe poder re-ejecutarse de cero con un comando y dar el mismo
resultado: semillas fijas, versiones de datos ancladas (hash), entorno declarado.
Si la calibración no es reproducible, no es verificable.

---

## 7. REGLAS INQUEBRANTABLES

1. **El determinismo es sagrado.** Hay una huella numérica de referencia:
   ```
   PYTHONHASHSEED=0, energy_runner.run_energy_simulation(
       "polarizacion social", n_agents=60, steps=25, seed=1234)
   → sha256 4dd504333bbfa2c983fc4bc3adcbeee4978b43c3cb3d5ba607a3017ad99ac388
   ```
   Cambiará legítimamente al recalibrar los motores (son otros parámetros). Lo que
   **no** puede pasar es que cambie por un refactor, ni que deje de ser reproducible.
   Fijad una huella nueva con cada calibración aceptada.

2. **Cero fugas.** El valor que se predice no puede entrar, ni directa ni
   indirectamente, en su propia predicción. Ante una mejora sospechosamente limpia,
   asumid fuga hasta demostrar lo contrario.

3. **Las líneas base son obligatorias.** Ningún resultado se publica sin la tabla
   comparativa frente a persistencia y constantes.

4. **Los resultados negativos son entregables de pleno derecho.** "El modelo no supera
   la persistencia" es un hallazgo valioso y debe publicarse con la misma visibilidad
   que un éxito. El repositorio ya tiene precedente:
   `reports/cfc_validation.json` y `scripts/validate_cfc_walkforward.py`.

5. **No toquéis la documentación para que cuadre con el modelo.** Al revés: si el
   README afirma algo que la medición no sostiene, se corrige el README.

6. **La suite debe seguir verde.** 837 tests, `ruff`, `black`, cobertura ≥ 60 %.
   Añadid tests de regresión para cada calibración aceptada.

7. **Toda cifra publicada necesita el comando que la reproduce.** Sin excepción.

---

## 8. ENTREGABLES

| # | Entregable | Ruta |
|---|---|---|
| 1 | Inventario de fuentes con licencias | `docs/validation/DATA_SOURCES.md` |
| 2 | Dataset ampliado + validador | `datasets/real_cases/`, `scripts/validate_dataset.py` |
| 3 | Pre-registro de la partición | `docs/validation/preregistration_*.md` |
| 4 | Análisis de identificabilidad | `reports/identifiability.json` |
| 5 | Calibración de motores + posteriores | `reports/engine_calibration.json` |
| 6 | Informe de entrenamiento con líneas base | `reports/cfc_validation.json` |
| 7 | Estudio de ablación | `reports/ablation.md` |
| 8 | Calibración de incertidumbre | `reports/uncertainty_calibration.md` |
| 9 | Veredicto independiente (rol E) | `reports/validation_report.md` |
| 10 | Documentación sincronizada | README (EN/ES), `docs/` |

---

## 9. CRITERIO DE ÉXITO

La simulación se considera **calibrada y funcional** cuando:

1. Supera a la persistencia y a la mejor constante en **validación cruzada por casos**,
   con significación estadística (DM test, Holm-Bonferroni).
2. Sus intervalos de incertidumbre tienen **cobertura empírica correcta** (±5 % del
   nominal).
3. Mantiene el rendimiento en **al menos un caso fuera de distribución**.
4. Cada mecanismo activo **justifica su presencia** en la ablación.
5. Todo el pipeline es **reproducible desde cero** con un comando.
6. La documentación publicada **coincide exactamente** con lo medido.

Si no se alcanza alguno, el entregable es el informe honesto de por qué — no una
versión maquillada de las cifras.

> Lo que hace creíble a un simulador social no es acertar: es saber, y poder demostrar,
> cuánto se equivoca y dónde deja de ser válido.
