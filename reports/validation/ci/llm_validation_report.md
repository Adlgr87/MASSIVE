# LLM Run-Simulation Endpoint — Validación Final

**Generated:** 2026-08-16 (run from `/home/adlg/Escritorio/Proyectos/MASSIVE` with `.venv`)
**Endpoint:** `POST /v1/llm/run_simulation`
**Spec reference:** `configs/llm_contract/massive_llm_contract.json`
**Entrypoint de backend:** `backend/app/main.py` (FastAPI UI-NG) — enrutador `backend/app/routers/llm.py`, servicio `backend/app/services/llm_orchestrator.py`.

> ⚠️ **Contexto sobre el estado previo al QA.** Al iniciar la validación, los
> artefactos del endpoint (`/v1/llm/run_simulation`, `llm_orchestrator.py`,
> los DTOs `LLMRunRequest`/`LLMRunResponse`/`LLMAmbiguityResponse`) **no
> existían todavía** en el working tree ni en la historia de git. La
> especificación del contrato existía en `configs/llm_contract/` y servía como
> base para la implementación. La implementación se completó como parte de
> este ciclo (ver §5) y luego se validó.

---

## 1. Tests que cubren el endpoint LLM

Comando de ejecución (equivalente a CI):

```bash
env -u GROQ_API_KEY -u OPENAI_API_KEY -u OPENROUTER_API_KEY \
  .venv/bin/python -m pytest -v -k "llm or LLM" -p no:cacheprovider
```

- **Tests coleccionados que coinciden:** 18  (6 escenarios de contrato en
  `tests/test_llm_endpoint.py` + 7 tests de cobertura adicionales en
  `tests/test_llm_orchestrator_coverage.py` + 5 preexistentes en
  `tests/test_integration_llm.py`).
- **Resultado:** ✅ `18 passed, 0 failed, 0 errors`.
- La suite se ejecuta en ~3–4 s y es **offline-first**: ningún test lanza
  tráfico real al LLM (se usan clasificaciones por keyword + dispatch
  determinista, y `api_key='fake-llm-key'` para forzar la rama configurada).

---

## 2. Validación TestClient de todos los paths del contrato

Se usó `fastapi.testclient.TestClient` contra `create_app()` (modo *open dev*
sin claves de API configuradas — válido para CI offline). Cada escenario
suministra `api_key: "fake-llm-key"` a menos que el path lo pida explícitamente.

| # | Path requerido | Test | Status | Asserts clave |
|---|----------------|------|--------|---------------|
| 1 | multilayer básico | `test_multilayer_basic` | ✅ 200 | `classified_motor='multilayer_engine'`, `timeline` ≥ 1, `metrics.dominant_rule` |
| 2 | energy + Factbook Brasil | `test_energy_with_factbook_brasil` | ✅ 200 | `classified_motor='energy_engine'`, `country_code_resolved='BR'`, asunción con Factbook |
| 3 | forecast | `test_forecast` | ✅ 200 | `classified_motor='forecast_model'`, `timeline` ≥ 1 |
| 4 | LLM key faltante (503) | `test_missing_llm_key_returns_503` | ✅ 503 | `detail` menciona proveedor/configuración |
| 5 | intent ambiguo (422 + requested_fields) | `test_ambiguous_intent_returns_422_with_fields` | ✅ 422 | `detail` + `requested_fields` incluye `motor_override` |
| 6 | intent vacío (422) | `test_empty_intent_returns_422` | ✅ 422 | Error de validación de pydantic menciona `intent` |

**Detalle de implementación por path:**

- **1. Multilayer básico.** El clasificador de keyword (`red|social|...`)
  asigna `multilayer_engine`; el dispatcher llama a
  `services.simulation_service.run_multilayer_simulation(n_agents=200)`.
  Devuelve `SimAggregateMetrics` + `TimelineTick[]` construidos a partir de la
  serie de opiniones por capa.
- **2. Energy + Factbook Brasil.** El keyword `energ[ií]a` + `country_code=BR`
  dispara `_augment_with_factbook` → `services.factbook_service.country_params`
  → parámetros del CIA Factbook. El dispatcher usa
  `run_scalar_simulation(escenario='campana', ...)`.
- **3. Forecast.** El keyword `forecast` → `forecast_model`; dispatcher llama a
  `services.forecast_service.baseline_forecast` (baseline `naive`) sobre una
  serie sintética de 10 observaciones y horizonte acotado (1..36).
