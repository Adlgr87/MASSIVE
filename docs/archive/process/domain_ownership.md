# MASSIVE — Ownership conceptual por dominio

## Propósito

Asignar ownership conceptual a cada dominio del sistema para reducir ambigüedad estructural durante la consolidación.

Este documento **no** define propietarios humanos, sino propietarios arquitectónicos: dónde vive cada responsabilidad y qué frontera debe protegerse.

---

## D1. Orquestación de simulación

### Owner conceptual
`simulator.py`

### Responsabilidad
- API principal de simulación
- selección de reglas
- integración de mecanismos transversales
- integración con engines, CfC, empirical, EWS/TDA
- compatibilidad pública más amplia del sistema

### Superficie pública asociada
- `simular`
- `simular_multiples`
- `run_with_schedule`
- `resumen_historial`
- constantes exportadas desde `simulator`

### Dependencias críticas
- `massive_engine.py`
- `multilayer_engine.py`
- `empirical_calibration.py`
- `cfc_router.py`
- `extended_models.py`
- `utility_logic.py`
- `schemas.py`

### Riesgo estructural
Máximo. No intervenir sin slice propio.

---

## D2. Motores especializados

### Owners conceptuales
- `massive_engine.py`
- `multilayer_engine.py`
- `energy_engine.py`

### Responsabilidad
- ejecutar dinámicas especializadas
- ofrecer capacidades de simulación masiva, multicapa y energética
- servir como subsistemas para `simulator.py` y/o `app.py`

### Riesgo estructural
Alto. Deben tratarse como motores conectados al sistema, no como librerías aisladas.

---

## D3. Social Architect / optimización

### Owner conceptual
`social_architect.py`

### Responsabilidad
- búsqueda inversa de estrategias
- narrativa de intervención
- coordinación entre simulación, optimización y forecast

### Dependencias críticas
- `simulator.py`
- `intervention_optimizer.py`
- `forecast/`
- `cfc_router.py`

### Riesgo estructural
Alto. Capa transversal entre IA, simulación y planeamiento.

---

## D4. Forecast temporal

### Owner conceptual
`forecast/`

### Responsabilidad
- predicción temporal analítica/escenarios
- comparación de intervenciones
- API de forecast reutilizable

### Superficie pública asociada
`forecast/__init__.py`

### Dependencias críticas
- `simulator.py`
- `schemas.py`
- `empirical_config.py`

### Riesgo estructural
Medio-alto. Tiene buena frontera de paquete, pero está integrado al core.

---

## D5. IA / routing / credenciales

### Owners conceptuales
- `cfc_router.py`
- `cfc_engine.py`
- `cfc_trainer.py`
- `llm_credentials.py`
- `langchain_workflows.py`

### Responsabilidad
- resolución de modelos
- fast paths CfC
- entrenamiento de modelos CfC
- credenciales y acceso a proveedores

### Dependencias críticas
- `simulator.py`
- `social_architect.py`
- `multilayer_engine.py`
- `app.py`

### Riesgo estructural
Alto por transversalidad, aunque no sea la API principal.

---

## D6. UI y experiencia operativa

### Owner conceptual
`app.py`

### Responsabilidad
- integración de controles, visualización y ejecución de flujos
- composición de capacidades del sistema
- punto principal de interacción humana

### Dependencias críticas
- `simulator.py`
- `social_architect.py`
- `forecast/`
- `visualizations.py`
- `cfc_router.py`
- conectores sociales y motores especializados

### Riesgo estructural
Muy alto. No es una UI delgada; es ensamblador operativo.

---

## D7. Contrato backend/frontend

### Owner conceptual
`backend/app/models/__init__.py`

### Responsabilidad
- exportar DTOs públicos del dominio API
- fijar contrato de intercambio backend/frontend
- alimentar generación de tipos TS

### Dependencias críticas
- `scripts/gen_ts_types.py`
- `frontend/src/types/api.generated.ts`
- `tests/test_dto_models.py`

### Riesgo estructural
Alto por impacto contractual, aunque la frontera esté bien encapsulada.

---

## D8. Validación y benchmark

### Owner conceptual
`tests/` + `benchmarks/`

### Responsabilidad
- fijar arquitectura observable
- detectar regresiones
- validar claims científicos o de integración

### Riesgo estructural
No son implementación, pero sí frontera de verdad operativa.

---

## D9. Compatibilidad y adapters

### Owners conceptuales
- `massive_core/__init__.py`
- `app/__init__.py`
- aliases backward-compatible

### Responsabilidad
- sostener imports estables
- desacoplar consumidores de detalles de runtime
- permitir transición arquitectónica sin rotura brusca

### Riesgo estructural
Muy alto en consolidación temprana. No tocar sin necesidad real.

---

## D10. Modularización parcial / zonas en observación

### Owners conceptuales provisionales
- `massive/`
- `massive/core/micro/`
- `micro_massive/` residual

### Responsabilidad
Pendiente de consolidación o clarificación.

### Estado actual
No deben asumirse como fuente de verdad general del proyecto.

### Riesgo estructural
Alto por ambigüedad.

---

## Conclusión

El ownership actual de MASSIVE no está organizado todavía por una única jerarquía de paquetes. Está distribuido entre:
- superficies de raíz,
- wrappers de compatibilidad,
- subpaquetes bien definidos,
- y zonas parciales de modularización.

La consolidación debe respetar ese mapa real en vez de imponer uno imaginado.
