# MASSIVE — Primeros slices de ejecución seguros

## Propósito

Traducir la cartografía arquitectónica ya realizada en un conjunto inicial de slices ejecutables, pequeños y seguros.

Estos slices siguen `CLAUDE.md`:
- pensar antes de codificar,
- simplicidad primero,
- cambios quirúrgicos,
- metas verificables.

Y respetan la condición principal del proyecto:

> MASSIVE funciona en conjunto y en sinergia; los slices deben preservar esa realidad.

---

## Regla general

Ninguno de estos slices debe:
- borrar módulos,
- mover árboles completos,
- reemplazar superficies públicas,
- ni mezclar refactor estructural con cambios funcionales amplios.

---

## Slice 0 — Baseline de validación real

### Objetivo
Capturar el estado real de tests y validaciones antes de tocar código.

### Alcance
- ejecutar test suite relevante
- registrar resultado base

### Archivos potencialmente tocados
- ninguno, salvo documentación de progreso si se decide registrar

### Verify
```text
1. Ejecutar pytest sobre el proyecto actual
   → verify: existe baseline real de tests
2. Registrar fallas o xfails observados
   → verify: el plan futuro no trabaja sobre supuestos
3. No modificar código funcional en este slice
   → verify: diff funcional nulo
```

### Riesgo
Muy bajo.

---

## Slice 1 — Registro formal del baseline en documentos operativos

### Objetivo
Conectar la evidencia de validación con el plan arquitectónico.

### Alcance
- actualizar `progress.md` o documento equivalente
- registrar baseline y alcance

### Verify
```text
1. Registrar baseline de validación
   → verify: queda trazabilidad explícita
2. Enlazar baseline con documentos de arquitectura
   → verify: el estado actual puede auditarse
3. No tocar runtime
   → verify: no hay cambios funcionales
```

### Riesgo
Muy bajo.

---

## Slice 2 — Inventario de consumers de `DEFAULT_CONFIG` y `PROVEEDORES`

### Objetivo
Mapear dos constantes críticas antes de cualquier extracción futura desde `simulator.py`.

### Alcance
- documentar quién consume `DEFAULT_CONFIG`
- documentar quién consume `PROVEEDORES`
- clasificar consumo directo vs indirecto

### Razón
Estas constantes son frontera compartida entre UI, LLM, forecast y otros flujos.

### Verify
```text
1. Identificar consumers directos e indirectos
   → verify: lista documentada
2. Clasificar qué consumers dependen de shape vs contenido
   → verify: riesgo de cambio entendido
3. No cambiar aún la ubicación de estas constantes
   → verify: compatibilidad intacta
```

### Riesgo
Bajo si es solo documental.

---

## Slice 3 — Inventario del historial de simulación como contrato implícito

### Objetivo
Documentar la estructura esperada del historial devuelto por `simular` y `run_with_schedule`.

### Alcance
- listar campos mínimos observables
- listar campos opcionales usados en UI/tests/forecast/architect
- distinguir campos estructurales de campos analíticos

### Razón
Mucho del sistema parece acoplado a dicts más que a modelos tipados.

### Verify
```text
1. Identificar campos mínimos del historial
   → verify: contrato implícito explicitado
2. Identificar consumers de campos auxiliares
   → verify: riesgo de cambio localizado
3. No tipar ni reescribir aún el historial
   → verify: cero cambios funcionales
```

### Riesgo
Bajo si es documental.

---

## Slice 4 — Aislamiento documental de la frontera `simulator` ↔ `multilayer_engine`

### Objetivo
Describir exactamente el acoplamiento bidireccional parcial detectado.

### Alcance
- documentar import de `MultilayerEngine` desde `simulator.py`
- documentar consulta de `PROVEEDORES` desde `multilayer_engine.py`
- proponer opciones futuras sin implementar aún

### Verify
```text
1. Describir acoplamiento en ambos sentidos
   → verify: frontera frágil documentada
2. Enumerar riesgos de tocarla
   → verify: no se interviene a ciegas
3. No ejecutar refactor todavía
   → verify: runtime intacto
```

### Riesgo
Bajo si es documental.

---

## Slice 5 — Catálogo de aliases backward-compatible

### Objetivo
Inventariar compatibilidad semántica y nominal, no solo compatibilidad de imports.

### Alcance
- aliases en `empirical_config.py`
- otros nombres heredados observables
- registrar si son runtime-facing o solo transición interna

### Verify
```text
1. Identificar aliases activos
   → verify: mapa de naming backward-compatible disponible
2. Clasificar su criticidad
   → verify: riesgo de limpieza futura entendido
3. No eliminar ninguno
   → verify: sin impacto funcional
```

### Riesgo
Bajo.

---

## Slice 6 — Primer slice técnico de bajo riesgo (futuro, no inmediato)

### Objetivo
Elegir una mejora estructural mínima en una frontera limpia, sin tocar el núcleo.

### Candidatos posibles
- documentación o comments contractuales en scripts de generación
- pequeñas mejoras de encapsulación en subdominios ya limpios
- aclaraciones de compatibilidad en wrappers

### Condición previa
Solo ejecutar este slice después de completar y validar los slices documentales anteriores.

### Verify
```text
1. Elegir una zona con frontera limpia
   → verify: no afecta núcleo ni múltiples dominios
2. Aplicar cambio mínimo y reversible
   → verify: diff pequeño
3. Ejecutar tests relevantes
   → verify: sin regresiones
```

### Riesgo
Bajo, si se elige bien.

---

## Orden recomendado de ejecución

1. Slice 0 — Baseline de validación real
2. Slice 1 — Registro formal del baseline
3. Slice 2 — Consumers de `DEFAULT_CONFIG` y `PROVEEDORES`
4. Slice 3 — Historial de simulación como contrato implícito
5. Slice 4 — Frontera `simulator` ↔ `multilayer_engine`
6. Slice 5 — Aliases backward-compatible
7. Slice 6 — Primer slice técnico de bajo riesgo

---

## Criterio de avance

Solo se avanza al siguiente slice si:
- el actual quedó documentado,
- su verificación se cumplió,
- y no aparecieron dependencias nuevas no mapeadas.

Si aparece una dependencia inesperada, el orden debe revisarse antes de tocar código.
