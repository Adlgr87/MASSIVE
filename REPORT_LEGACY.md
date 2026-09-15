# Reporte de Código Obsoleto y Duplicado

**Fecha:** 2026-07-17  
**Projecto:** /home/adlg/Escritorio/Proyectos/MASSIVE  
**Agente:** Legacy Code Architect (DSH subagent)

---

## Resumen Ejecutivo

El repositorio tiene **3 capas de API en paralelo** (legacy `api.py`, `massive-ui-ng/backend/`, y `backend/app/`), **5 archivos re-export deprecated en raíz**, y múltiples duplicados de lógica auth/rate-limit/settings entre `massive-ui-ng` y `backend/app`. La migración a `backend/app/main.py` (`/v1/*`) está parcial pero los artefactos legacy aún están activos y testeados.

---

## 1. Archivos Potencialmente Obsoletos

| Archivo | Razón | Líneas | Acción Sugerida |
|---------|-------|--------|-----------------|
| `api.py` | Marcado `⚠️ DEPRECATED` en docstring. Endpoints en `/api/*`. Tests de parity (`test_api_security.py`) lo importan directamente. No es el entrypoint de producción. | 497 | **Mantener hasta** que `test_api_security.py` migre sus pruebas de parity y el frontend termine de usar `/v1/*`. Luego eliminar. |
| `empirical_calibration.py` (raíz) | Re-export deprecated → `massive.core.empirical_calibration`. Solo importa para backwards-compat. | ~30 | Confirmar que ningún consumer externo lo usa; si no, eliminar. |
| `empirical_config.py` (raíz) | Re-export deprecated → `massive.core.empirical_config`. | ~20 | Igual. |
| `llm_credentials.py` (raíz) | Re-export deprecated → `massive.core.llm_credentials`. | ~15 | Igual. |
| `schemas.py` (raíz) | Emite `DeprecationWarning` en runtime. Re-export → `massive.core.schemas`. | ~25 | Migrar consumidores; eliminar re-export. |
| `energy_schemas.py` (raíz) | Header dice "deprecated, moved to massive/core/". Still defines `Attractor` Pydantic model. | ~85 | Verificar si `Attractor` se usa fuera de tests. Si no, mover a `massive/core/` o eliminar. |
| `micro_schemas.py` (raíz) | Header dice "deprecated, moved to massive/core/". Solo usado por tests de micro_engine. | ~114 | Confirmar uso exclusivo en tests; si es así, mover a `tests/` o consolidar. |
| `gen_report.py` (raíz) | **0 imports externos**. No es llamado por CI, scripts, ni tests. Mencionado en docs de lint como fuente de errores ruff. | 348 | **Eliminar** — código muerto confirmado. |
| `i18n.py` (raíz) | **0 imports externos**. Mencionado en `consolidation_plan.md` como candidato a fusión, pero nunca se ejecutó. | 268 | **Eliminar o migrar** contenido a `massive/core/i18n/` si hay traducciones reutilizables. |
| `massive-ui-ng/` (kit completo) | Header en `main.py` dice "DEPRECATED — duplicate backend". Dockerfiles y docs existen pero **no está en CI raíz** ni en `pyproject.toml`. Referenciado en docs de arquitectura como decisión pendiente (D1). | ~varios | **Decisión de producto requerida:** (a) fusionar, (b) convertir a subdir referencial, o (c) extraer a repo aparte. Sin decisión, permanece como deuda arquitectónica. |

---

## 2. Funcionalidad Duplicada

### 2.1 Rate Limiting

| Módulo 1 | Módulo 2 | Función | Diferencia |
|----------|----------|---------|------------|
| `api.py:103` | `backend/app/security.py:79` | `_rate_limit(request)` vs `rate_limit_dependency(request)` | `api.py` usa contador simple por IP; `security.py` usa `massive_core.config.build_rate_limiter` con backends memory/file. Implementaciones distintas, misma semántica. |
| `massive-ui-ng/backend/app/rate_limit.py` | `massive_core/config/rate_limit.py` | `SlidingWindowLimiter` class | ui-ng tiene su propia implementación de sliding-window; `massive_core` tiene versión con backends pluggables. Código duplicado con divergencia. |
| `massive-ui-ng/backend/app/security.py` | `backend/app/security.py` | `get_api_key()` | Firmas diferentes (sync vs async); validan variables de entorno con nombres distintos. |

