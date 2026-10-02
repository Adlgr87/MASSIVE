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

### Hecho 1-bis — La variable objetivo no está definida, y no es la misma en todos los casos

Esto es **más bloqueante que la escasez de datos** y se descubrió al construir el
validador. Los doce `timeseries.csv` tienen la columna `P`, pero **ningún `meta.json`
dice qué mide**, y demostrablemente mide cosas distintas:

| Caso | `scenario_type` | Serie `P` | Qué parece medir |
|---|---|---|---|
| brexit_referendum_2016 | polarization_spike | 0,28 → 0,62 → 0,52 | Cuota de voto *Leave* |
| egypt_arab_spring_2011 | contagion_sir | 0,02 → 0,70 → 0,08 | Fracción participante (curva SIR) |
| south_korea_candlelight_2016 | consensus_cascade | 0,35 → 0,50 → 0,23 | Cascada de consenso |

Una cuota de voto y una fracción de movilización **no son el mismo observable**.
Agruparlas porque comparten nombre de columna no es *pooling*: es un error de tipo.

Además, `data_type` es `empirical_estimated` en los doce: las series fueron
**reconstruidas a mano desde fuentes publicadas**, no medidas directamente. Es
legítimo, pero debe declararse y ponderarse distinto que un dato medido.

**Nada se calibra hasta que cada caso declare `target_variable`, `target_units` y
`observation_operator`.** `python scripts/validate_dataset.py` ya lo exige y
actualmente falla los doce casos.

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

## 1-BIS. SPRINT 0 — TRES ENTREGABLES OBLIGATORIOS ANTES DE TODO LO DEMÁS

Nada de las fases siguientes empieza hasta cerrar estos tres. Son baratos, son
rápidos y determinan si el resto del trabajo tiene sentido.

### G0 — Etiqueta de la variable objetivo: el léxico de sentimiento

**Esta es la prioridad número uno, por encima de conseguir más datos.** Si la
variable objetivo está mal etiquetada, ninguna calibración la arregla: *garbage in,
garbage out*.

`social_connectors.py` puntúa texto con **37 palabras positivas y 36 negativas**, en
inglés y español, **sin negación, sin intensificadores, sin ironía y sin pesos**.
«No es nada bueno» puntúa **positivo**. Todo el camino de sembrado desde opinión real
(`massive_core/opinion_sources.py`) descansa sobre esto.

Entregables:

1. **Gold set humano de 200–300 mensajes**, muestreados del dominio real (protesta,
   elección, polarización), en español e inglés, anotados por ≥ 2 personas.
2. **Acuerdo entre anotadores** (kappa de Cohen o Krippendorff). Si κ < 0,6, el
   problema es la guía de anotación, no el modelo: corregidla antes de seguir.
3. **Medición del léxico actual contra el gold set**: accuracy, F1 macro, y matriz de
   confusión. Documentad explícitamente el comportamiento ante negación.
4. **Decisión fundamentada**: sustituir por un transformer de dominio (XLM-T,
   RoBERTa en español afinado, o similar) o, como mínimo, un léxico con manejo de
   negación e intensificadores. Reportad la mejora medida sobre el mismo gold set.

**Criterio de salida de G0:** el analizador elegido supera al léxico actual sobre el
gold set con significación, y su F1 se publica. Sin esto, el sembrado desde opinión
real no es utilizable para calibrar.

### G0-bis — Definición de la variable objetivo y del operador de observación

Para **cada** caso de `datasets/real_cases/`, rellenad en `meta.json`:

- `target_variable`: qué mide `P`, en palabras inequívocas
  (p. ej. `leave_vote_share`, `fraction_participating`, `polarization_index`).
- `target_units`: `share` | `fraction_participating` | `index` | …
- `observation_operator`: **cómo se obtiene la medición a partir del estado del
  simulador**. Ejemplos: `mean(opinion > 0)` para una cuota de voto;
  `fraction(|opinion| > umbral)` para participación; `std(opinion)/half_range` para
  un índice de polarización.

