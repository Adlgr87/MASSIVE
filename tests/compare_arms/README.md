# Clasificación de Postura — Comparación de Brazos

Script para comparar diferentes métodos de clasificación de postura/stance (3 clases: `a_favor`, `neutral`, `en_contra`) sobre textos sociales.

## Brazos

| Brazo | Qué es | Salida | Dónde corre |
|---|---|---|---|
| `lexicon` | `score_text` de `massive/core/sentiment.py` (conteo de palabras) | Etiqueta, sin probabilidad | Local |
| `llm` | LLM vía API compatible con OpenAI (GPT, Claude, etc.) | Etiqueta + probabilidades | Según proveedor |
| `von` | `von.decide(...)` (modelo local) | Etiqueta + probabilidades | Local |
| `jev` | API `/api/alpha/decisions` de OpenRouter | Etiqueta + probabilidades | Nube terceros |
| `mock` | Solo para testing (probabilidades aleatorias) | Etiqueta + probabilidades | Local |

## Uso rápido

```bash
# Lexicon + mock (sin dependencias externas)
python compare_arms.py --arms lexicon,mock --target "politica" \
  --data tests/compare_arms/plantilla_etiquetado.csv --split all

# Con LLM (requiere OPENAI_API_KEY, LLM_MODEL, LLM_BASE_URL)
python compare_arms.py --arms lexicon,llm --target "politica" \
  --data etiquetas.csv --split test

# Con Von (requiere instalar 'von' package)
pip install von
python compare_arms.py --arms lexicon,von --target "politica" \
  --data etiquetas.csv --split test

# Con Jev (requiere OPENROUTER_API_KEY)
python compare_arms.py --arms lexicon,jev --target "politica" \
  --data etiquetas.csv --split test
```

## Datos

Usa `plantilla_etiquetado.csv` como plantilla. Formato:

| Columna | Descripción |
|---------|-------------|
| `id` | Identificador único |
| `text` | Texto a clasificar |
| `lang` | `es` o `en` |
| `target` | Tema objetivo |
| `label` | `a_favor`, `neutral`, o `en_contra` |
| `label_2` | (opcional) etiqueta de segundo anotador |
| `split` | `dev` o `test` |

## Métricas

- Accuracy
- F1 macro
- ECE (Expected Calibration Error)
- Brier score
- Bootstrap CI (pareado)
- Latencia

## Decisiones (R0–R3)

El script imprime veredictos según umbrales configurables:
- R0: ¿Algún brazo supera al léxico en precisión global?
- R1: ECE ≤ 0.05?
- R2: F1 macro ≥ 0.75?
- R3: Calidad de probabilidades (Brier < léxico)

Ver `plan_prueba_clasificacion.md` para el plan completo de prueba.
