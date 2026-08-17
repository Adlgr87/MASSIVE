# MASSIVE — Especificación de Arquitectura de Producción (Fase 1)

> **Arquitecto de Software — MASSIVE Master Orchestrator**  
> **Estado:** Activo · **Versión del spec:** 0.1.0 · **Base de código:** commit `2026-05-27` (recuperación)  
> **Propósito:** Definir la arquitectura lógica, superficies de interfaz oficiales, stack de producción y roadmap para llevar MASSIVE de prototipo/legacy a un producto cloud-ready.

---

## 1. Contexto del Cartógrafo (Inventario del Sistema)

El repositorio `Adlgr87/MASSIVE` exhibe una **estructura dual y evolutiva**:

### 1.1 Superposición de capas

| Capa | Path | Rol | Estado |
|------|------|-----|--------|
| **Legacy API** | `api.py` (raíz) | FastAPI monolítico; endpoints `/api/*` (extract, wizard, simulate-uil) + `/health`, `/ready`, `/version`. Auth-gated con `X-API-Key`. Rate-limit en memoria. | Productivo pero legacy — NO versionado bajo `/v1` |
| **UI-NG Backend** | `backend/app/` | Espacio de paquetes para la nueva pila. Contiene `models/` con DTOs pydantic v2 (`dto_architect.py`, `dto_forecast.py`, `dto_simulation.py`, `dto_snapshot.py`). **No contiene `main.py` aún** — es un paquete de modelos + contratos pendiente de wiring. | En construcción |
| **UI-NG Frontend** | `frontend/` | React 18 + Vite + TypeScript + Tailwind. Cliente oficial futuro. Genera tipos TS desde DTOs via `scripts/gen_ts_types.py`. | En construcción (skeleton) |
| **Adapter científico opt-in** | `massive_core/` | Fachada estable sobre módulos legacy. Re-exporta `simular`, `run_scientific_simulation`, contratos (`SimulationState`, `SimulationConfig`), `RateLimiter`, `ScientificRuntimeConfig`, logging centralizado. | Activo, es la "puerta de entrada" recomendada para nuevos consumidores |
| **Simulación multi-agente** | `micro_massive/` | Motor de grupos pequeños (3-15 agentes). Personalidades Forer + matriz de influencia + teoría de juegos evolutiva. | Autónomo, con CLI propia (`MicroOrchestrator`) |
| **Motores legacy** | raíz (`simulator.py`, `energy_engine.py`, `multilayer_engine.py`, `massive_engine.py`, `social_architect.py`, `forecast/`) | Núcleo de física/social. Mantener compatibilidad con CLAUDE.md §4. | Legacy — inmantean los existentes |

### 1.2 Punto de tensión crítico

> **`backend/app/main.py` NO EXISTE.**  
> El `backend/app/__init__.py` solo contiene un docstring.  
> El punto de entrada productivo actual es `api.py` en la raíz, no `backend/app/main.py`.

Esto significa que la "Fase 1 del Master Orchestrator" debe **definir** esta superficie, no solo documentarla. La migración de `api.py` → `backend/app/main.py` es parte del roadmap.

---

## 2. Arquitectura Lógica

### 2.1 Diagrama textual de capas