Sin el operador **H**, ninguna distancia entre simulación y realidad (RMSE,
Wasserstein, KL) está bien definida — se estaría comparando magnitudes distintas.

**Criterio de salida:** `python scripts/validate_dataset.py` termina con código 0.
Hoy falla los doce casos por esta razón exacta.

### G0-ter — Plan de sourcing con fuentes y costos reales

Una meta de «2.000 observaciones» sin decir de dónde salen es una lista de deseos.
Entregad una tabla con fuente, volumen estimado, licencia, **coste real** y esfuerzo:

| Fuente | Tipo | Volumen estimado | Licencia | Coste | Notas |
|---|---|---|---|---|---|
| Latinobarómetro | Encuesta anual, 18 países | alto | Registro gratuito | 0 € | Serie larga, ideal para pooling |
| CEP (Chile) | Encuesta, serie histórica | medio | Pública | 0 € | Cubre el caso Chile 2019 |
| ANES / CSES | Panel electoral | alto | Académica | 0 € | Requiere acuerdo de uso |
| Eurobarómetro | Encuesta UE | alto | Pública | 0 € | Serie muy larga |
| Archivos Pushshift / Reddit | Texto con timestamp | muy alto | Variable | 0 € | Verificad estado actual del archivo |
| Kaggle (datasets de opinión) | Mixto | medio | Por dataset | 0 € | Revisar licencia caso por caso |
| Comentarios de medios con timestamp | Texto | medio | Por medio | Variable | Suele requerir permiso |
| **API de X/Twitter** | Texto | alto | Comercial | **Caro y restringido** | **No asumir disponibilidad** |

**Criterio de salida:** un plan que llegue al Nivel 2 (500 obs) con fuentes concretas,
licencias verificadas y coste cerrado. No basta con enumerar posibilidades.

### G0-quater — Líneas base sobre los 12 casos

Antes de calibrar nada, medid qué hace falta batir. Sobre los doce casos actuales:

- **Persistencia** (último valor observado).
- **Lineal** (tendencia ajustada por mínimos cuadrados).
- **Mean-reverting** (Ornstein-Uhlenbeck / AR(1)).

Usad `benchmarks/baselines.py` y `benchmarks/metrics.py`, que ya existen. Publicad la
tabla en `reports/baselines_12cases.json`. **Ese es el listón.** Cualquier motor o red
que no lo supere no se publica como mejora.

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

### 2.4 Escalera de capacidad (no es un muro: cada peldaño habilita trabajo real)

El estado actual es **169 observaciones** → Nivel 1. Cada peldaño habilita técnicas,
no solo permisos. `scripts/validate_dataset.py` calcula el nivel automáticamente.

| Nivel | Observaciones válidas | Qué se puede hacer | Qué queda prohibido |
|---|---|---|---|
| **1** | < 500 | Líneas base; parámetros **agregados** (σ, ε promedio) con **priors fuertes**; pooling jerárquico | Redes neuronales; parámetros por segmento o por arista (`W` completa, ε por perfil) |
| **2** | 500 – 2.000 | Calibración paramétrica por **SBI/ABC con pooling jerárquico**; posteriores con incertidumbre | Correctores neuronales residuales |
| **3** | > 2.000, ≥ 25 casos | Corrector neuronal con capacidad ajustada al número de observaciones | Nada por volumen; la identificabilidad sigue mandando |

**Qué cuenta como observación válida** (el validador lo exige):

1. Tiene **timestamp** parseable y ordenado.
2. Pertenece a una **serie**, no es un escalar suelto sin contexto temporal.
3. Su caso declara `target_variable`, `target_units` y `observation_operator`.
4. Está en `[0,1]` y su `data_type` está declarado.