- **4. LLM key faltante → 503.** `llm_orchestrator.run_simulation` resuelve
  credenciales con `services.llm_service.resolve_llm_credentials`. Si
  `configured == False` (ni `api_key` en request ni variables de entorno ni
  keys) eleva `ServiceUnavailable`, que el router traduce a `HTTPException(503)`.
- **5. Intent ambiguo → 422.** Un intent sin keyword motor reconocible
  (`"Brasil"`) eleva `AmbiguityError(detail, requested_fields=[...])` → el
  router responde con `LLMAmbiguityResponse` (422).
- **6. Intent vacío → 422.** `intent=""` viola `min_length=5` de pydantic →
  FastAPI devuelve 422 de validación automáticamente (no llega al
  orquestador).

---

## 3. Coverage del módulo

Ejecución con `--cov` sobre los tres módulos implementados:

```bash
.venv/bin/python -m pytest tests/test_llm_endpoint.py \
  tests/test_llm_orchestrator_coverage.py \
  --cov=backend.app.services.llm_orchestrator \
  --cov=backend.app.routers.llm \
  --cov=backend.app.models.dto_llm --cov-report=term-missing
```

| Módulo | Stmts | Miss | Branch | BrPart | Cover | Missing (líneas) |
|--------|------:|-----:|-------:|-------:|------:|------------------|
| `backend/app/models/dto_llm.py` | 34 | 0 | 0 | 0 | **100%** | — |
| `backend/app/routers/llm.py` | 20 | 0 | 0 | 0 | **100%** | — |
| `backend/app/services/llm_orchestrator.py` | 155 | 8 | 44 | 6 | **93.0%** | 78, 102, 141-142, 143→145, 234-235, 236→238, 280-281 |
| **TOTAL** | **209** | **8** | **44** | **6** | **94.5%** | |

### Líneas sin cubrir en el orquestador (justificación)

- `141-142` / `234-235` / `236→238` — ramas de *factbook augment failure*
  (`except Exception` defensivo) y de motor micro/massive sin provider real.
- `78`, `102` — casos límite de detección de país por nombre en inglés y de
  ISO-2 *non-standard*.
- `280-281` — rama `motor == "factbook_validation"` con `params` vacíos.
- `143→145` — branch parcial de `if col:` (columna vacía en serie multilayer).

**Conclusión de cobertura:** los módulos router y DTO están al **100 %**; el
orquestador está al **93 %** con las líneas no cubiertas siendo ramas
defensivas / de proveedores no disponibles offline. El umbral del 90 % se
supera con holgura.

---

## 4. Resultado de la validación de QA

- ✅ Todos los tests del endpoint LLM pasan (18 passed).
- ✅ Los 6 paths contractuales validados con TestClient.
- ✅ Coverage: DTO 100 %, router 100 %, orquestador 93 % (total 94.5 %).
- ✅ No regresiones: `tests/test_dto_models.py`, `tests/test_contracts.py`,
  `tests/test_api_security.py`, `tests/test_services_layer.py` siguen verdes
  tras el ensamblaje de `backend/app/main.py`.

### Recomendaciones para el siguiente sprint
1. Añadir tests de integración que ejerzan `factbook_validation` con dataset
  completo (cubriría líneas 280-281).
2. Añadir un caso para el flujo `flow_inverse` (búsqueda inversa) del contrato,
   no implementado en este ciclo.
3. Considerar promover el 503 a una respuesta estructurada
   (`LLMAvailabilityError` con `retry_after`) para clientes que hacen polling.

---

## 5. Artefactos implementados (para este QA)

| Archivo | Rol |
|---------|-----|
| `backend/app/models/dto_llm.py` | `LLMRunRequest`, `LLMRunResponse`, `LLMAmbiguityResponse` + `MOTOR_ENUM`. |
| `backend/app/models/__init__.py` | Re-export de los DTOs LLM. |
| `backend/app/services/llm_orchestrator.py` | `run_simulation`, clasificador de keyword, dispatchers por motor, manejo de 422/503. |
| `backend/app/routers/llm.py` | Router `POST /v1/llm/run_simulation` (auth + rate-limit + mapeo de errores). |
| `backend/app/main.py` | Registro del router `llm` en `create_app()`. |
| `tests/test_llm_endpoint.py` | 6 tests de contrato (TestClient). |
| `tests/test_llm_orchestrator_coverage.py` | 7 tests de cobertura ampliada. |
| `configs/llm_contract/massive_llm_contract.json` | Especificación de contrato (preexistente, usada como fuente de verdad). |
