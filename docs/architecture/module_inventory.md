# MASSIVE — Inventario arquitectónico basado en evidencia

## Propósito

Este documento registra el reconocimiento estructural de `MASSIVE actualizado` realizado **antes de cualquier consolidación**. Su objetivo es evitar decisiones basadas en README o suposiciones superficiales.

Se redacta bajo el protocolo de `CLAUDE.md`:
- pensar antes de codificar,
- simplicidad primero,
- cambios quirúrgicos,
- ejecución guiada por objetivos verificables.

## Premisa fundamental

MASSIVE **no funciona como un conjunto de funciones aisladas**. El sistema opera como un ensamblaje sinérgico donde UI, simulación, forecast, LLM/CfC, validación, DTOs y motores especializados comparten datos, imports y contratos.

Por tanto, cualquier consolidación estructural debe tratar el repositorio como un **sistema acoplado** y no como carpetas independientes.

---

## 1. Evidencia principal observada

### 1.1. La superficie pública real sigue anclada en módulos raíz

Evidencia leída:
- `simulator.py`
- `massive_engine.py`
- `multilayer_engine.py`
- `intervention_optimizer.py`
- `app.py`
- `app/__init__.py`
- `massive_core/__init__.py`
- múltiples tests en `tests/`

Hallazgo:
- Los tests importan principalmente desde módulos de raíz, por ejemplo:
  - `from simulator import ...`
  - `from massive_engine import ...`
  - `from multilayer_engine import ...`
  - `from intervention_optimizer import ...`
- `app/__init__.py` reexporta desde `simulator`.
- `massive_core/__init__.py` también reexporta desde `simulator`.

Conclusión:
- La compatibilidad y el comportamiento observable del sistema siguen dependiendo de la **superficie legacy de raíz**.
- Hoy `massive_core` actúa como adaptador, no como fuente de verdad independiente.

### 1.2. `massive/` existe pero no actúa aún como núcleo operativo consolidado

Evidencia observada:
- `massive/` solo contiene `core/`
- `massive/core/` contiene `micro/`
- no apareció un árbol amplio de módulos Python activos bajo `massive/core/` en el reconocimiento

Conclusión:
- La consolidación hacia `massive/` quedó incompleta o parcial.
- A día de hoy no puede asumirse que `massive/` sea el centro real del sistema.

### 1.3. `simulator.py` es el punto de acoplamiento central

Evidencia en imports de `simulator.py`:
- `benchmarks.butterfly_diagnostic`
- `massive_engine.MassiveEngine`
- `multilayer_engine.MultilayerEngine`
- `schemas.GamePayoff`
- `utility_logic.calculate_strategic_force`
- `llm_credentials.resolve_provider_api_key`
- `empirical_calibration.*`
- `cfc_router.CfCRouter` (opcional)
- `extended_models.*` (opcional)
- dependencias científicas (`numpy`, `scipy`, `networkx`, `requests`)

Conclusión:
- `simulator.py` no es un módulo simple: es un **orquestador híbrido** que conecta:
  - dinámica social base,
  - motores integrados,
  - calibración empírica,
  - selección LLM,
  - fast path CfC,
  - diagnósticos,
  - teoría de juegos,
  - TDA y EWS.
- Tocar su posición o interfaz sin estrategia de compatibilidad sería de alto riesgo.

### 1.4. `app.py` depende de una red transversal de módulos

Evidencia observada en `app.py`:
- importa desde:
  - `i18n`
  - `llm_credentials`
  - `social_architect`
  - `visualizations`
  - `forecast`
  - `simulator`
  - `cfc_router` (opcional)
  - conectores sociales y motores especializados dentro del flujo de UI

Conclusión:
- La UI Streamlit no es una capa fina. Es un **integrador operativo** de múltiples dominios.
- Una consolidación estructural no puede asumir que `app.py` solo consume una API limpia y estable; hoy participa de varias uniones internas del sistema.

### 1.5. `social_architect.py` depende del simulador, optimización y forecast

Evidencia observada:
- `from simulator import run_with_schedule, resumen_historial, DEFAULT_CONFIG`
- `from intervention_optimizer import optimize_interventions`
- `from forecast import TemporalConfig, forecast`
- uso opcional de `cfc_router`

Conclusión:
- El arquitecto social no es un módulo aislado de IA; depende del núcleo de simulación y de la capa temporal.
- Cualquier cambio estructural aquí tiene impacto transversal.

### 1.6. `multilayer_engine.py` también está acoplado al ecosistema

