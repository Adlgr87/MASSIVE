# Pull Request

## Resumen de cambios

Describe brevemente qué se ha modificado y por qué.

### Tipo de cambio

- [ ] Nueva funcionalidad (feature)
- [ ] Corrección de error (bug fix)
- [ ] Mejora de rendimiento
- [ ] Refactorización
- [ ] Documentación
- [ ] Otro

## Módulos afectados

- [ ] `massive_core/data_assimilation/` — EnKF, filtro EnKF disperso
- [ ] `massive_core/network_inference/` — Reconstrucción de red (DE, CG)
- [ ] `massive_core/numerics/` — Steppers, estabilidad, motor multicapa disperso
- [ ] `massive_core/physics/` — Perturbación, mecánica estadística
- [ ] `tests/` — Pruebas unitarias
- [ ] `frontend/` — UI, generated types
- [ ] `README.md` / `README_ES.md` — Documentación
- [ ] `massive_engine.py` — Motor principal

## Checklist

- [ ] Las pruebas existentes siguen pasando (`pytest tests/`)
- [ ] Se han añadido pruebas para nueva funcionalidad
- [ ] No se han roto APIs públicas legacy
- [ ] La documentación se ha actualizado
- [ ] Se ha seguido el protocolo de `CLAUDE.md`

## Notas de integración

Si este PR toca el motor principal (`massive_engine.py`) o el frontend, especificar cambios en las rutas de la API o la UI.
