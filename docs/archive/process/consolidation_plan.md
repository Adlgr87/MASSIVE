# MASSIVE — Plan de consolidación estructural

## Goal

Consolidar la estructura de MASSIVE sin romper su comportamiento sinérgico ni su compatibilidad observable.

---

## Success criteria

La consolidación será exitosa cuando:

1. exista un mapa claro de dominios y ownership,
2. la superficie pública estable quede identificada y protegida,
3. cada intervención estructural pueda ejecutarse por slices pequeños,
4. los tests sigan validando la arquitectura observable,
5. y se reduzca la ambigüedad estructural sin introducir daño sistémico.

---

## Alcance de este plan

### Incluye
- documentación de arquitectura
- inventario y clasificación de dominios
- workflow de intervención
- protocolo de seguridad
- priorización de futuros slices

### No incluye aún
- refactor masivo del código
- eliminación agresiva de módulos legacy
- mover archivos por lotes grandes
- rediseñar la UI o el simulador principal

---

## Dominios detectados

### D1. Orquestación de simulación
Archivos núcleo observados:
- `simulator.py`
- `schemas.py`
- `utility_logic.py`
- `empirical_calibration.py`
- `extended_models.py`

### D2. Motores especializados
- `massive_engine.py`
- `multilayer_engine.py`
- `energy_engine.py`
- `energy_runner.py`
- `energy_schemas.py`
- `state_compression.py`

### D3. Social Architect / optimización
- `social_architect.py`
- `intervention_optimizer.py`
- `programmatic_architect.py`

### D4. Forecast temporal
- `forecast/`

### D5. IA / routing / credenciales
- `cfc_engine.py`
- `cfc_router.py`
- `cfc_trainer.py`
- `llm_credentials.py`
- `langchain_workflows.py`

### D6. UI y visualización
- `app.py`
- `i18n.py`
- `visualizations.py`
- `social_connectors.py`
- `cache_manager.py`

### D7. Contratos backend/frontend
- `backend/app/models/`
- `scripts/gen_ts_types.py`
- `frontend/src/types/`

### D8. Validación y benchmarks
- `tests/`
- `benchmarks/`
- `docs/validation/`
- scripts de validación descritos en `CLAUDE.md`

### D9. Modularización parcial / compatibilidad
- `massive_core/__init__.py`
- `app/__init__.py`
- `massive/core/micro/`
- `micro_massive/`

---

## Priorización de consolidación

## Prioridad 1 — Claridad estructural y ownership
Objetivo: eliminar ambigüedad antes de tocar código.

Acciones:
- consolidar documentación arquitectónica
- declarar ownership por dominio
- registrar contratos públicos

Verify:
- documentación completa y consistente

## Prioridad 2 — Superficies públicas y wrappers
Objetivo: distinguir claramente entre:
- superficie pública estable
- implementación interna
- wrappers de compatibilidad

Acciones:
- catalogar reexports y adapters
- decidir qué wrappers deben preservarse

Verify:
- inventario de wrappers disponible
- imports públicos actuales identificados

## Prioridad 3 — Dominios de bajo riesgo
Objetivo: preparar futuros slices en zonas menos peligrosas.

Posibles candidatos futuros:
- scripts
- utilidades puras
- documentación de generación de tipos
- zonas claramente encapsuladas

Verify:
- lista de slices de bajo riesgo preparada

## Prioridad 4 — Núcleo altamente acoplado
Objetivo: intervenir solo cuando la cartografía y wrappers estén maduros.

Incluye:
- `simulator.py`
- `app.py`
- integración social architect / forecast / CfC / engines

Verify:
- existe un plan específico por slice antes de cualquier cambio

---

## Primer backlog recomendado

### Slice A — Mapa de wrappers y compatibilidad
- catalogar `app/__init__.py`, `massive_core/__init__.py` y cualquier reexport residual
- verify: inventario documentado

### Slice B — Ownership por dominio
- crear documento con owner conceptual de cada zona
- verify: todos los dominios críticos clasificados

### Slice C — Fronteras de contratos tipados
- documentar dependencias entre DTOs, script TS y tests
- verify: contrato backend/frontend explicitado

### Slice D — Dependencias transversales del simulador
- documentar enlaces entre `simulator.py`, motores, CfC, empirical, architect y forecast
- verify: mapa sistémico disponible

---

## Política de ejecución

Ningún slice futuro debe comenzar sin este formato:

```text
1. [Paso] → verify: [check]
2. [Paso] → verify: [check]
3. [Paso] → verify: [check]
```

Y ningún slice debe cerrar sin dejar actualizado:
- inventario
- progreso
- riesgos abiertos