Evidencia observada:
- depende de `llm_credentials`
- depende de `state_compression`
- usa `cfc_router` opcionalmente para la `tau_matrix`

Conclusión:
- El motor multicapa tampoco es independiente. Participa del sistema LLM/CfC y del pipeline de compresión.

### 1.7. Existe un contrato backend/frontend tipado y validado por tests

Evidencia observada:
- `backend/app/models/*`
- `scripts/gen_ts_types.py`
- tests en `tests/test_dto_models.py`
- archivo generado en `frontend/src/types/api.generated.ts`

Conclusión:
- El sistema ya tiene un subdominio con una disciplina de contrato más fuerte:
  - DTOs Pydantic en backend
  - generación de tipos TS
  - verificación por tests
- Esta zona puede servir de referencia metodológica para futuras consolidaciones.

### 1.8. Los tests actuales codifican la arquitectura observable

Evidencia observada:
- `tests/test_simulator.py`
- `tests/test_integrated_dynamics.py`
- `tests/test_energy_core.py`
- `tests/test_multilayer.py`
- `tests/test_massive_engine.py`
- `tests/test_integration_llm.py`
- `tests/test_social_architect.py`
- `tests/test_dto_models.py`

Conclusión:
- Aunque exista una visión más modular en documentos previos, la arquitectura que realmente cuenta es la que los tests consumen.
- Hoy los tests fijan como superficie estable principalmente a los módulos de raíz.

---

## 2. Mapa conceptual del sistema actual

## 2.1. Superficies públicas activas

### Legacy/root public surface
- `simulator.py`
- `massive_engine.py`
- `multilayer_engine.py`
- `intervention_optimizer.py`
- `energy_engine.py`
- `forecast/`
- `social_architect.py`
- `app.py`

### Wrappers / adapters
- `app/__init__.py`
- `massive_core/__init__.py`

### Typed contract zone
- `backend/app/models/`
- `scripts/gen_ts_types.py`
- `frontend/src/types/`

### Partial modularization zone
- `massive/core/micro/`
- `micro_massive/` (aparentemente reducido o residual)

---

## 3. Riesgos de consolidación detectados

### Riesgo 1 — Confundir arquitectura objetivo con arquitectura real
Existe evidencia documental previa de una modularización más profunda, pero la evidencia del código y tests muestra que la raíz sigue siendo crítica.

### Riesgo 2 — Tratar módulos como independientes
No aplica a MASSIVE. El sistema está acoplado en:
- imports,
- contratos de datos,
- tests,
- flujos UI,
- motores internos,
- y rutas de compatibilidad.

### Riesgo 3 — Reubicar `simulator.py` prematuramente
Es el módulo con más acoplamiento transversal. Moverlo o vaciarlo demasiado pronto sería una operación de alto riesgo.

### Riesgo 4 — Suponer que `massive_core` ya desacopló el sistema
La evidencia indica que `massive_core` aún reexporta desde `simulator` y no constituye una independencia estructural real.

### Riesgo 5 — Romper contratos backend/frontend durante un refactor estructural amplio
La zona DTO + TS generation ya tiene validación automática; debe tratarse como frontera estable.

---

## 4. Oportunidades de consolidación reales

### Oportunidad A — Consolidar documentación y ownership antes del código
Es la acción de menor riesgo y mayor retorno inmediato.

### Oportunidad B — Separar dominios por responsabilidad, no solo por carpeta
Dominios observables:
- simulación legacy/orquestación
- motores especializados
- social architect / optimización
- forecast temporal
- contratos DTO / frontend
- CfC / LLM / credenciales
- validación y benchmarks

### Oportunidad C — Usar wrappers como estrategia intermedia
La evidencia muestra que MASSIVE ya tolera wrappers/adapters (`app/__init__.py`, `massive_core/__init__.py`).
Eso sugiere que la consolidación segura debe avanzar mediante:
1. extracción interna,
2. wrappers estables,
3. validación,
4. y solo después reducción de duplicación.

---

## 5. Conclusión operativa

La consolidación estructural de MASSIVE debe partir de esta verdad:

> El sistema actual es híbrido, sinérgico y todavía fuertemente centrado en módulos de raíz. La modularización existente es parcial y no debe sobreestimarse.

Por lo tanto:
- primero se consolida el mapa arquitectónico,
- luego se fijan reglas de intervención,
- después se trabaja por slices pequeños y verificables,
- y solo al final se evalúa reducción de superficie legacy.

Cualquier otra secuencia aumenta innecesariamente el riesgo de daño estructural.
