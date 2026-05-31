# MASSIVE — Protocolo de seguridad para consolidación estructural

## Propósito

Establecer reglas operativas obligatorias para cualquier cambio estructural en MASSIVE.

Este protocolo asume:
- antecedentes de daño previo por automatización,
- alto acoplamiento sistémico,
- y necesidad de cambios conservadores y verificables.

---

## Principio general

> En MASSIVE, la seguridad estructural tiene prioridad sobre la velocidad de refactor.

---

## Reglas obligatorias

### Regla 1 — No asumir independencia de módulos
Si un módulo parece aislado, debe verificarse en código y tests antes de tratarlo como tal.

### Regla 2 — No borrar en fases tempranas
Durante la consolidación inicial no se eliminan:
- wrappers,
- módulos legacy,
- adapters,
- rutas de import públicas,
- ni artefactos de compatibilidad.

### Regla 3 — No mezclar estructura con lógica
Un cambio estructural no debe introducir al mismo tiempo cambios funcionales amplios.

### Regla 4 — No tocar más de un dominio crítico por slice
Dominios críticos incluyen:
- simulador principal
- UI principal
- social architect
- forecast
- contratos backend/frontend
- motores especializados

### Regla 5 — Toda intervención debe ser trazable
Cada archivo tocado debe poder justificarse directamente por el slice en curso.

### Regla 6 — Validación obligatoria
Cada slice debe declarar su verificación antes de ejecutarse.

### Regla 7 — Si hay ambigüedad, se detiene
Ante cualquiera de estas condiciones, la ejecución debe pausarse:
- fuente de verdad desconocida
- dependencia inesperada
- contratos no mapeados
- tests que fijan comportamiento no entendido

---

## Checklist previo a cualquier cambio

- [ ] El dominio está identificado.
- [ ] La superficie pública afectada está identificada.
- [ ] Los consumidores conocidos están identificados.
- [ ] El cambio está limitado a un slice pequeño.
- [ ] Existe criterio de verificación.
- [ ] Existe rollback simple.

---

## Checklist posterior a cualquier cambio

- [ ] Los imports esperados siguen resolviendo.
- [ ] Los tests relevantes del área pasan.
- [ ] El diff es pequeño y justificable.
- [ ] No se introdujeron cambios adyacentes innecesarios.
- [ ] Se actualizó la documentación de arquitectura/progreso.

---

## Operaciones explícitamente prohibidas en fases tempranas

- mover árboles completos de archivos por intuición
- borrar wrappers “porque parecen redundantes”
- unificar paquetes sin inventario de consumidores
- reemplazar imports públicos globalmente
- reducir superficie legacy sin evidencia de equivalencia
- combinar limpieza estética con consolidación estructural

---

## Criterio de rollback

Debe revertirse o replantearse un slice si:
- rompe compatibilidad observable,
- obliga a tocar demasiados archivos nuevos,
- altera contratos no previstos,
- o revela que el alcance fue mal delimitado.

---

## Regla específica para agentes y automatización

Cualquier agente o colaborador automatizado debe operar bajo esta secuencia:

```text
1. Reconocer → verify: dependencias y superficie afectada entendidas
2. Delimitar → verify: alcance pequeño y verificable
3. Ejecutar → verify: cambios mínimos
4. Validar → verify: tests/comprobaciones relevantes
5. Documentar → verify: hallazgos y decisiones registrados
```

Si no puede cumplir esa secuencia, no debe ejecutar el cambio.
