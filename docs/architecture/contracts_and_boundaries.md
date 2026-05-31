# MASSIVE — Contratos y fronteras entre dominios

## Propósito

Definir qué intercambia cada dominio del sistema, cuáles son sus fronteras observables y qué cruces deben considerarse contractuales durante la consolidación.

Este documento no redefine la arquitectura ideal. Describe las **fronteras reales** del sistema actual para evitar refactors que rompan sinergias invisibles.

---

## 1. Principio rector

En MASSIVE, una frontera no se define solo por carpeta o paquete. Se define por una combinación de:
- imports públicos,
- estructuras de datos compartidas,
- constantes y defaults consumidos por varios subsistemas,
- y tests que fijan comportamiento observable.

Por tanto, un contrato puede vivir en:
- una API Python,
- un DTO Pydantic,
- una convención de dict,
- un alias backward-compatible,
- o una surface `__init__.py`.

---

## 2. Frontera A — Núcleo de simulación

### Owner conceptual
`simulator.py`

### Contrato observable
- funciones públicas:
  - `simular`
  - `simular_multiples`
  - `run_with_schedule`
  - `resumen_historial`
- configuración compartida:
  - `DEFAULT_CONFIG`
  - `PROVEEDORES`
  - `RANGOS_DISPONIBLES`
- shape implícito del historial de simulación:
  - lista de dicts
  - cada estado contiene al menos `opinion`
  - muchos flujos esperan además `_regla`, `_regla_nombre`, `_razon`, `_paso`, etc.

### Consumidores críticos
- `app.py`
- `app/__init__.py`
- `massive_core/__init__.py`
- `social_architect.py`
- `forecast/engine.py`
- `forecast/scenarios.py`
- `cfc_trainer.py`
- `benchmarks/runner.py`
- tests

### Regla de frontera
No cambiar firmas, nombres exportados ni estructura básica del historial sin slice dedicado y validación transversal.

---

## 3. Frontera B — Wrappers de compatibilidad

### Owners conceptuales
- `app/__init__.py`
- `massive_core/__init__.py`

### Contrato observable
Permiten importar la API principal sin depender del runtime completo de UI.

### Tipo de contrato
- reexport de símbolos
- superficie pública estable
- compatibilidad de import path

### Regla de frontera
No eliminar ni adelgazar estos wrappers hasta demostrar:
1. quién los consume,
2. cuál será su reemplazo,
3. y que la compatibilidad ya está cubierta.

---

## 4. Frontera C — Forecast temporal

### Owner conceptual
`forecast/`

### Contratos observables
#### API pública de paquete
Desde `forecast/__init__.py`:
- `TemporalConfig`
- `ForecastResult`
- `forecast`
- `ScenarioReport`
- `compare_scenarios`
- `apply_intervention`

#### Configuración temporal tipada
`TemporalConfig` fija:
- `event_type`
- `step_duration_days`
- `time_horizon_days`
- `n_steps`

#### Dependencia contractual hacia simulación
`forecast/scenarios.py` depende de `run_with_schedule`.
`forecast/engine.py` depende de `DEFAULT_CONFIG`.

### Regla de frontera
La capa forecast puede evolucionar internamente, pero su surface pública y su dependencia con el núcleo deben tratarse como contrato explícito.

---

## 5. Frontera D — Social Architect

### Owner conceptual
`social_architect.py`

### Contratos observables
- consume `run_with_schedule`
- consume `resumen_historial`
- consume `DEFAULT_CONFIG`
- consume forecast temporal
- opera con estrategias que siguen la estructura de `StrategyMatrix` / `Intervention`

### Contrato de datos relevante
En `schemas.py`:
- `Intervention`
- `StrategyMatrix`

Estos modelos fijan la forma de:
- fases
- parámetros
- target nodes
- rationale

### Regla de frontera
No alterar shape de estrategias o intervención sin validar:
- architect
- forecast scenarios
- app.py
- tests asociados

---

## 6. Frontera E — Motores especializados

### Owners conceptuales
- `massive_engine.py`
- `multilayer_engine.py`
- `energy_engine.py`

### Contratos observables
#### Massive engine
- consumido por tests
- consumido por `simulator.py`
- depende de `multilayer_engine` para partes de la dinámica

