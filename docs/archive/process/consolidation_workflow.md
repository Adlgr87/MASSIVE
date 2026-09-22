# MASSIVE — Workflow de consolidación estructural

## Propósito

Definir el flujo de trabajo obligatorio para cualquier tarea de consolidación estructural en MASSIVE.

Este workflow existe para minimizar riesgo en un sistema sinérgico y con antecedentes de cambios destructivos.

---

## Reglas del workflow

1. No se modifica estructura sin reconocimiento previo.
2. No se mueve una superficie pública sin wrapper de compatibilidad.
3. No se mezcla refactor estructural con cambio funcional en el mismo slice.
4. No se borran piezas legacy en fases tempranas.
5. Cada slice debe tener validación explícita y rollback simple.

---

## Fase 0 — Baseline y congelación lógica

### Objetivo
Capturar qué estructura y qué comportamiento estamos protegiendo.

### Acciones
- identificar entradas públicas activas
- identificar adapters/wrappers
- identificar contratos tipados
- identificar tests que fijan arquitectura observable
- registrar riesgos y supuestos

### Verificación
- existe inventario arquitectónico
- existe visión de consolidación
- existe lista inicial de superficies públicas

---

## Fase 1 — Mapa de sinergias

### Objetivo
Entender cómo se acoplan realmente los dominios del sistema.

### Acciones
- mapear dependencias entre:
  - `simulator.py`
  - `app.py`
  - `social_architect.py`
  - `forecast/`
  - `multilayer_engine.py`
  - `massive_engine.py`
  - `energy_engine.py`
  - `backend/app/models/`
  - scripts de generación y validación
- clasificar acoplamientos en:
  - públicos
  - internos
  - opcionales
  - experimentales

### Verificación
- cada dominio crítico tiene fronteras identificadas
- no se asume independencia donde hay dependencia real

---

## Fase 2 — Definición de ownership por dominio

### Objetivo
Asignar una fuente de verdad conceptual a cada área.

### Acciones
- declarar para cada dominio:
  - propósito
  - owner estructural
  - superficie pública
  - dependencias autorizadas
  - dependencias riesgosas

### Verificación
- cada dominio crítico tiene owner y límites explícitos
- no quedan módulos ambiguos sin clasificación

---

## Fase 3 — Consolidación documental

### Objetivo
Asegurar que las decisiones arquitectónicas existan en documentos antes de tocar código.

### Acciones
- mantener actualizados:
  - `module_inventory.md`
  - `consolidation_vision.md`
  - `consolidation_workflow.md`
  - `consolidation_plan.md`
  - `safety_protocol.md`

### Verificación
- una persona nueva puede entender el plan sin depender de contexto oral

---

## Fase 4 — Ejecución por slices mínimos

### Objetivo
Aplicar consolidación en pasos pequeños, acotados y verificables.

### Cada slice debe incluir
1. alcance exacto
2. archivos afectados
3. riesgo esperado
4. criterio de éxito
5. validación local
6. plan de rollback

### Orden recomendado
1. wrappers y adapters
2. utilidades puras
3. contratos y scripts sin impacto funcional central
4. motores secundarios
5. integración con UI
6. núcleo legacy/orquestación

### Verificación por slice
- imports esperados siguen funcionando
- tests del área pasan
- tests globales relevantes pasan
- el diff es pequeño y trazable

---

## Fase 5 — Contracción de superficie legacy

### Objetivo
Solo cuando exista equivalencia demostrada, reducir duplicación real.

### Acciones
- identificar wrappers que ya son redundantes
- verificar ausencia de consumidores críticos
- validar reemplazo estable
- documentar retiro

### Verificación
- el retiro no rompe tests ni contratos públicos
- existe evidencia de equivalencia previa

---

## Formato obligatorio para cada intervención futura

```text
1. [Paso concreto] → verify: [check concreto]
2. [Paso concreto] → verify: [check concreto]
3. [Paso concreto] → verify: [check concreto]
```

Ejemplo:

```text
1. Extraer helper interno de forecast sin cambiar imports públicos
   → verify: tests/test_forecast.py pasa
2. Mantener wrapper en el punto legacy
   → verify: imports existentes siguen resolviendo
3. Ejecutar validación global relevante
   → verify: pytest tests/ pasa o reporta solo fallas preexistentes
```

---

## Criterio de detención

Se debe detener la ejecución y revisar el plan si ocurre cualquiera de estos casos:
- aparece una dependencia no mapeada
- un cambio exige mover demasiados archivos a la vez
- la validación rompe zonas no relacionadas
- un wrapper de compatibilidad no puede mantenerse limpio
- hay ambigüedad sobre la fuente de verdad de un dominio