Una serie **escalar** (`date,P` sin dispersión) cuenta para el volumen pero **no
habilita calibrar parámetros distribucionales**. Para eso hacen falta columnas de
dispersión (`P_std`, `n_sample`, o intervalos).

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
5. **Umbral de éxito pre-registrado, con número exacto.** Antes de ejecutar nada,
   escribid la métrica primaria, el valor que cuenta como éxito y el test estadístico
   — por ejemplo: *«RMSE out-of-sample menor que la persistencia, con DM test
   p < 0,05 tras Holm-Bonferroni»*. Decidirlo después de ver los resultados es
   p-hacking aunque no se le llame así, y es exactamente cómo sobrevivió la cifra
   inflada del 50 %.

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

### 4.2-bis La granularidad de los datos acota la del modelo

Con un observable **escalar** por instante (que es lo que hay: `date,P`), la regla es
dura y no negociable:

| Lo que se observa | Lo que se puede identificar | Lo que NO |
|---|---|---|
| Escalar por instante (`P`) | Dinámica **agregada**: σ global, ε promedio, tasa de reversión, profundidad media del atractor | `W` completa, ε por perfil, profundidad por segmento, cualquier parámetro distribucional |
| Escalar + dispersión (`P_std`, `n_sample`) | Lo anterior + varianza del estado | Estructura de red individual |
| Distribución completa por instante | Parámetros distribucionales | Identidades de agente |

Consecuencia directa para el motor: **el Langevin 5D no es observable con datos
escasos y escalares**. Las cinco dimensiones (opinión, cooperación, jerarquía,
ingreso, acceso a información) no se pueden separar a partir de un único número por
fecha. Dos salidas legítimas, elegid una y documentadla:

1. **Reducir la dimensión de estado** para la calibración: calibrad un modelo de
   opinión 1D y tratad las otras cuatro capas como fijas o derivadas.
2. **Definir un operador de observación H explícito** que proyecte el estado 5D al
   escalar medido, y calibrad solo lo que H deja identificable. Este es el mismo H que
   necesita el EnKF (`massive_core/data_assimilation/kalman.py`): definidlo **una vez**
   y reutilizadlo en ambos sitios.

### 4.2-ter Pooling jerárquico bayesiano entre casos

Con 12 casos cortos, tratarlos por separado desperdicia información y tratarlos como
uno solo borra sus diferencias. La forma eficiente es **partial pooling**:

```
  theta_caso_i ~ Normal(mu_global, tau)      # cada caso tiene su parámetro…
  mu_global, tau ~ priors                     # …extraído de una población común
```

Así cada caso toma fuerza estadística prestada de los demás, y `tau` cuantifica
cuánto varían realmente entre contextos — que es en sí un resultado publicable.

**Advertencia derivada del Hecho 1-bis:** solo se agrupan casos que compartan
`target_variable`. Una cuota de voto y una fracción de movilización no pertenecen a
la misma población de parámetros. Si tras G0-bis resultan ser tres observables
distintos, haced **tres jerarquías**, no una.

### 4.3 Método

- **Estimación bayesiana** preferida, porque entrega **distribuciones posteriores** y
  no puntos. Con tan pocos datos, la incertidumbre *es* el resultado.
- **Coste computacional, que decide el método.** ABC por rechazo puro es prohibitivo:
  necesita cientos de miles de simulaciones. Usad **estimación neuronal de posterior
  (NPE/SNPE)**, que amortiza el coste entrenando un estimador sobre un presupuesto
  acotado de simulaciones.
- **Simulad sobre `massive_engine.py` (super-agentes LOD), no sobre el motor a
  resolución completa.** El bucle de inferencia ejecuta miles de simulaciones; a plena
  resolución es inviable. Antes de usarlo, **verificad que el LOD preserva los
  estadísticos que alimentan la verosimilitud** (media y varianza se conservan; hay
  tests que lo cubren) y documentad el error de aproximación que introduce.
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

**No se reentrena el CfC.** Es una decisión tomada, no una recomendación: con 169
observaciones el reentrenamiento repetiría el fallo del Hecho 2.

