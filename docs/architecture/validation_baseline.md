# MASSIVE — Baseline de validación

## Propósito

Registrar el estado real de validación del proyecto antes de cualquier cambio estructural no documental.

Este documento implementa los slices iniciales del plan:
- **Slice 0 — Baseline de validación real**
- **Slice 1 — Registro formal del baseline**

---

## Fecha

2026-05-31

---

## Comando ejecutado

```bash
python -m pytest "MASSIVE actualizado/tests/"
```

Ejecutado desde la raíz del workspace:

```bash
/home/adlg/Escritorio/Proyectos/MASSIVE
```

---

## Resultado

- **276 passed**
- **1 warning**
- **0 failed**
- **0 xfailed**
- tiempo aproximado: **8.40s**

---

## Suite cubierta

Se ejecutaron los tests en:
- `test_cfc_engine.py`
- `test_cfc_router.py`
- `test_dto_models.py`
- `test_empirical_calibration.py`
- `test_empirical_integration.py`
- `test_energy_core.py`
- `test_forecast.py`
- `test_game_theory.py`
- `test_integrated_dynamics.py`
- `test_integration_llm.py`
- `test_massive_engine.py`
- `test_multilayer.py`
- `test_optimization.py`
- `test_pvu_runner.py`
- `test_simulator.py`
- `test_social_architect.py`
- `test_visualizations.py`

---

## Warning observado

```text
pgmpy.estimators.StructureScore is deprecated and will be removed in v1.3.0.
Use pgmpy.structure_score instead.
```

### Interpretación
- No bloquea la suite actual.
- Es deuda técnica externa / de compatibilidad futura.
- No debe mezclarse con la consolidación estructural temprana salvo que pase a romper tests o runtime.

---

## Incidencia de entorno observada

Durante la ejecución apareció un intento de uso de `conda` en el entorno shell, seguido por:

```text
CondaError: Run 'conda init' before 'conda activate'
```

### Interpretación
- La suite de `pytest` sí ejecutó correctamente después de ese mensaje.
- El baseline de tests es válido.
- Sin embargo, el shell local parece tener inicialización parcial o defectuosa relacionada con `conda`.

### Regla operativa derivada
Mientras no sea necesario, evitar depender de activaciones implícitas del shell. Para validaciones futuras, preferir comandos directos y acotados, como en esta baseline.

---

## Conclusión operativa

El proyecto `MASSIVE actualizado` tiene una baseline de validación saludable para continuar con consolidación estructural conservadora:

- la suite principal pasa completa,
- los contratos principales están vivos,
- y no hay evidencia inmediata de rotura sistémica en el estado actual.

Esto habilita continuar con los siguientes slices documentales/técnicos de bajo riesgo.
