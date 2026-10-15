# Plan de prueba: ¿qué mide mejor la postura en MASSIVE?

Pregunta de decisión: ¿alguno de Von, Jev o un LLM generalista mide la postura de un texto mejor que el léxico actual (`_score_text` en `social_connectors.py`), y en qué eje (precisión, calibración, estabilidad, velocidad, costo) justifica una dependencia nueva?

Glosario: LLM (Large Language Model, modelo de lenguaje grande), ECE (Expected Calibration Error, error de calibración esperado: qué tan lejos está la confianza declarada de la tasa real de aciertos), Brier (error cuadrático de las probabilidades), F1 macro (promedio de F1 por clase), IC (intervalo de confianza), kappa de Cohen (acuerdo entre dos etiquetadores descontando el azar), EnKF (Ensemble Kalman Filter, filtro de Kalman por conjuntos).

---

## 1. Brazos

| Brazo | Qué es | Salida | Dónde corre |
|---|---|---|---|
| `lexicon` | `_score_text` de MASSIVE (conteo de palabras) mapeado a clase con umbrales | Etiqueta, sin probabilidad | Local |
| `llm` | El LLM generalista que ya usas (API compatible con OpenAI) con probabilidades verbalizadas en JSON | Etiqueta + probabilidades (declaradas por el modelo) | Según tu proveedor |
| `von` | `von.decide(...)` ([README de Von](https://github.com/wfzyx/von)) | Etiqueta + probabilidades | Local |
| `jev` | API `/api/alpha/decisions` de OpenRouter con `typesafe/jev-1.13` ([OpenRouter](https://openrouter.ai/blog/insights/what-is-jev/)) | Etiqueta + probabilidades | Nube de terceros |

Nota: el endpoint de Jev está en versión alpha según su ruta; si cambia, ajusta `JevArm` en el script.

## 2. Tarea y datos

**Tarea única:** postura del autor hacia un tema objetivo, 3 clases: `a_favor`, `neutral` (incluye "no relacionado"), `en_contra`. Se eligió postura y no sentimiento porque el simulador usa "opinión" y el léxico actual mide sentimiento (diferencia verificada en el código).

**Tamaño:** 300 textos mínimo, 500 recomendado, balanceados aproximadamente entre español e inglés. Con 300 ítems y 80% de precisión, el IC 95% de una precisión es de ±4.5 puntos; con 500, ±3.5 (cálculo normal aproximado, `1.96·√(0.8·0.2/n)`). Diferencias de 2 puntos entre brazos no son detectables con estos tamaños; el script usa bootstrap pareado, que es menos ruidoso que comparar intervalos separados, pero la limitación es real.

**Fuentes (solo legales):**
- Datos que ya tienes por las APIs oficiales y dentro de sus términos.
- Conjuntos públicos de postura. Candidatos que debes verificar tú o un agente (existencia, idioma, licencia): SemEval-2016 Task 6 (inglés) y conjuntos de postura de IberEval/IberLEF (español/catalán). Varios distribuyen solo IDs de tweets, no texto.
- No raspar sitios contra sus términos de servicio para armar la prueba.

**Privacidad:** quitar @usuarios, URLs y cualquier dato personal antes de etiquetar. El brazo `jev` envía el texto a un tercero; usa solo texto público y no sensible.

**Particiones:** `dev` (30%) para ajustar prompts, descripciones de clases y los umbrales del léxico; `test` (70%) solo se mira al final. Nunca ajustar nada con `test`.

**Etiquetado:**
1. Define el tema objetivo en una frase y escribe la guía de etiquetado (qué cuenta como a favor, en contra, neutral) antes de empezar.
2. Etiqueta tú todo el conjunto. Un segundo etiquetador (persona) etiqueta al menos el 20% (columna `label_2`).
3. Calcula kappa de Cohen en ese 20%. Si es menor de ~0.6 (umbral convencional, no mío), la guía es ambigua: corrígela y reetiqueta antes de medir modelos.
4. Preetiquetar con un modelo para acelerar es válido solo si un humano revisa cada etiqueta; una etiqueta de modelo no revisada no es referencia.

Plantilla: `plantilla_etiquetado.csv`.

## 3. Procedimiento

```
# 1) Etiquetar -> etiquetas.csv (columnas de la plantilla)
# 2) Variables de entorno (según los brazos que uses)
export OPENROUTER_API_KEY=...            # jev
export LLM_API_KEY=... LLM_MODEL=... LLM_BASE_URL=...   # llm (API compatible con OpenAI)
pip install von-sdk                      # von (según su README; descarga ~1.5 GB de pesos)

# 3) Fase dev: revisar prompts y umbrales (no mirar test)
python compare_arms.py --data etiquetas.csv --split dev --arms lexicon,llm,von,jev \
    --repo /ruta/a/MASSIVE --target "TEMA OBJETIVO"

# 4) Fijar la regla de decisión (sección 5) y NO tocarla

# 5) Fase test, con repeticiones para medir estabilidad
python compare_arms.py --data etiquetas.csv --split test --arms lexicon,llm,von,jev \
    --repo /ruta/a/MASSIVE --target "TEMA OBJETIVO" --repeat-n 100 --repeat-k 3
```

Todas las respuestas se guardan en `cache/` (una línea JSON por llamada, con la versión del modelo cuando la API la devuelve). Reejecutar no vuelve a gastar llamadas.

## 4. Métricas (el script las calcula)

- **Precisión y F1 macro**, global y por idioma (es/en).
- **Salidas inválidas** (el brazo no devolvió una etiqueta válida), contadas como error.
- **ECE y Brier** para los brazos con probabilidades (para `llm` son probabilidades declaradas por el modelo, no calibradas por construcción).
- **Estabilidad:** en las primeras `--repeat-n` muestras se repite `--repeat-k` veces; se reporta la fracción de ítems cuya etiqueta cambia entre corridas.
- **Latencia** (mediana y p95 por llamada) y **costo estimado por 1 000 textos**. Para `jev` se usan los tokens de entrada que devuelve la API ($0.042 por millón de tokens de entrada, salida gratis, según [OpenRouter](https://openrouter.ai/blog/insights/what-is-jev/); verifica el precio vigente). Para los demás se estima (caracteres/4) y se marca como estimado.
- **Diferencia de precisión pareada con IC 95%** por bootstrap (2 000 remuestreos, semilla fija).

## 5. Regla de decisión (valores propuestos; edítalos ANTES de ver `test`)

Para integrar cualquier brazo distinto del léxico:

- **R0, vale la pena:** el límite inferior del IC 95% de (precisión del brazo − precisión del léxico) es mayor que 0, global y también en español y en inglés por separado. Si no, el léxico se queda (y conviene mejorarlo: negación, listas de palabras).

Para que Von o Jev entren **además** del LLM generalista:

- **R1, no inferioridad:** límite inferior del IC 95% de (brazo − LLM) mayor que −5 puntos, global y por idioma. (El margen de 5 puntos refleja lo que 300-500 ítems permiten detectar; con más datos se puede bajar.)
- **R2, al menos una ventaja real:** ECE menor que la del LLM por ≥ 0.02, o tasa de cambios de etiqueta menor por ≥ 0.02, o mediana de latencia ≥ 5 veces menor, o costo por 1 000 textos ≥ 5 veces menor.
- **R3, condiciones de despliegue (no medibles aquí):** licencias de pesos y datos verificadas (Von); política de retención de datos aceptable y reproducibilidad con versión fija y caché (Jev).

Si el LLM empata o gana, no se integra nada más. Si pasa R0 pero ningún candidato pasa R2, el LLM generalista es la opción por defecto.

## 6. Qué NO prueba este plan

- No mide si mejores observaciones mejoran el pronóstico del EnKF. Eso requiere un caso con desenlace conocido y texto crudo; es un segundo experimento.
- No evalúa extracción de cifras desde documentos (`document_intelligence.py`): ahí un clasificador no sustituye a un LLM.
- El español de tus clientes (variante regional, jerga política) puede diferir de tu muestra; etiqueta con textos del contexto real.
- Si la referencia viene de un solo etiquetador, hereda sus sesgos; por eso el kappa.

## 7. Entregables

1. `etiquetas.csv` con kappa reportado.
2. `results_*.json` y la tabla impresa por el script.
3. Un párrafo de decisión citando R0-R3, escrito antes de integrar nada.
4. Lista de licencias verificadas (pesos de Von, datos de entrenamiento, dependencias nuevas).