El Nivel 3 de la escalera (§2.4) —más de 2.000 observaciones válidas y ≥ 25 casos— es
condición **necesaria pero no suficiente** para reabrir la cuestión. También hace falta
haber cerrado G0 (etiquetas fiables) y G0-bis (operador H), y que el validador con veto
lo autorice. Si no se llega, eso no es un fracaso: es el resultado, y se documenta.

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

| Observaciones reales | Modelo defendible | Nivel (§2.4) |
|---|---|---|
| < 500 | Ninguno. Persistencia + parámetros agregados con priors fuertes | 1 |
| 500 – 2.000 | SBI/ABC paramétrico con pooling jerárquico (< 100 parámetros) | 2 |
| 2.000 – 10.000 | CfC pequeño (hidden 8–16, < 1.000 parámetros) | 3 |
| > 10.000 | CfC actual (hidden 64, 10.177 parámetros) justificable | 3 |

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

### 6.1 El léxico de sentimiento → promovido a G0

Era el punto más subestimado de la versión anterior de este documento. Está ahora en
**§1-BIS / G0** como entregable bloqueante del Sprint 0, por delante de conseguir más
datos: una variable objetivo mal etiquetada no se arregla con ninguna calibración
posterior.

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

### 6.8 Dominio de validez declarado

Los doce casos están sesgados a **protestas y elecciones polarizadas**, en su mayoría
episodios de crisis de 2011–2022. Un simulador calibrado sobre eso **no es un
simulador social general**.

Declarad explícitamente, en la salida de la API y en el README, para qué familia de
eventos es válido y para cuál no se ha verificado. No afirméis fidelidad universal:
es la forma más rápida de perder la credibilidad que el resto del trabajo construye.

### 6.9 Datos sintéticos: solo como puente

Se permiten **únicamente** para stress-testing, pruebas de recuperación de parámetros
(¿recupera el calibrador un valor conocido?) y pruebas de carga. **Nunca para
calibrar**, y siempre etiquetados `data_type: synthetic` — el validador ya los marca y
los excluye del recuento de calibración.

Un uso legítimo y valioso: **prueba de recuperación**. Generad datos con parámetros
conocidos, pasadlos por el pipeline completo y comprobad que la posterior los
recupera. Si no los recupera con datos sintéticos limpios, no los recuperará jamás con
datos reales — y eso se sabe antes de gastar el presupuesto de datos.

### 6.10 Deriva y recalibración

Los parámetros sociales no son constantes universales. Definid cada cuánto se
revalida, con qué criterio se declara obsoleta una calibración, y dejadlo
automatizado en CI.

### 6.11 Reproducibilidad de la calibración

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
| 0a | **G0** Gold set + medición del léxico + decisión | `reports/sentiment_goldset.md` |
| 0b | **G0-bis** `target_variable` + `observation_operator` en los 12 casos | `datasets/real_cases/*/meta.json` |
| 0c | **G0-ter** Plan de sourcing con costos | `docs/validation/DATA_SOURCES.md` |
| 0d | **G0-quater** Líneas base sobre los 12 casos | `reports/baselines_12cases.json` |
| 1 | Validador del corpus | `scripts/validate_dataset.py` **(ya entregado)** |
| 2 | Dataset ampliado | `datasets/real_cases/` |
| 3 | Pre-registro de la partición | `docs/validation/preregistration_*.md` |
| 4 | Análisis de identificabilidad + jerarquía de pooling | `reports/identifiability.json` |
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
7. `python scripts/validate_dataset.py` termina en 0: cada caso declara su variable
   objetivo y su operador de observación.
8. El **dominio de validez** está declarado y no se afirma fidelidad fuera de él.
9. El umbral de éxito estaba **pre-registrado antes** de ver los resultados.

Si no se alcanza alguno, el entregable es el informe honesto de por qué — no una
versión maquillada de las cifras.

> Lo que hace creíble a un simulador social no es acertar: es saber, y poder demostrar,
> cuánto se equivoca y dónde deja de ser válido.