### 2.2 Settings / Env Helpers

| Módulo 1 | Módulo 2 | Función |
|----------|----------|---------|
| `massive-ui-ng/backend/app/settings.py:17-31` | `backend/app/settings.py` | `_env_int`, `_env_float`, `_env_bool` existen solo en ui-ng; backend canónico usa `pydantic-settings`. |

### 2.3 Routers de Simulación

| Módulo 1 | Módulo 2 | Nota |
|----------|----------|------|
| `massive-ui-ng/backend/app/routers/simulation.py` (~560 líneas) | `backend/app/routers/sim.py` (~100 líneas) | ui-ng tiene endpoints `/api/simulate`, `/api/simulate/stream`, `/api/explain`, `/api/runs`, SSE, RunStore SQLite. Backend canónico solo tiene `/v1/simulate`. **ui-ng es más completo pero no está conectado al frontend servido.** |

### 2.4 DTOs Duplicados

| ui-ng | backend/app | Estado |
|-------|-------------|--------|
| `models/dto_architect.py` | `models/dto_architect.py` | Copia idéntica |
| `models/dto_forecast.py` | `models/dto_forecast.py` | Copia idéntica |
| `models/dto_simulation.py` | `models/dto_simulation.py` | Copia idéntica |
| `models/dto_snapshot.py` | `models/dto_snapshot.py` | Copia idéntica |
| `models/dto_ui.py` | *(no existe)* | Solo en ui-ng |

> **Nota:** Los 4 DTOs compartidos son duplicados exactos. Cualquier cambio debe aplicarse en ambos lugares o consolidarse en un paquete compartido.

---

## 3. TODOs / FIXMEs / Hack / XXX Pendientes

| Ubicación | Línea | Mensaje | Prioridad |
|-----------|-------|---------|-----------|
| `massive_engine.py` | 670 | `# Fuerza social sobre agentes activos usando TODOS los agentes como fuentes` | Baja — comentario descriptivo, no técnico |
| `scripts/todo_triage.py` | 78 | `_No TODO/FIXME markers found outside experiments/site._` | Info — script de triaje funciona |

> **Conclusión:** No hay TODOs/FIXMEs activos en el código productivo. El único marcador es un comentario descriptivo en `massive_engine.py`.

---

## 4. Imports Innecesarios / Obsoletos

| Archivo | Import | Alternativa / Estado |
|---------|--------|---------------------|
| `tests/test_api_security.py:9` | `import api as api_mod` | Testea el módulo legacy. Debería migrarse a probar solo `backend.app` cuando `api.py` se elimine. |
| `energy_schemas.py` | Define `Attractor` que podría vivir en `massive/core/schemas.py` | Movido teóricamente; archivo raíz aún existe. |
| `micro_schemas.py` | Define `GroupProfile`, `MemberProfile` usados solo por tests | Mover a `tests/fixtures/` o consolidar en `massive/core/schemas.py`. |

---

## 5. Inconsistencias Detectadas

### 5.1 Dev Environment Semantics (docs/architecture/current-state.md §165)
- `api.py:24` valida `MASSIVE_ENV == "dev"`
- `backend/app/security.py:50` valida `== "development"`
- Con `MASSIVE_ENV=development` y sin `MASSIVE_API_KEY`, el backend canónico abre fallback dev pero el legacy devuelve 503.

### 5.2 `massive-ui-ng` no conectado
- El frontend React (`frontend/`) se sirve desde `backend/app/main.py` (unified backend).
- `massive-ui-ng/backend/app/main.py` tiene su propio servidor con `create_app()`, pero **no está referenced** por nginx, docker-compose.yml principal, ni CI.
- Los tests de ui-ng (`massive-ui-ng/tests/`) no corren en el pipeline raíz.

