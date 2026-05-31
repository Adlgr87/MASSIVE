# MASSIVE — Historial de simulación como contrato implícito

## Propósito

Documentar la estructura observable del historial devuelto por:
- `simular`
- `run_with_schedule`

Este documento implementa el **Slice 3 — Historial de simulación como contrato implícito**.

Su objetivo es hacer explícito un hecho arquitectónico importante:

> gran parte de la sinergia actual de MASSIVE depende de listas de `dict` compartidas entre dominios, no de modelos tipados formales.

---

## 1. Tesis

El historial de simulación es hoy un **contrato de datos transversal** entre:
- núcleo de simulación,
- UI,
- social architect,
- forecast,
- benchmarks,
- training CfC,
- y tests.

Aunque no esté formalizado como DTO Pydantic, actúa como una interfaz estable de facto.

Por eso, cualquier intento futuro de tiparlo, reducirlo o renombrar campos debe tratarse como un cambio contractual.

---

## 2. Forma general del historial

### Tipo observable
`list[dict]`

### Convención observable
- cada elemento representa un estado por paso temporal
- el primer elemento suele corresponder al estado inicial
- los elementos posteriores agregan metadatos del régimen y diagnósticos

### Productores observados
- `simular`
- `run_with_schedule`

---

## 3. Campos mínimos observables

Estos son los campos cuya presencia puede considerarse mínima o altamente esperada en la práctica.

## 3.1. `opinion`

### Estado
Campo esencial.

### Evidencia de consumo
- `app.py` construye trayectorias con `h["opinion"]`
- `benchmarks/runner.py` extrae opiniones desde historial
- `cfc_trainer.py` construye trayectorias con `h["opinion"]`
- `tests/test_simulator.py`, `tests/test_forecast.py`, `tests/test_social_architect.py` lo usan explícitamente

### Regla contractual
No puede faltar en un historial válido.

---

## 3.2. Estado base social
Campos observados como parte del estado de simulación principal:
- `propaganda`
- `confianza`
- `opinion_grupo_a`
- `opinion_grupo_b`
- `pertenencia_grupo`

### Evidencia de consumo
- `app.py` usa `historial[-1]["confianza"]` para visualización
- `app.py` grafica o consulta `pertenencia_grupo`
- múltiples reglas del simulador se apoyan en estos campos para evolucionar el estado

### Regla contractual
No todos son obligatorios para cada consumer, pero forman parte del shape esperado del estado social base.

---

## 4. Metadatos estructurales de ejecución

Estos campos no son puramente “analíticos”; ayudan a interpretar el historial como proceso dinámico.

## 4.1. `_paso`

### Uso observado
- `app.py` filtra pasos para logs
- `app.py` arma timelines y eventos de cambio de régimen

### Papel
Identificador temporal explícito del paso.

---

## 4.2. `_regla`

### Uso observado
- `cfc_trainer.py` usa `_regla` para construir labels de régimen

### Papel
ID de la regla aplicada.

### Importancia
Alta para training y análisis interno.

---

## 4.3. `_regla_nombre`

### Uso observado
- `app.py` calcula regla dominante
- `app.py` muestra distribución de reglas
- `app.py` construye tabla de cambios de régimen
- `tests/test_simulator.py` verifica su presencia en pasos no iniciales

### Papel
Nombre legible del régimen aplicado.

### Importancia
Muy alta para UI y trazabilidad.

---

## 4.4. `_razon`

### Uso observado
- `app.py` detecta pasos CfC por prefijo de razón
- `app.py` lo muestra en logs y eventos de régimen

### Papel
Justificación de selección del régimen.

### Importancia
Alta para explicabilidad operativa.

---

## 4.5. `_rango`

### Uso observado
- aparece en exportes y trazabilidad

### Papel
Persistencia del rango de opinión configurado.

### Importancia
Media, pero útil para auditoría y exportación.

---

## 5. Campos analíticos/diagnósticos opcionales

Estos campos no siempre están presentes, pero existen consumers reales cuando aparecen.

## 5.1. `ews`

### Forma observable
```python
{
  "metrics": {
    "variance": [...],
    "autocorr": [...],
    "skewness": [...],
  },
  "flags": {
    "high_variance": bool,
    "high_autocorr": bool,
    "high_skewness": bool,
  }
}
```

### Consumers observados
- `app.py` muestra warnings EWS
- `forecast/engine.py` extrae métricas EWS desde el estado
- `tests/test_forecast.py` usa esa estructura explícitamente

### Importancia
Alta para forecast y señales tempranas.

---

## 5.2. `tda_change`

### Consumers observados
- `app.py` muestra alerta de cambio topológico

### Importancia
Media. Diagnóstico avanzado, pero ya consumido por UI.

---

## 5.3. `_fraccion_adoptantes`