#### Multilayer engine
- consumido por tests
- consumido por `simulator.py`
- depende parcialmente de `simulator` para `PROVEEDORES` en un fallback
- puede consumir CfC (`tau_matrix`)

#### Energy engine
- validado por tests y usado desde su runner/capa asociada

### Regla de frontera
No intervenir un engine suponiendo independencia total del resto. Validar siempre interacciones con simulador, tests y UI cuando aplique.

---

## 7. Frontera F — IA / CfC / LLM

### Owners conceptuales
- `cfc_router.py`
- `cfc_engine.py`
- `cfc_trainer.py`
- `llm_credentials.py`
- `langchain_workflows.py`

### Contratos observables
- `CfCRouter.get()` y `status`
- generación de datasets basada en `simular`
- configuración de proveedores basada en `PROVEEDORES` y resolución de credenciales

### Frontera débil detectada
`multilayer_engine.py` consulta `PROVEEDORES` desde `simulator`, lo que crea un cruce no ideal pero real.

### Regla de frontera
No separar configuración de proveedores o paths CfC sin mapear consumidores indirectos.

---

## 8. Frontera G — Contrato backend/frontend

### Owner conceptual
`backend/app/models/__init__.py`

### Contratos observables
DTOs Pydantic con `extra="forbid"`:
- simulación live (`dto_simulation.py`)
- snapshots históricos (`dto_snapshot.py`)
- forecast (`dto_forecast.py`)
- architect (`dto_architect.py`)

### Evidencia contractual fuerte
- `scripts/gen_ts_types.py` consume el namespace público de DTOs
- `frontend/src/types/api.generated.ts` se genera desde ese contrato
- `tests/test_dto_models.py` valida shape, límites y generación

### Regla de frontera
Cualquier cambio aquí es contractual. No modificar DTOs sin actualizar generación TS y tests.

---

## 9. Frontera H — Schemas de dominio Python

### Owner conceptual
`schemas.py`

### Contratos observables
Modelos como:
- `GamePayoff`
- `StrategicConfig`
- `Intervention`
- `StrategyMatrix`

### Papel arquitectónico
Actúan como contrato Python interno entre:
- simulador
- architect
- forecast scenarios
- teoría de juegos

### Regla de frontera
Tratar `schemas.py` como punto de contrato interno, no como simple utilitario.

---

## 10. Frontera I — Validación

### Owners conceptuales
- `tests/`
- `benchmarks/`
- scripts de validación descritos en `CLAUDE.md`

### Contratos observables
No solo validan outputs; también fijan:
- qué módulos deben poder importarse,
- qué tipos deben mantenerse,
- qué campos deben existir,
- y qué surfaces públicas siguen vivas.

### Regla de frontera
Si un refactor rompe tests de importación, contrato o generación, probablemente rompió una frontera arquitectónica real.

---

## 11. Cruces que deben considerarse sensibles

### Cruce 1
`simulator.py` ↔ `social_architect.py` ↔ `forecast/`

### Cruce 2
`simulator.py` ↔ `multilayer_engine.py`

### Cruce 3
`simulator.py` ↔ `app.py`

### Cruce 4
`backend/app/models` ↔ `scripts/gen_ts_types.py` ↔ `frontend/src/types`

### Cruce 5
`simulator.py` ↔ `cfc_trainer.py` / `cfc_router.py`

Estos cruces no deben tocarse de forma oportunista.

---

## 12. Reglas derivadas

1. Una frontera con tests y surface pública se trata como contrato.
2. Una convención de dict ampliamente consumida también se trata como contrato.
3. Los paquetes con `__all__` y reexports públicos no son simples atajos; son fronteras.
4. `schemas.py` y DTOs deben considerarse partes contractuales, no detalles internos.
5. Si una intervención cambia más de una frontera a la vez, el slice está mal definido.

---

## 13. Conclusión

La consolidación de MASSIVE no puede guiarse solo por mover archivos “a donde deberían estar”. Debe respetar fronteras reales:
- APIs públicas,
- wrappers de compatibilidad,
- contratos Python,
- contratos backend/frontend,
- y shapes de datos usados en múltiples capas.

Consolidar bien significa fortalecer esas fronteras, no ignorarlas.