---

## 6. Área de Optimización

### Oportunidad 1: Consolidar `massive-ui-ng/backend/` → `backend/app/`
- **Impacto:** Elimina ~2,000 líneas de código duplicado (security, rate_limit, routers, narrative, run_store, llm_chat, llm_prompts, scenario_parser).
- **Ventaja:** Un solo source of truth para auth, rate-limiting, y routers.
- **Riesgo:** `massive-ui-ng/backend/app/routers/simulation.py` tiene funcionalidad (`/api/explain`, SSE streaming, SQLite run_store) que **no existe** en `backend/app/routers/sim.py`. Hay que migrar esas features antes de eliminar ui-ng.
- **Acción:** Planear migración feature-by-feature en lugar de eliminación brutal.

### Oportunidad 2: Eliminar `api.py` + `test_api_security.py` parity tests
- **Impacto:** -497 líneas de código legacy, -133 líneas de tests de parity.
- **Requisito:** Confirmar que el frontend `frontend/src/services/api.ts` ya no usa `/api/*` (solo `/api/v1/*` que mapea al backend canónico).
- **Acción:** Verificar en `frontend/src/services/api.ts` el baseURL y endpoints usados.

### Oportunidad 3: Limpieza de re-exports deprecated en raíz
- **Archivos:** `empirical_calibration.py`, `empirical_config.py`, `llm_credentials.py`, `schemas.py`
- **Impacto:** -100 líneas de wrappers inútiles.
- **Riesgo:** Si algún consumer externo (package installed via pip) usa estas vías, se rompe compatibilidad.
- **Acción:** `grep -r "from empirical_calibration\|from empirical_config\|from llm_credentials\|from schemas import"` en todo el repo para confirmar que solo se usan internamente.

### Oportunidad 4: Eliminar `gen_report.py` y `i18n.py`
- **Impacto:** -616 líneas de código completamente muerto.
- **Riesgo:** Bajo — 0 imports confirmados.
- **Acción:** Eliminar directamente.

### Oportunidad 5: Unificar rate-limiting
- **Estado actual:** 3 implementaciones (api.py, massive-ui-ng/rate_limit.py, massive_core/config/rate_limit.py).
- **Acción:** Documentar cuál es la canonical (`massive_core.config.build_rate_limiter`) y hacer que `api.py` y `massive-ui-ng` la re-exporten en lugar de tener su propia lógica.

---

## 7. Archivos Sin Uso Confirmado

| Archivo | Lýneas | Importadores externos | Veredicto |
|---------|--------|----------------------|-----------|
| `gen_report.py` | 348 | 0 | **ELIMINAR** |
| `i18n.py` | 268 | 0 | **ELIMINAR o MIGRAR** |
| `energy_schemas.py` | ~85 | Solo tests own | **CONSOLIDAR** en `massive/core/schemas.py` |
| `micro_schemas.py` | 114 | Solo tests | **MOVER a `tests/fixtures/`** |
| `schemas.py` (raíz) | ~25 | Varios (emite warning) | **MANTENER** hasta migración completa |

---

## 8. Resumen de Prioridades

| Prioridad | Hallazgo | Esfuerzo | Impacto |
|-----------|----------|----------|---------|
| 🔴 Alta | `gen_report.py` + `i18n.py` eliminados | Bajo (1 PR) | -616 líneas, limpia CI ruff |
| 🔴 Alta | Consolidar DTOs duplicados (ui-ng ↔ backend/app) | Medio (2 PRs) | Un solo source of truth |
| 🟡 Media | Decisión de producto sobre `massive-ui-ng/` | Alto (planificación) | Reduce deuda arquitectónica |
| 🟡 Media | Unificar rate-limiting a `massive_core.config` | Medio | Elimina 2 implementaciones |
| 🟢 Baja | Migrar tests de parity de `api.py` | Bajo | Prep para eliminación de api.py |
| 🟢 Baja | Eliminar re-exports deprecated de raíz | Bajo | Código más limpio |