### Consumers observados
- `app.py` lo muestra en logs
- `app.py` lo usa como proxy de contagio en el centro analítico

### Importancia
Media-alta cuando se usa el modelo de umbral heterogéneo.

---

## 5.4. `_sim_grupo_a`, `_sim_grupo_b`

### Consumers observados
- `app.py` los muestra en logs

### Papel
Trazabilidad de homofilia/similitud.

---

## 5.5. `_nash_sigma_a`, `_nash_sigma_b`

### Consumers observados
- `app.py` muestra `_nash_sigma_a` en logs
- `extended_models.py` los produce

### Papel
Trazabilidad del estado estratégico del modelo Nash.

---

## 5.6. `_bayes_uncertainty`

### Consumers observados
- `app.py` lo muestra en logs
- `extended_models.py` lo produce

### Papel
Incertidumbre del modelo bayesiano.

---

## 5.7. `_sir_S`, `_sir_I`, `_sir_R`

### Consumers observados
- `app.py` muestra `_sir_I` y `_sir_R` en logs
- `app.py` usa `_sir_I` como proxy de contagio en el centro analítico
- `extended_models.py` los produce

### Papel
Estado epidemiológico/opinión-contagio del modelo SIR.

### Importancia
Alta dentro de ese régimen.

---

## 6. Campos añadidos fuera del historial puro

Hay una distinción importante:
- el historial en sí es `list[dict]`
- algunos consumers crean un **estado extendido** a partir del último elemento del historial

### Ejemplo observado en `app.py`
Se construye:
- `temporal_state = dict(historial[-1])`
- luego se agregan:
  - `historial`
  - `config`

### Implicación
El contrato no es solo “cada item del historial”, sino también el patrón operativo:
- tomar el último estado,
- enriquecerlo con `historial` y `config`,
- pasarlo a forecast u otros análisis.

---

## 7. Consumers por categoría

## 7.1. UI / visualización
`app.py` consume:
- `opinion`
- `confianza`
- `pertenencia_grupo`
- `_paso`
- `_regla_nombre`
- `_razon`
- `ews`
- `tda_change`
- `_fraccion_adoptantes`
- `_sim_grupo_a`
- `_sim_grupo_b`
- `_nash_sigma_a`
- `_bayes_uncertainty`
- `_sir_I`
- `_sir_R`

## 7.2. Forecast
Consume desde el estado enriquecido:
- `opinion`
- `historial`
- `config`
- `confianza`
- `ews`

## 7.3. Social Architect
`evaluar_resultado()` consume principalmente:
- `opinion`

Pero los flujos más amplios dependen de `run_with_schedule()` y de la compatibilidad general del historial.

## 7.4. Benchmarks
`benchmarks/runner.py` consume:
- `opinion`

## 7.5. Training CfC
`cfc_trainer.py` consume:
- `opinion`
- `_regla`

## 7.6. Tests
Hay tests que fijan explícitamente o implícitamente:
- `opinion`
- `_regla_nombre`
- estructuras `ews`
- semántica del historial como lista de estados

---

## 8. Clasificación contractual de campos

## A. Campos estructurales duros
Cambiar estos es muy riesgoso:
- `opinion`
- `_regla_nombre`
- `_regla`
- `_paso`
- `_razon`

## B. Campos del estado social base
Riesgo alto si se alteran:
- `propaganda`
- `confianza`
- `opinion_grupo_a`
- `opinion_grupo_b`
- `pertenencia_grupo`

## C. Campos diagnósticos opcionales pero ya consumidos
Riesgo medio-alto si se renombran o desaparecen sin transición:
- `ews`
- `tda_change`
- `_fraccion_adoptantes`
- `_sim_grupo_a`
- `_sim_grupo_b`
- `_nash_sigma_a`
- `_bayes_uncertainty`
- `_sir_S`
- `_sir_I`
- `_sir_R`

---

## 9. Reglas derivadas para consolidación futura

1. No tipar ni reemplazar el historial sin inventario completo de consumers.
2. Si se crea un modelo formal para el historial, debe coexistir primero con el shape legacy.
3. No renombrar metadatos estructurales (`_regla_nombre`, `_paso`, `_razon`, `_regla`) sin wrappers o adaptación.
4. Los campos diagnósticos opcionales ya son parte del contrato práctico porque la UI y forecast los consumen.
5. El patrón `dict(historial[-1]) + historial + config` debe considerarse parte del flujo contractual.

---

## 10. Conclusión

El historial de simulación en MASSIVE no es un detalle de implementación. Es un **bus de datos implícito** entre múltiples capas del sistema.

Aunque su forma actual sea flexible y basada en `dict`, ya opera como contrato transversal.

Por ello, la consolidación segura debe:
- reconocer ese contrato,
- documentarlo,
- y solo después considerar tipificación o reestructuración gradual.
