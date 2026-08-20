# Estrategia de tests — MASSIVE

> Fecha: 2026-08-20. Baseline verificada: 483 passed / 2 failed / 2 módulos sin colectar en HEAD `288ba9a`.

## 1. Pirámide objetivo

```
        ┌─────────┐   E2E/Smoke (docker-e2e, /health, flujo mínimo)
       ┌───────────┐  Contrato (OpenAPI/DTO ↔ tests; /v1/llm contract JSON)
      ┌─────────────┐ Integración (routers + services + motores reales sin red)
     ┌───────────────┐ Unitarias (numerics, schemas, config, validaciones)
```

## 2. Estado actual (verificado)

- 48 archivos en `tests/`; suite completa ~38 s en 2 vCPU (rápida — apta para gate de PR).
- Cobertura de motores: tests de reproducibilidad RNG (`test_rng_reproducibility.py`,
  `test_engine_reproducibility.py`), scientific stack, PVU runner, kalman, forecast, etc.
- Contract test LLM existente (`test_llm_endpoint.py`) **roto por divergencia de contrato** (PR #84) — reparación en Hito 0.
- 20 tests antes "skipped" por torch ahora corren (torch instalado); 0 skipped en la última ejecución.
- CI (`pytest.yml`) estratifica core/scientific/api/full-suite — el job full-suite es el que está rojo.

## 3. Reglas

1. **Ninguna exclusión permanente de módulos en pytest**: los 2 módulos rotos se reparan, no se ignoran.
2. **Bugfix ⇒ test de regresión** en el mismo PR (ej.: SEC-02 con test de entornos).
3. **Motores científicos**: cambios de comportamiento exigen (a) test de caracterización previo capturando salidas con seed fija, (b) comparación con tolerancia numérica explícita, (c) justificación en el PR.
4. **Contratos**: `/v1/llm/run_simulation` se valida contra `configs/llm_contract/massive_llm_contract.json` (fuente de verdad v1.1.0). Cambios de DTO ⇒ regenerar `frontend/src/types/api.generated.ts` (`scripts/gen_ts_types.py`) — el workflow `validate_ts_types` lo exige.
5. **Seguridad**: tests de auth (401/503/429), uploads maliciosos y no-fuga de secretos en respuestas/logs.
6. **Smoke Docker**: `docker-e2e.yml` ya existe (build + health) — mantener verde.

## 4. Cobertura

- Signoff previo (2026-08-16): 47% agregado. **Por medir en HEAD** con:
  `python -m pytest tests/ --cov --cov-report=term` (config en `pyproject.toml [tool.coverage]`).
- Umbral: se fijará tras medir, como `baseline − 0` inicial y subiendo por hitos. Nada de cifras arbitrarias.

## 5. Priorización de rutas críticas para nuevos tests

1. `backend/app/routers/llm.py` + `services/llm_orchestrator.py` (clasificación y dispatch).
2. `backend/app/security.py` + `api.py` auth (entornos y claves).
3. Flujo mínimo E2E: config → simulate → resultado → summary (vía `/v1/simulate`).
4. Uploads `/api/extract` (extensiones, tamaño, contenido malicioso).