```
┌─────────────────────────────────────────────────────────────────┐
│                      CLIENTES OFICIALES                         │
├─────────────────────────────────────────────────────────────────┤
│  UI-NG (React SPA)  │  CLI (legacy wrapper)  │  LLM Agents (HTTP) │
├─────────────────────────────────────────────────────────────────┤
│                    API GATEWAY / ENTRYPOINT                      │
│                  backend/app/main.py (FastAPI)                   │
│                                                                 │
│   middleware: auth(get_api_key) │ cors │ rate_limit │ logging    │
├─────────────────────────────────────────────────────────────────┤
│                     ROUTING & VERSIONING                         │
│  GET  /            → root info                                  │
│  GET  /health      → liveness                                  │
│  GET  /ready       → readiness (LLM + adapter checks)          │
│  GET  /version     → build metadata                            │
│  POST /v1/simulate → run_scalar_simulation (simulator.py)      │
│  POST /v1/scientific → run_scientific_simulation (opt-in)      │
│  POST /v1/factbook → build_engine_from_country                 │
│  POST /v1/benchmarks → benchmark runner (offline/real/llm)     │
│  POST /v1/llm/run_simulation → UIL full_pipeline (LLM)         │
├─────────────────────────────────────────────────────────────────┤
│                    SERVICE LAYER (backend/)                       │
│  services/simulation_service.py  → simular / MultilayerEngine    │
│  services/forecast_service.py   → forecast/engine.py           │
│  services/factbook_service.py   → massive.core.factbook        │
│  services/llm_service.py        → llm_credentials, wizard      │
├─────────────────────────────────────────────────────────────────┤
│                    ADAPTER CIENTÍFICO (massive_core/)            │
│  contracts.py         → SimulationState, SimulationConfig      │
│  scientific_runner.py → run_*_scientific_simulation               │
│  config/              → settings, logging, rate_limit            │
├─────────────────────────────────────────────────────────────────┤
│                    MOTORES LEGACY (raíz)                         │
│  simulator.py, energy_engine.py, multilayer_engine.py,          │
│  massive_engine.py, social_architect.py, forecast/engine.py     │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Flujo de datos canónico

1. **Cliente** → envía petición HTTP a `/v1/*` con payloads `dict` (no pydantic input DTOs, siguiendo convención actual).
2. **Entrypoint FastAPI** (`backend/app/main.py`) → valida auth, rate-limit, parsea payload.
3. **Service layer** (`services/`) → adapta payload a firma legacy; aplica defaults de `AppSettings`.
4. **massive_core** → opcional, envuelve con scientific config; re-exporta símbolos legacy.
5. **Motores legacy** → ejecutan simulación.
6. **Respuesta** → se valida contra DTOs de salida (`backend.app.models.*`) y se serializa como JSON estructurado.

### 2.3 Invariants

- **CLAUDE.md §4:** `simular` y `simular_multiples` deben mantener compatibilidad. Nuevas funcionalidades viven en módulos nuevos.
- **AGENTS.md:** DTOs usan `extra="forbid"`; payloads de entrada son `dict` con `_rate_limit`, `_public_error`.
- **Reproducibilidad:** Semillas pasadas explícitamente via `seed=` — no son globales env vars.

---

## 3. Interfaces Oficiales de Producción

### 3.1 API HTTP FastAPI (`backend/app/main.py` — EN CONSTRUCCIÓN)

#### 3.1.1 Endpoints versionados (`/v1/`)

| Método | Path | Wrapper legacy | Service target | Auth | Rate-limit |
|--------|------|----------------|----------------|------|------------|
| `POST` | `/v1/simulate` | `simular` + `resumen_historial` | `run_scalar_simulation` | `X-API-Key` | 60/min |
| `POST` | `/v1/scientific` | `simular` + scientific runner | `run_scientific_simulation` | `X-API-Key` | 30/min |
| `POST` | `/v1/factbook` | `MassiveEngine.from_factbook` | `build_engine_from_country` | `X-API-Key` | 30/min |
| `POST` | `/v1/benchmarks` | `benchmarks.runner` | `_massive_offline_forecast` / real / llm | `X-API-Key` | 10/min |
| `POST` | `/v1/llm/run_simulation` | `UILAdapter.full_pipeline` | `UILAdapter` | `X-API-Key` + LLM key | 30/min |

#### 3.1.2 Endpoints de infraestructura (ya existentes en `api.py`)

| Método | Path | Descripción | Auth |
|--------|------|-------------|------|
| `GET` | `/` | Info del servicio | No |
| `GET` | `/health` | Liveness probe | No |
| `GET` | `/ready` | Readiness (verifica LLM + adapter) | No |
| `GET` | `/version` | Metadata de build | No |

#### 3.1.3 Endpoints legacy (deprecados pero mantenidos en v0.1)

| Método | Path | Status |
|--------|------|--------|
| `POST` | `/api/extract` | Deprecado — mover a `/v1/llm/extract` en v0.2 |
| `POST` | `/api/wizard` | Deprecado — mover a `/v1/llm/wizard` en v0.2 |
| `POST` | `/api/simulate-uil` | Deprecado — reemplazado por `/v1/llm/run_simulation` |
| `POST` | `/api/v1/forecast` | Ya versionado — migrar a `/v1/forecast` en v0.2 |
| `POST` | `/api/v1/architect` | Ya versionado — migrar a `/v1/architect` en v0.2 |
| `POST` | `/api/v1/energy` | Ya versionado — migrar a `/v1/energy` en v0.2 |

#### 3.1.4 Convenciones de respuesta

**Cuerpo de error estructurado (HTTP):**

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable summary",
    "details": {
      "field": "user_goal",
      "issue": "must be non-empty string"
    },
    "request_id": "req_abc123",
    "timestamp": "2026-08-16T13:30:00Z"
  }
}
```

**Códigos de error canónicos:**

| Código | HTTP Status | Causa |
|--------|-------------|-------|
| `VALIDATION_ERROR` | 400 | Payload no conforme |
| `UNAUTHORIZED` | 401 | API key inválida/faltante |
| `FORBIDDEN` | 403 | Auth OK pero acceso denegado |
| `RATE_LIMITED` | 429 | Límite de rate excedido |
| `EXTERNAL_SERVICE_ERROR` | 502 | LLM provider no disponible |
| `INTERNAL_ERROR` | 500 | Error inesperado (nunca se expone stack trace) |

> **Política anti-fuga de información:** `_public_error()` en `api.py` ya implementa el patrón. Todos los endpoints `/v1/*` deben usarlo. Nunca se devuelve stack trace interno al cliente.

### 3.2 CLI (envoltura legacy)

La CLI envuelve las APIs legacy existentes. Se implementa como entry-point en `pyproject.toml`:

```bash
# Simulación escalar (legacy)
python -m massive.cli simulate --escenario campana --pasos 50 --seed 42

# Simulación con schedule de intervenciones (Modo Inverso)
python -m massive.cli simulate --schedule schedule.json --config config.yaml

# Simulación científica (opt-in)
python -m massive.cli simulate --scientific --enable-report --enable-enkf --observations obs.json

# Benchmark offline
python -m massive.cli benchmark --cases datasets/pvu_cases --offline --out reports/ci --seed 42
```

**Entry-point en `pyproject.toml`:**

```toml
[project.scripts]
massive = "massive.cli:cli_main"
massive-cli = "massive.cli:cli_main"
```

### 3.3 UI Web Angular UI-NG (cliente oficial)

- **Stack:** React 18, Vite, TypeScript, Tailwind (ya inicializado en `frontend/`).
- **Contrato con API:** Tipos TS auto-generados desde DTOs pydantic via `scripts/gen_ts_types.py`.
- **Auth:** API key inyectada via Vite env (`VITE_MASSIVE_API_KEY`); en dev usa fallback `dev-secret-key`.
- **Endpoints consumidos:** `/v1/simulate`, `/v1/scientific`, `/v1/factbook`, `/v1/benchmarks`, `/v1/llm/run_simulation`.

### 3.3.1 Política de exposición vs. interno

| Elemento | Exposición | Comentario |
|----------|-----------|-----------|
| `simular`, `simular_multiples` | **Interno** | Se accede vía service layer, no exportado directamente por API |
| `run_with_schedule` | **Interno** | Usado por CLI y `/v1/scientific` indirectlyamente |
| `buscar_estrategia_inversa` | **Interno** | Envuelto por `/v1/llm/run_simulation` |
| `SocialEnergyEngine` | **Interno** | Accedido vía `/v1/scientific` |
| `ForecastEngine` | **Interno** | Accedido vía `/v1/forecast` (heredado) |
| DTOs (`backend.app.models.*`) | **Público (salida)** | Definen el contrato API; versionados |
| `massive_core.*` | **Interno + opt-in** | Para consumidores científicos avanzados |
| `micro_massive.*` | **Interno** | Motor autónomo; CLI propia |

---

## 4. Stack de Producción

### 4.1 Variables de entorno (`.env.example`)

El `.env.example` actual carece de variables críticas para producción. **Se requiere un `.env.example` consolidado** con al menos:

```bash
# ── Core ─────────────────────────────────────────────────────
MASSIVE_API_KEY=change-me-in-prod
MASSIVE_ENV=production          # development | staging | production
MASSIVE_CORS_ORIGINS=https://massive-ui.example.com
MASSIVE_RATE_LIMIT_PER_MIN=60
MASSIVE_RATE_LIMIT_BACKEND=file
MASSIVE_RATE_LIMIT_PATH=/var/cache/massive/rate_limit.json
MASSIVE_MAX_UPLOAD_MB=10

# ── Logging ──────────────────────────────────────────────────
MASSIVE_LOG_FILE=/var/log/massive/app.log
PYTHONHASHSEED=42              # para CI/reproducibilidad

# ── LLM Providers ────────────────────────────────────────────
PROVIDER=groq
GROQ_API_KEY=your-groq-key
OPENAI_API_KEY=your-openai-key
OPENROUTER_API_KEY=your-openrouter-key

# ── Social Media Seeding (opcional) ──────────────────────────
TWITTER_BEARER_TOKEN=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=

# ── Observabilidad (v0.3) ────────────────────────────────────
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
MASSIVE_SLO_ERROR_BUDGET=0.05
MASSIVE_SLO_P95_LATENCY_MS=2000
```

> **Nota de seguridad:** `MASSIVE_API_KEY` no debe usar fallback inseguro en producción. `api.py` ya implementa fail-closed cuando `MASSIVE_ENV != "dev"` y la key no está configurada.

### 4.2 Manejo de errores

**Patrón existente (`api.py`):**

```python
def _public_error(exc: Exception) -> HTTPException:
    log.exception("API error: %s", exc)  # logging estructurado interno
    return HTTPException(status_code=500, detail="Internal server error")
```

**Extensión en `/v1/*`:**

```python
from uuid import uuid4
from datetime import datetime, timezone

def _error_response(request_id: str, code: str, message: str,
                    status_code: int = 500, details: dict = None) -> JSONResponse:
    payload = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }
    if details:
        payload["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=payload)

def _public_error(exc: Exception) -> JSONResponse:
    rid = str(uuid4())
    log.error("request_id=%s error=%s type=%s", rid, exc, type(exc).__name__, exc_info=True)
    return _error_response(rid, "INTERNAL_ERROR", "Internal server error", 500)
```

### 4.3 Logging estructurado con campos por módulo

**Centralizado en `massive_core/config/logging_setup.py`:**

```python
log = get_logger("massive.api")        # para endpoints FastAPI
log = get_logger("massive.services.simulation")  # para service layer
log = get_logger("massive.engine.simulator")  # para motor legacy
log = get_logger("massive.scientific_runner")  # para núcleo científico
log = get_logger("massive.benchmarks.runner")   # para benchmarks
log = get_logger("massive.micro_orchestrator")  # para micro_massive
```

**Formato estructurado (JSON en producción):**

```json
{"timestamp": "2026-08-16T13:30:00Z", "level": "INFO", "module": "massive.api", "request_id": "req_abc", "message": "simulation completed", "sim_id": "sim_123", "steps": 50}
```

**Configuración del formato (propuesta para v0.2):**

- `development`: leer humano, colores con `coloredlogs`
- `production`: JSON estructurado con `jsonlog` o `pydantified` logging

**Rotación de logs:** Ya soportado via `RotatingFileHandler` en `logging_setup.py` (`max_bytes=10MB`, `backup_count=5`).

### 4.4 Empaquetado y despliegue

#### Docker multi-stage (existente, optimizar en v0.2)

| Stage | Base | Responsabilidad | Output |
|-------|------|-----------------|--------|
| `builder-py` | `python:3.11-slim` | `pip wheel` de todo `requirements.txt` | `/wheels/` |
| `builder-fe` | `node:20-alpine` | `npm ci` + `npm run build` (React/Vite) | `/usr/share/nginx/html` |
| `runtime` | `python:3.11-slim` | Instala wheels (offline), nginx + supervisord | Imagen final |

**Supervisord gestiona:**

| Proceso | Puerto | Usuario |
|---------|--------|---------|
| `uvicorn api:app` | 127.0.0.1:8000 | `appuser` (non-root) |
| `streamlit run app.py` | 8501 | `appuser` (non-root) |
| `nginx` | 80 | root (solo para binding) |

**docker-compose.yml ya expone:**

- `80` → nginx (frontend + API gateway)
- `8000` → FastAPI (directo, opcional)
- `8501` → Streamlit (legacy)

#### nginx routing (existente)

| Ruta | Target |
|------|--------|
| `/` | `/usr/share/nginx/html` (SPA) |
| `/api/` | `api_backend` (127.0.0.1:8000) |
| `/docs`, `/openapi.json`, `/health`, `/ready`, `/version` | `api_backend` |
| `/ui/` | `streamlit_backend` (8501, con Upgrade headers) |
| `/{static assets}` | nginx directo (cache 30d) |

---

## 5. Roadmap de Producción

### 5.1 v0.1 — Empaquetado Básico, CI, Documentación Mínima

**Objetivo:** Baseline estable para desarrollo y CI.

| Ítem | Estado | Acción |
|------|--------|--------|
| ✅ `README.md` | Hecho | Documenta instalación, uso rápido, Docker |
| ✅ `requirements.txt` | Hecho | Dependencias declaradas |
| ✅ `pyproject.toml` | Hecho | Metadata `0.1.0`, `build-system = maturin` |
| ✅ `Dockerfile` | Hecho | Multi-stage + nginx + supervisord |
| ✅ `docker-compose.yml` | Hecho | 3 puertos expuestos |
| ✅ CI `pytest.yml` | Hecho | Jobs: core, scientific, api, full-suite |
| ✅ CI `docker-e2e.yml` | Hecho | Smoke test del stack Docker |
| ✅ `.env.example` | Parcial | Falta: observabilidad, DB, production flags |
| ⬜ `backend/app/main.py` | **Pendiente** | Migrar endpoints `/api/*` → `/v1/*` desde `api.py` |
| ⬜ CLI oficial | **Pendiente** | `python -m massive.cli` con `simulate`, `benchmark` |
| ⬜ TypeScript generado | Parcial | `scripts/gen_ts_types.py` funciona; CI `validate_ts_types.yml` activo |
| ⬜ Documentación API | Parcial | `docs/api.md` (mkdocstrings); no hay OpenAPI spec escrita |

**Criterio de "done" v0.1:**

- `uvicorn backend.app.main:app` levanta el servidor con todos los endpoints `/v1/*`.
- `python -m massive.cli --help` muestra sub-comandos.
- CI verde en GitHub Actions (core + scientific + api + docker-e2e).
- `.env.example` completo con todas las variables de entorno críticas.
- Docker image reproducible con `docker compose build`.

### 5.2 v0.2 — Contrato MASSIVE-LLM y Endpoints para LLMs

**Objetivo:** Interfaz estable para agentes LLM y orquestadores externos.

| Ítem | Acción |
|------|--------|
| **`backend/app/main.py`** — establecer como entry-point principal |
| Migrar `/api/v1/forecast` → `/v1/forecast` (URL limpia) |
| Migrar `/api/v1/architect` → `/v1/architect` |
| Migrar `/api/v1/energy` → `/v1/energy` |
| Deprecar `/api/extract`, `/api/wizard`, `/api/simulate-uil` con header `X-API-Warn` |
| **`/v1/llm/run_simulation`** — wrapper de `UILAdapter.full_pipeline` |
| **`/v1/llm/wizard`** — `services.llm_service.wizard_config` |
| **`/v1/llm/extract`** — `UILAdapter.from_document` con upload file |
| **OpenAPI v1 generado** — exportar spec a `/openapi/v1.json` |
| **CLI completa** — `massive simulate`, `massive scientific`, `massive benchmark`, `massive llm run` |
| **`.env.example`** — añadir `MASSIVE_LLM_TIMEOUT_SECONDS`, `MASSIVE_LLM_MAX_RETRIES` |

**Contrato MASSIVE-LLM (esqueleto):**

```json
POST /v1/llm/run_simulation
X-API-Key: <key>
Content-Type: application/json

{
  "description": "Reduce polarization in a polarized community",
  "country": "US",
  "steps": 100,
  "seed": 42,
  "llm": {
    "provider": "groq",
    "model": "llama-3.3-70b-versatile"
  },
  "config_overrides": {
    "alpha_blend": 0.6
  }
}

→ 200 OK
{
  "sim_id": "sim_abc123",
  "config": { ... },
  "summary": { ... },
  "history": [ ... ],
  "narrative": "..."
}
```

**Criterio de "done" v0.2:**

- Contrato MASSIVE-LLM documentado y testeado.
- Deprecación de endpoints legacy con migración graceful.
- CLI 1.0 con `--help` y sub-comandos.
- OpenAPI spec versionado publicado.

### 5.3 v0.3 — Observabilidad, SLOs, Seguridad

**Objetivo:** Producción con monitoreo, acuerdos de nivel de servicio y hardening.

| Ítem | Acción |
|------|--------|
| **OpenTelemetry** — instrumentar FastAPI, simulaciones, LLM calls |
| **Prometheus metrics** — `/metrics` endpoint (latencia, throughput, error rate) |
| **Grafana dashboards** — SLOs para `/v1/simulate`, `/v1/llm/run_simulation` |
| **SLOs canónicos** |
| - Error budget: < 5% error rate (500/502) |
| - P95 latency: < 2s (simulaciones < 100 steps), < 30s (LLM) |
| - Disponibilidad: 99.9% |
| **Rate limiting distribuido** — migrar de `memory` a `redis` o `file` en multi-worker |
| **Security headers** — HSTS, X-Content-Type-Options, X-Frame-Options (nginx) |
| **Audit logging** — log de todos los requests con `request_id`, `client_ip`, endpoint, response code |
| **Secrets management** — integrar con Vault o AWS Secrets Manager |
| **Backup/restore** — snapshots de Factbook DB, historial de simulaciones |

**Criterio de "done" v0.3:**

- Dashboard de observabilidad en vivo.
- SLOs definidos y monitoreados en CI.
- Security audit completa (bandit, pip-audit).
- Disaster recovery plan documentado.

---

## 6. Decisiones de Arquitectura (ADRs)

### 6.1 ADR-001: Migración de `api.py` → `backend/app/main.py`

- **Status:** Aceptada
- **Contexto:** `api.py` en raíz es monolítico y no versionado bajo `/v1`. La convención `backend/app/` existe pero carece de `main.py`.
- **Decisión:** Crear `backend/app/main.py` como el entry-point FastAPI oficial. Migrar endpoints gradualmente manteniendo `api.py` como compat bridge durante v0.1-v0.2.
- **Consecuencia:** Docker Compose debe cambiar `uvicorn api:app` → `uvicorn backend.app.main:app` en v0.2.

### 6.2 ADR-002: Payloads de entrada como `dict` (no pydantic input DTOs)

- **Status:** Aceptada (status quo)
- **Contexto:** `AGENTS.md` establece que endpoints existentes usan `dict` + `_rate_limit` + `_public_error`.
- **Decisión:** Los endpoints `/v1/*` heredan este patrón. DTOs pydantic se usan solo para **salida**.
- **Consecuencia:** Menos boilerplate, pero menos validación client-side. Compensado con tests de integración.

### 6.3 ADR-003: Semillas no globales

- **Status:** Aceptada
- **Contexto:** CLAUDE.md §7 y AGENTS.md exigen reproducibilidad explícita.
- **Decisión:** Siempre usar `seed=` como argumento de función o en `config["seed"]`. Nunca leer `os.environ["SEED"]`.
- **Consecuencia:** CI usa `PYTHONHASHSEED=42` como complemento, no como mecanismo de reproducibility.

### 6.4 ADR-004: Frontend React (no Angular)

- **Status:** Aceptada
- **Contexto:** El spec menciona "Angular UI-NG" pero el repo `frontend/` usa React 18 + Vite + TS.
- **Decisión:** Seguir con React. Actualizar naming en specs futuros para decir "UI-NG (React)".
- **Consecuencia:** Ninguna. El frontend ya está scaffoldeado correctamente.

---

## 7. Políticas de Configuración y Despliegue

### 7.1 Principio de configuración

> **"Configuration vía env vars, defaults en YAML, overrides en memoria."**

- **`massive_core/config/defaults.yaml`** — defaults estáticos (CORS origins, rate limits).
- **`get_app_settings()`** — `lru_cache(4)`; cargado una vez y validado por pydantic.
- **Env vars** — toman precedencia sobre YAML. Prefijo `MASSIVE_`.
- **`MASSIVE_ENV`** — `development` desbloquea fallback `dev-secret-key`. En `production`, fail-closed.

### 7.2 Política de despliegue

| Entorno | Build | Auth | Rate Limit | CORS |
|---------|-------|------|------------|------|
| **development** | `pip install -e .` | `dev-secret-key` fallback | 60/min memory | localhost:1234,3000 |
| **staging** | `docker compose up -d` | API key real | 60/min file | `*.staging.massive.example.com` |
| **production** | Docker image tag | API key real | 60/min file | `massive.example.com` |

### 7.3 CI/CD (existente)

```yaml
# .github/workflows/
pytest.yml → core, scientific, api, full-suite jobs
docker-e2e.yml → build + smoke test en Docker
mkdocs.yml → deploy MkDocs a GitHub Pages
typecheck.yml → MyPy en CI
validate_ts_types.yml → regenerate TS types y fail si drift
```

### 7.4 Pruebas

| Tipo | Scope | Herramienta |
|------|-------|-------------|
| Unit | Simulador, engines, DTOs | `pytest tests/test_*.py` |
| Integration | Service layer + API endpoints | `pytest tests/test_services_layer.py`, `tests/test_api_security.py` |
| E2E | Docker compose + curl smoke tests | `docker-e2e.yml` |
| Contract | TS types sync | `validate_ts_types.yml` |
| Type-check | MyPy estricto | `mypy.ini` + `typecheck.yml` |

---

## 8. Criterios de "Production-Ready"

Un release de MASSIVE puede ser considerado **production-ready** cuando cumple:

### 8.1 Código

- [ ] Todos los endpoints `/v1/*` implementados en `backend/app/main.py` con tests de integración.
- [ ] Deprecación de endpoints `/api/*` completada con migración graceful.
- [ ] CLI oficial (`python -m massive.cli`) funciona y documentada.
- [ ] TypeScript types en `frontend/src/types/api.generated.ts` sincronizados con DTOs.
- [ ] MyPy pasa con `strict=True` en `backend/` y `massive_core/`.

### 8.2 Operacional

- [ ] SLOs definidos y monitoreados (error budget < 5%, P95 < 2s para simulaciones).
- [ ] Prometheus metrics + Grafana dashboard operativo.
- [ ] Healthcheck + readiness check probados en Docker.
- [ ] Rate limiting distribuido configurado (file backend funciona en multi-worker).
- [ ] Security audit pasada (bandit, pip-audit sin CRITICAL).

### 8.3 Documentación

- [ ] OpenAPI v1 spec generado y publicado.
- [ ] `docs/api.md` actualizado con ejemplos de todos los endpoints `/v1/*`.
- [ ] README.md incluye sección "Production Deployment" con ejemplos de env vars.
- [ ] MASSIVE-LLM contract documentado.

### 8.4 Packaging

- [ ] `.env.example` consolidado con todas las variables críticas.
- [ ] `requirements.txt` no duplica `pyproject.toml`.
- [ ] Docker image reproducible (`docker compose build` sin errores).
- [ ] Entry-points (`console_scripts`) declarados en `pyproject.toml`.

---

## 9. Glosario

| Término | Definición |
|---------|-----------|
| **UIL** | User Intent Language — layer de interpretación natural → config (ver `uil_adapter.py`) |
| **massive_core** | Adapter científico opt-in. Re-exporta legacy símbolos y añade contratos/científicos. |
| **micro_massive** | Motor de grupos pequeños (3-15 agentes). Personalidades Forer. |
| **CfC** | Closed-form Continuous-time dynamics. Motor de regla adaptativa. |
| **MASSIVE-LLM** | Contrato API para que agentes LLM invoquet simulaciones complejas vía un solo endpoint. |
| **Factbook** | CIA World Factbook. Fuente de datos demográficos reales (260+ países). |

---

## 10. Trazabilidad hacia el Código

| Concepto en este spec | Archivo(s) fuente |
|----------------------|-------------------|
| Endpoints `/api/*` | `api.py` |
| Endpoints `/api/v1/*` | `api.py` (líneas 226-383) |
| DTOs de salida | `backend/app/models/dto_*.py` |
| Service layer | `services/*.py` |
| Scientific runner | `massive_core/scientific_runner.py` |
| Config + logging | `massive_core/config/*.py` |
| Rate limiting | `massive_core/config/rate_limit.py` |
| Settings YAML | `massive_core/config/defaults.yaml` |
| CLI legacy | `simulator.py:run_with_schedule`, `benchmarks/runner.py` |
| Frontend API client | `frontend/src/services/api.ts` |
| TS type generator | `scripts/gen_ts_types.py` |

---

## 11. Próximos pasos inmediatos (acción Fase 1)

1. **Crear `backend/app/main.py`** — migrar endpoints de `api.py` a `/v1/*` manteniendo compatibilidad.
2. **Definir CLI entry-point** — `massive/cli.py` con `argparse` o `click` para `simulate`, `scientific`, `benchmark`, `llm`.
3. **Reforzar `.env.example`** — añadir variables de observabilidad, production flags, SLOs.
4. **Documentar MASSIVE-LLM draft contract** — spec minimal viable para v0.2.

---

*Documento generado por Arquitecto de Software — MASSIVE Master Orchestrator, Fase 1.*
*Última actualización: 2026-08-16T13:30Z.*
