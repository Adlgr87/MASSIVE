# MASSIVE — Observabilidad y Seguridad (Fase 5)

> **Ingeniero de Observabilidad / Seguridad** — Documento de fase 5 del Master Orchestrator.
>
> Este documento formaliza la arquitectura de observabilidad y seguridad para el
> backend UI-NG de MASSIVE (`backend/app/`). Está basado en el código real encontrado
> en el repositorio y describe el estado actual, brechas identificadas y
> recomendaciones de implementación para producción.

---

## 1. Resumen Ejecutivo

| Dimensión | Estado actual | Brecha crítica | Prioridad |
|-----------|---------------|----------------|-----------|
| **Health endpoint** | `/health` implementado en `main.py` | Sin readiness vs liveness distinción | Media |
| **Metrics endpoint** | `/metrics` implementado (Prometheus text) | Solo contadores; sin histogramas de latencia | Alta |
| **Logging estructurado** | Formato plano (`logging.basicConfig`) | Sin contexto (request_id, engine_type, etc.) | Alta |
| **API Auth** | `MASSIVE_API_KEYS` (X-API-Key) + dev fallback | Dev fallback en `api.py` | Alta |
| **CORS** | Configurable, no wildcard con credenciales | Validado en tests | Baja |
| **Rate limiting** | Sliding-window per-IP in-process | Sin multi-worker (necesita Redis) | Media |
| **Seguridad de credenciales** | `.env` + docker mounts | Sin vault/secret manager | Media |
| **SLOs / Alertas** | No definidos | Sin SLI/SLO/alertas | Alta |
| **Auditoría** | No implementada | Sin registro de cambios de config | Media |

---

## 2. Endpoints de Salud y Métricas

### 2.1 `/health` — Endpoint de estado

**Archivo:** `backend/app/main.py` (líneas 153–162)

**Implementación actual:**

```python
@app.get("/health")
def health_check() -> dict:
    """Liveness + light readiness probe (used by Docker HEALTHCHECK)."""
    store: RunStore = app.state.run_store
    try:
        store.count()
        store_ok = True
    except Exception:
        store_ok = False
    return {
        "status": "healthy" if store_ok else "degraded",
        "service": "MASSIVE UI-NG API",
        "version": "2.0.0",
        "env": settings.env,
        "store": "ok" if store_ok else "error",
    }
```

**Características:**
- Verifica conectividad del store de runs (SQLite).
- Devuelve `status: "degraded"` si el store falla.
- Usado por Docker `HEALTHCHECK` (Dockerfile.ui-ng línea 35, docker-compose.yml línea 26).

**Recomendación de producción — Separar liveness y readiness:**

| Probe | Endpoint | Propósito |
|-------|----------|-----------|
| **Liveness** (`/health`) | Si el proceso está respondiendo | Orquestador reinicia si falla |
| **Readiness** (`/ready`) | Si está listo para tráfico | Load balancer quita del pool si falla |

**Recomendación de implementación:**

```python
@app.get("/ready")
def readiness_check() -> dict:
    """Full readiness: DB, LLM provider, run store."""
    checks = {}
    # 1. Store
    store_ok = True
    try:
        app.state.run_store.count()
    except Exception:
        store_ok = False
    checks["store"] = store_ok
    # 2. LLM provider (soft check — warn, not fail, in heuristic mode)
    llm = resolve_provider()
    checks["llm_configured"] = llm["configured"]
    # 3. DB writable (production)
    if app.state.settings.db_path:
        checks["db_writable"] = app.state.settings.db_path.parent.exists()
    all_ok = all(checks.values())
    return {
        "status": "ready" if all_ok else "not_ready",
        "checks": checks,
        "service": "MASSIVE UI-NG API",
        "version": "2.0.0",
    }
```

### 2.2 `/metrics` — Endpoint Prometheus

**Archivo:** `backend/app/main.py` (líneas 144–151)
**Registry:** `backend/app/metrics.py`

**Implementación actual:**
- Registry personalizado con threadsafe counters.
- Métrica actual: `http_requests_total` (labels: `method`, `group`).
- Exponierto en formato texto Prometheus v0.0.4.

**Counters existentes:**

| Métrica | Labels | Quién lo incrementa |
|---------|--------|---------------------|
| `http_requests_total` | `method`, `group` | middleware `http_counter` en `main.py` |
| `simulations_total` | `engine` | `simulation.py:_execute()` |
| `ws_connections_total` | *(none)* | `live.py:ws_live()` |
| `ws_snapshots_total` | *(none)* | `live.py:ws_live()` |
| `ws_shocks_total` | *(none)* | `live.py:ws_live()` |
| `ws_stops_total` | *(none)* | `live.py:ws_live()` |
| `rate_limit_hits_total` | `group` | `rate_limit.py:RateLimitMiddleware` |
| `llm_requests_total` | `provider`, `outcome` | `llm_chat.py:chat_completion()` |

**Brechas críticas para SLOs:**

1. **No hay histogramas de latencia** — `http_request_duration_seconds` es esencial para SLO de p95.
2. **No hay gauges** — `ws_active_connections`, `run_store_count`, `llm_queue_depth` no existen.
3. **El counter `http_requests_total` no distingue códigos de respuesta** — para error rate SLO se necesita `http_responses_total` con label `status_code`.

**Propuesta de métricas adicionales:**

```python
# En metrics.py, extender MetricsRegistry con:
# - Histogramo de latencia (por endpoint group)
# - Counter de respuestas por código de estado
# - Gauge de conexiones WebSocket activas
# - Gauge de tamaño del run store
# - Histogramo de duración de simulación (segundos, por engine)
# - Gauge de latencia LLM (por provider, en segundos)
```

**Propuesta de nuevo registry:**

| Métrica | Tipo | Labels | Uso SLO |
|---------|------|--------|---------|
| `http_request_duration_seconds` | Histogramo | `method`, `group`, `status_code` | Latencia p95 |
| `http_responses_total` | Counter | `method`, `group`, `status_code` | Error rate |
| `simulation_duration_seconds` | Histogramo | `engine` | Latencia de simulación |
| `llm_request_duration_seconds` | Histogramo | `provider`, `outcome` | Latencia LLM |
| `ws_active_connections` | Gauge | *(none)* | Estado WebSocket |
| `run_store_count` | Gauge | *(none)* | Volumen de runs |

**Configuración de scrape de Prometheus:**

```yaml
# prometheus.yml — scrape config
scrape_configs:
  - job_name: "massive-ui-ng"
    static_configs:
      - targets: ["massive-ui-ng:8000"]
    metrics_path: /metrics
    scrape_interval: 15s
```

### 2.3 Endpoints de salud en Docker

**Dockerfile.ui-ng (línea 35):**
```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s     CMD curl -sf http://127.0.0.1:8000/health || exit 1
```

**docker-compose.yml (línea 26):**
```yaml
healthcheck:
  test: ["CMD", "curl", "-sf", "http://127.0.0.1:8000/health"]
```

**Observación:** `Dockerfile.optimized` (raíz) usa `/docs` como healthcheck, lo cual es inconsistente y incorrecto. Debe usar `/health`.

---

## 3. Logs Estructurados

### 3.1 Estado actual

**Archivo:** `backend/app/main.py` (líneas 39–44)

```python
logging.basicConfig(
    level=os.getenv("MASSIVE_LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(name)-28s | %(levelname)-8s | %(message)s",
)
```

- Formato plano, sin estructura JSON.
- No hay `request_id`, `simulation_id`, `engine_type`, `country_code`, `llm_provider`, `user_id`.
- El logger `massive_core/config/logging_setup.py` (`configure_logging`) existe pero **no se usa en `main.py`** del UI-NG backend. El backend UI-NG inicializa logging de forma independiente.

### 3.2 Campos de contexto requeridos (Phase 5)

El Master Orchestrator especifica estos campos en el registro de logs:

| Campo | Origen | Cuándo se propaga |
|-------|--------|-------------------|
| `request_id` | UUID generado por middleware | Cada request HTTP / WebSocket |
| `simulation_id` | UUID generado al iniciar simulación | `/api/simulate`, `/ws/live` |
| `engine_type` | `req.engine` (scalar\|energy\|multilayer\|massive) | `/api/simulate`, `/ws/live` |
| `country_code` | Detectado de `config.factbook_country` | `/api/conversation`, `/api/simulate` |
| `llm_provider` | `resolve_provider()["provider"]` | Cada llamada LLM |
| `user_id` | Derivado de API key (o "anonymous") | Cada request autenticado |

### 3.3 Diseño de logging estructurado

**Recomendación de implementación:**

#### 3.3.1. Middleware de request_id

```python
# backend/app/logging_middleware.py (nuevo archivo)
import uuid
import logging
from starlette.types import ASGIApp

class RequestIDMiddleware:
    """Inyecta request_id en el contexto logging."""
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            headers = scope.get("headers", [])
            rid = None
            for k, v in headers:
                if k == b"x-request-id":
                    rid = v.decode()
                    break
            if not rid:
                rid = uuid.uuid4().hex[:12]
            scope["state"].request_id = rid
        await self.app(scope, receive, send)
```

#### 3.3.2. Logger estructurado JSON

```python
# backend/app/logging_config.py (nuevo)
import json, logging, sys
from datetime import datetime, timezone

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "simulation_id", "engine_type",
                     "country_code", "llm_provider", "user_id"):
            val = getattr(record, key, None)
            if val:
                log_entry[key] = val
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)

def configure_json_logging(level="INFO"):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
```

#### 3.3.3. Logger contextual con `extra`

```python
# En cada router:
import logging

log = logging.getLogger("massive.ui_ng.simulation")

# En simulation.py:
log.info("simulation_started", extra={
    "simulation_id": sim_id,
    "engine_type": req.engine,
    "country_code": req.config.get("factbook_country", "N/A"),
    "user_id": api_key_hash,
})

# En llm_chat.py:
log.info("llm_request", extra={
    "llm_provider": cfg["provider"],
    "model": cfg["model"],
    "outcome": "ok" if text else "error",
})
```

#### 3.3.4. Formato JSON esperado

```json
{
  "timestamp": "2025-06-15T14:30:00.123Z",
  "level": "INFO",
  "logger": "massive.ui_ng.simulation",
  "message": "simulation_started",
  "request_id": "a1b2c3d4e5",
  "simulation_id": "sim_f4a3b2c1",
  "engine_type": "multilayer",
  "country_code": "MX",
  "user_id": "apikey_7f3a",
  "llm_provider": "groq"
}
```

### 3.4 Variables de entorno de logging

**Nuevas variables en `.env.example`:**

| Variable | Default | Descripción |
|----------|---------|-------------|
| `MASSIVE_LOG_LEVEL` | `INFO` | Nivel de logging (DEBUG/INFO/WARNING/ERROR) |
| `MASSIVE_LOG_FORMAT` | `text` | `json` para producción, `text` para dev |
| `MASSIVE_LOG_FILE` | *(unset)* | Archivo log rotativo (opcional) |

---

## 4. Seguridad

### 4.1 Autenticación (API Keys)

**Archivo:** `backend/app/security.py`

**Implementación actual:**
- Headers: `X-API-Key`
- Soporte multi-key: `MASSIVE_API_KEYS` (comma-separated)
- Validación constante (`hmac.compare_digest`)
- **Modo dev abierto**: Si no hay keys configuradas, el API corre en "open dev mode" (con warning).

**Problema en `api.py` (raíz):**
```python
# api.py líneas 17-27 — INSEGURO
valid_key = os.getenv("MASSIVE_API_KEY")
if not valid_key:
    valid_key = "default-secret-key"  # fallback inseguro
    log.warning("MASSIVE_API_KEY not set — using insecure default")
if api_key != valid_key:
    raise HTTPException(status_code=401, detail="Invalid API Key")
```

**Hallazgo:** `api.py` (servicio UIL monolítico raíz) NO usa `security.py`. Usa su propia validación con `!=` (no constant-time) y un fallback "default-secret-key". Esto es una **brecha de seguridad crítica** si `api.py` se expone públicamente.

**Recomendación:**
- Unificar en `security.py` — eliminar el fallback inseguro de `api.py`.
- En producción, requerir `MASSIVE_API_KEYS` siempre.
- Considerar migración a tokens JWT con expiración para usuarios individuales (`user_id`).

### 4.2 CORS

**Archivo:** `backend/app/settings.py` (líneas 63–69)

```python
cors_origins: list[str] = field(
    default_factory=lambda: [
        o.strip()
        for o in os.getenv(
            "MASSIVE_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
        ).split(",") if o.strip()
    ]
)
```

**Configuración en `main.py`:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Estado:** Correcto — no usa `"*"` con `allow_credentials=True`.

**Test de seguridad:** `tests/test_api_security.py` verifica que `"*"` no esté en origins.

**Recomendación:**
- En producción, `MASSIVE_CORS_ORIGINS=https://massive.example.com`
- Nunca usar `allow_origins=["*"]` con `allow_credentials=True`.

### 4.3 Rate Limiting

**Archivo:** `backend/app/rate_limit.py`

**Implementación actual:**
- Sliding window por IP (cliente).
- Dos límites:
  - General: `MASSIVE_RATE_LIMIT_PER_MIN` (default 120)
  - Simulación: `MASSIVE_RATE_LIMIT_SIMULATE_PER_MIN` (default 12) — endpoints `/api/simulate*`
- Client IP: respeta `X-Forwarded-For` solo si `MASSIVE_TRUST_PROXY=1`.
- **Almacenamiento in-process** — no funciona con múltiples workers.

**Código relevante (rate_limit.py: líneas 107–110):**
```python
def _client_ip(request: Request, trust_proxy: bool) -> str:
    if trust_proxy:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
```

**También existe** `massive_core/config/rate_limit.py`:
- `InMemoryRateLimiter` — para single worker.
- `FileRateLimiter` — para multi-worker (JSON con fcntl advisory lock).
- `build_rate_limiter(backend="memory"|"file", path=...)`.

**Brecha:** `backend/app/rate_limit.py` (UI-NG) no usa el rate limiter de `massive_core`. Dos implementaciones divergentes.

**Recomendación:**
- Unificar en `massive_core/config/rate_limit.py`.
- Para producción multi-worker: usar Redis (`RedisRateLimiter`).
- Documentar que el rate limiter in-process funciona para single-worker (como el Dockerfile.ui-ng que usa `--workers 1`).

### 4.4 TrustedHost & Security Headers

**Implementación en `main.py`:**

```python
# TrustedHost (opcional)
if settings.allowed_hosts and settings.allowed_hosts != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

# Security headers (middleware http)
@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    return response
```

**Estado:** Implementado correctamente.

### 4.5 Gestión de Credenciales

**Proveedores LLM (credenciales via env):**

| Variable | Proveedor | Estado en `.env.example` |
|----------|-----------|--------------------------|
| `GROQ_API_KEY` | Groq | Presente |
| `OPENAI_API_KEY` | OpenAI | Presente |
| `OPENROUTER_API_KEY` | OpenRouter | Presente |
| `OLLAMA_HOST` | Ollama (local) | Presente |
| `PROVIDER` | Selección default | Agregada en esta actualización |
| `HF_TOKEN` | HuggingFace Spaces | Mencionado en docs, no en .env.example |

**Docker mounts (read-only):**
- `.env` y `.env.local` montados como `:ro` en `docker-compose.yml` (línea 19–20).

**Recomendación:**
- **Nunca** commitear `.env` real. Usar secret manager en producción.
- Rotar API keys regularmente.
- `HF_TOKEN` solo necesario en deploy a HuggingFace Spaces.

### 4.6 Seguridad de uploads

**Archivo:** `api.py` (líneas 37–45)

```python
_MAX_UPLOAD_BYTES = int(os.getenv("MASSIVE_MAX_UPLOAD_MB", "10")) * 1024 * 1024
_ALLOWED_EXT = {".pdf", ".json", ".csv", ".xlsx", ".txt", ".md"}

def _safe_suffix(filename: str | None) -> str:
    ext = "." + filename.rsplit(".", 1)[-1].lower()
    if ext not in _ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
    return ext
```

**Estado:** Implementado. Límite de 10 MB, whitelist de extensiones.

### 4.7 Manejo de errores

**Archivo:** `api.py` (líneas 75–77)

```python
def _public_error(exc: Exception) -> HTTPException:
    """Never leak stack traces / internal paths to clients."""
    log.exception("API error: %s", exc)
    return HTTPException(status_code=500, detail="Internal server error")
```

**Estado:** Implementado — no filtra stack traces al cliente.

---

## 5. SLOs, SLIs y Alertas

### 5.1 SLI / SLO propuestos

| SLO | Métrica Prometheus | Ventana | Threshold |
|-----|-------------------|---------|-----------|
| **SL1 — Latencia API p95** | `histogram_quantile(0.95, http_request_duration_seconds_bucket)` | 30d | p95 <= 2000ms (simulaciones), <= 500ms (conversación) |
| **SL2 — Tasa de errores 5xx** | `rate(http_responses_total{status_code=~"5.."}[5m])` | 30d | < 1% |
| **SL3 — Disponibilidad** | `up{job="massive-ui-ng"}` | 30d | >= 99.5% |
| **SL4 — Latencia LLM p95** | `histogram_quantile(0.95, llm_request_duration_seconds_bucket{provider!="ollama"})` | 30d | p95 <= 5000ms |
| **SL5 — Rate limit hits** | `rate(rate_limit_hits_total[5m])` | 1h | < 0.5% de requests |

### 5.2 Definiciones formales

#### SL1 — Latencia p95 de API
- **SLI:** `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))`
- **SLO:** 95% de requests HTTP completados en <= 2000ms (simulaciones) y <= 500ms (conversación, health, status).
- **Ventana de error:** 30 dias.
- **Error budget:** 5% de requests pueden exceder el threshold.

#### SL2 — Tasa de errores 5xx
- **SLI:** `sum(rate(http_responses_total{status_code=~"5.."}[5m])) / sum(rate(http_responses_total[5m]))`
- **SLO:** < 1% de respuestas 5xx.
- **Ventana:** 30 dias.

#### SL3 — Disponibilidad
- **SLI:** `avg_over_time(up{job="massive-ui-ng"}[5m])`
- **SLO:** >= 99.5% en 30 dias.
- **MTTR implicito:** < 10 minutos (Docker restart: unless-stopped).

#### SL4 — Latencia LLM
- **SLI:** `histogram_quantile(0.95, sum(rate(llm_request_duration_seconds_bucket{provider!="ollama"}[5m])) by (le))`
- **SLO:** p95 <= 5000ms para proveedores cloud (Groq/OpenAI/OpenRouter).
- **Ventana:** 30 dias.

#### SL5 — Tasa de rate limiting
- **SLI:** `rate(rate_limit_hits_total[5m])`
- **SLO:** < 0.5% de requests totales retornan 429.

### 5.3 PromQL recording rules

```yaml
# prometheus/rules/massive_slo.yml
groups:
  - name: massive.slo
    rules:
      # --- SLIs ---
      - record: massive:api_latency_p95_5m
        expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

      - record: massive:error_rate_5m
        expr: sum(rate(http_responses_total{status_code=~"5.."}[5m])) / sum(rate(http_responses_total[5m]))

      - record: massive:availability_5m
        expr: avg_over_time(up{job="massive-ui-ng"}[5m])

      - record: massive:llm_latency_p95_5m
        expr: histogram_quantile(0.95, sum(rate(llm_request_duration_seconds_bucket{provider!="ollama"}[5m])) by (le))

      - record: massive:rate_limit_rate_5m
        expr: rate(rate_limit_hits_total[5m])

      # --- SLO Error Budgets (30d window) ---
      - record: massive:slo_api_latency_burn_rate
        expr: |
          1 - (
            count(http_request_duration_seconds_bucket{le="2.0",job="massive-ui-ng"}) > 0
          ) / count(time() - timestamp(http_request_duration_seconds_bucket))

      - record: massive:slo_error_budget_remaining
        expr: 1 - sum(increase(http_responses_total{status_code=~"5.."}[30d])) / 0.01
```

### 5.4 Alertas (PrometheusRule)

```yaml
# alertmanager/rules/massive_alerts.yml
groups:
  - name: massive.critical
    rules:
      # --- Disponibilidad ---
      - alert: MassiveDown
        expr: up{job="massive-ui-ng"} == 0
        for: 2m
        labels:
          severity: critical
          team: devops
        annotations:
          summary: "MASSIVE UI-NG service is down"
          description: "The massive-ui-ng target has been down for more than 2 minutes."

      # --- Latencia API ---
      - alert: APIHighLatencyP95
        expr: massive:api_latency_p95_5m > 2.0
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "API p95 latency above 2000ms (5m avg)"
          description: "API latency is degrading. Check simulation load."

      - alert: APICriticalLatency
        expr: massive:api_latency_p95_5m > 5.0
        for: 2m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "API p95 latency above 5000ms"
          description: "Severe latency degradation. Immediate investigation required."

      # --- Tasa de errores ---
      - alert: HighErrorRate
        expr: massive:error_rate_5m > 0.01
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "Error rate > 1% (5m avg)"

      - alert: CriticalErrorRate
        expr: massive:error_rate_5m > 0.05
        for: 2m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "Error rate > 5% - site reliability issue"

      # --- Rate limiting ---
      - alert: HighRateLimitHits
        expr: massive:rate_limit_rate_5m > 0.005
        for: 10m
        labels:
          severity: warning
          team: devops
        annotations:
          summary: "Rate limit rejects > 0.5% of requests"
          description: "Potential abuse or legitimate load exceeded limits."

      # --- LLM provider ---
      - alert: LLMRequestErrors
        expr: sum(rate(llm_requests_total{outcome="error"}[5m])) > 0.1
        for: 2m
        labels:
          severity: warning
          team: ml
        annotations:
          summary: "LLM provider returning errors"
          description: "LLM provider {{ $labels.provider }} has a high error rate. Fallback mode active."

      # --- Run store ---
      - alert: RunStoreError
        expr: count(up{job="massive-ui-ng"} == 1) > 0
          and on() (massive:run_store_healthy == 0)
        for: 1m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "Run store (SQLite) is unhealthy"
          description: "Cannot read/write run history. Simulations may fail persistence."
```

### 5.5 Dashboard propuesto (Grafana)

#### Dashboard: "MASSIVE UI-NG - Overview"

**Paneles:**
1. **Service status** — `up{job="massive-ui-ng"}` (singlestat)
2. **API p95 latency (5m)** — `massive:api_latency_p95_5m` (gauge, threshold 2s)
3. **Error rate (5m)** — `massive:error_rate_5m * 100` (gauge, threshold 1%)
4. **Availability (30d)** — `massive:availability_5m * 100` (gauge, threshold 99.5%)
5. **Requests/sec by group** — `sum by(group) (rate(http_requests_total[5m]))` (bar chart)
6. **Response codes** — `sum by(status_code) (rate(http_responses_total[5m]))` (graph)
7. **Simulations run (5m)** — `rate(simulations_total[5m])` (graph, by engine)
8. **LLM request latency p95** — `massive:llm_latency_p95_5m` (gauge)
9. **LLM errors by provider** — `sum by(provider) (rate(llm_requests_total{outcome="error"}[5m]))` (bar)
10. **WebSocket connections** — `ws_active_connections` (gauge)
11. **Rate limit hits** — `massive:rate_limit_rate_5m` (graph)
12. **Run store count** — `run_store_count` (gauge)

---

## 6. Auditoría de Configuración

### 6.1 Necesidad

El Master Orchestrator (Fase 5.3) requiere:
> Implementar auditoría de cambios de configuración (quién, cuándo, qué parámetros se modifican).

### 6.2 Diseño propuesto

| Evento | Campos | Destino |
|--------|--------|---------|
| `config_change` | `user_id`, `request_id`, `timestamp`, `param_name`, `old_value`, `new_value`, `reason` | Log estructurado (JSON en tabla `audit_logs`) |
| `simulation_start` | `simulation_id`, `user_id`, `engine_type`, `country_code`, `llm_provider`, `config_hash` | Metrics + logs |
| `simulation_complete` | `simulation_id`, `duration_seconds`, `engine_type`, `outcome` | Metrics + logs |
| `llm_call` | `llm_provider`, `model`, `duration_seconds`, `outcome`, `tokens_requested`, `tokens_used` | Metrics + logs |

### 6.3 Almacenamiento

```python
# Modelo de auditoría (para futura implementación)
class AuditLog(BaseModel):
    event_id: str           # UUID
    timestamp: datetime     # UTC
    user_id: str            # API key hash or "anonymous"
    event_type: str         # config_change, simulation_start, etc.
    resource: str           # entity affected
    action: str             # created, updated, deleted
    details: dict           # old/new values, parameters
    request_id: str         # correlation
    ip_address: str         # client IP
```

**Recomendación de almacenamiento:** SQLite (`audit_logs` table) para dev/simple, o Kafka/ClickHouse para producción.

---

## 7. Variables de Entorno — Mapa Completo

### 7.1 Mapa de variables de observabilidad y seguridad

| Variable | Componente | Default | Descripción |
|----------|-----------|---------|-------------|
| `MASSIVE_API_KEYS` | UI-NG `security.py` | *(vacío -> dev mode)* | Keys API (comma-separated, constant-time compare) |
| `MASSIVE_API_KEY` | `api.py` (legacy UIL) | `default-secret-key` | Single key legacy (INSEGURO - deprecar) |
| `MASSIVE_CORS_ORIGINS` | UI-NG `settings.py` | `localhost:5173,3000` | Orígenes CORS permitidos |
| `MASSIVE_ALLOWED_HOSTS` | UI-NG `settings.py` | `*` | Hosts confiables (TrustedHost) |
| `MASSIVE_TRUST_PROXY` | UI-NG `settings.py` | `false` | Confiar en `X-Forwarded-For` |
| `MASSIVE_RATE_LIMIT_ENABLED` | UI-NG `settings.py` | `true` | Toggle rate limiter |
| `MASSIVE_RATE_LIMIT_PER_MIN` | UI-NG `settings.py` | `120` | Límite general por IP/min |
| `MASSIVE_RATE_LIMIT_SIMULATE_PER_MIN` | UI-NG `settings.py` | `12` | Límite para `/api/simulate*` |
| `MASSIVE_RATE_LIMIT_BACKEND` | `api.py`, `massive_core` | `memory` | `memory` o `file` (multi-worker) |
| `MASSIVE_RATE_LIMIT_PATH` | `massive_core/config/rate_limit.py` | `/tmp/massive_rate_limit.json` | Path file backend |
| `MASSIVE_LOG_LEVEL` | UI-NG `main.py` | `INFO` | Nivel de logging |
| `MASSIVE_LOG_FORMAT` | UI-NG (propuesto) | `text` | `json` o `text` |
| `MASSIVE_LOG_FILE` | `logging_setup.py` | *(unset)* | Archivo log rotativo |
| `MASSIVE_ENV` | UI-NG `settings.py` | `development` | `development`/`staging`/`production` |
| `MASSIVE_MAX_UPLOAD_MB` | `api.py` | `10` | Tamaño máximo upload |
| `MASSIVE_ANALYTICS_SNIPPET` | (legacy) | *(empty)* | Snippet analytics (deprecado) |
| `PROVIDER` | `llm_chat.py`, `interpreter_layer.py` | `groq` | Proveedor LLM default |
| `GROQ_API_KEY` | `llm_chat.py` | *(requerido)* | API key Groq |
| `OPENAI_API_KEY` | `llm_chat.py` | *(requerido)* | API key OpenAI |
| `OPENROUTER_API_KEY` | `llm_chat.py` | *(requerido)* | API key OpenRouter |
| `OLLAMA_HOST` | `llm_chat.py` | `http://localhost:11434` | Host Ollama local |
| `OLLAMA_MODEL` | `llm_chat.py` | `llama3.2` | Modelo Ollama |
| `MASSIVE_LLM_MODEL` | `llm_chat.py` | *(auto)* | Override modelo LLM |
| `MASSIVE_LLM_TIMEOUT` | UI-NG `settings.py` | `45.0` | Timeout LLM (segundos) |
| `MASSIVE_LLM_MAX_TOKENS` | UI-NG `settings.py` | `1400` | Máx tokens generación |
| `MASSIVE_DATA_DIR` | UI-NG `settings.py` | `data/ui_ng/` | Directorio datos (SQLite) |
| `MASSIVE_SERVE_FRONTEND` | UI-NG `settings.py` | `true` | Servir frontend Angular/Vite |
| `MASSIVE_RUN_STORE_CAPACITY` | UI-NG `settings.py` | `500` | Capacidad LRU runs en memoria |

### 7.2 Herencia y migración de config

**Problema detectado:** Existen **dos** configuraciones de settings paralelas:

1. **`backend/app/settings.py`** — `UISettings` — usado por UI-NG backend (`main.py`)
2. **`massive_core/config/settings.py`** — `AppSettings` — usado por `api.py` (legacy) y `logging_setup.py`

Esto crea ambigüedad sobre qué configuración es "canonical". El `API_KEY_HEADER` y `CORS` se duplican.

**Recomendación:** Consolidar en `UISettings` (UI-NG es la API principal) y deprecar `api.py` o migrarlo a usar `UISettings`.

---

## 8. Checklist de Implementación Phase 5

### 8.1 Prioridad Alta (bloqueadores)

- [ ] **Unificar autenticación**: Eliminar fallback `default-secret-key` en `api.py`. Usar `security.py` como única fuente.
- [ ] **Migrar a logging estructurado JSON**: Implementar `MASSIVE_LOG_FORMAT=json` con middleware `request_id`.
- [ ] **Añadir histogramas de latencia** a `metrics.py`: `http_request_duration_seconds`, `llm_request_duration_seconds`.
- [ ] **Añadir counter de respuestas por código**: `http_responses_total{status_code=...}`.
- [ ] **Documentar SLOs formales** con recording rules y alertas (sección 5).

### 8.2 Prioridad Media

- [ ] **Separar health/readiness**: Añadir `/ready` con chequeos completos (DB, LLM configurado, store).
- [ ] **Unificar rate limiting**: Migrar `backend/app/rate_limit.py` a `massive_core/config/rate_limit.py`.
- [ ] **Implementar auditoría**: Tabla `audit_logs` + middleware de logging de cambios config.
- [ ] **Consistencia de healthcheck en Dockerfiles**: Usar `/health` en todos los Dockerfiles.
- [ ] **Añadir gauges**: `ws_active_connections`, `run_store_count`.
- [ ] **Tracer de tracing distribuido**: Añadir `traceparent` header support (OpenTelemetry).

### 8.3 Prioridad Baja

- [ ] **Multi-worker rate limiting**: Implementar `RedisRateLimiter` para scale horizontal.
- [ ] **Secret manager integration**: AWS Secrets Manager / GCP Secret Manager para prod.
- [ ] **JWT auth**: Migrar de API keys a JWTs para `user_id` real.
- [ ] **Metrics summary en `/health`**: Incluir contadores clave en health response.

---

## 9. Arquitectura de Seguridad

### 9.1 Matriz de amenazas (parcial)

| Activo | Amenaza | Mitigación actual | Gap |
|--------|---------|-------------------|-----|
| API keys | Filtrado en logs | `security.py` no loguea keys | `api.py` podría loguear |
| Uploads | Path traversal | `_safe_suffix` valida extensiones | No valida el nombre del file completo |
| Rate limits | Spoof X-Forwarded-For | `MASSIVE_TRUST_PROXY` controla | Si trust_proxy=1 + spoofed, bypass |
| CORS | Origen malicioso | Whitelist estricta | Si config default, dev localhost |
| LLM keys | Filtrado en código | Env vars via `.env` | `api.py` expone en `get_adapter()` |
| Run store | Acceso no autorizado | API key required en routers | Sin user_id, no ownership de runs |

### 9.2 Defensa en profundidad

```
Internet -> [Ingress/TLS] -> [WAF]
    |
[Load Balancer (sticky session para rate-limit in-process)]
    |
[Docker: MASSIVE_API_KEYS + CORS restrictivo + TrustedHost]
    |
[FastAPI: RateLimitMiddleware + APIKey auth + SecurityHeaders]
    |
[SQLite runs.db: per-run, no PII]
```

### 9.3 Hardening recomendado para producción

1. **Forzar TLS** al nivel del ingress (nginx/ALB).
2. **Restricted TrustedHost**: `MASSIVE_ALLOWED_HOSTS=massive.example.com`.
3. **Multi-key API**: `MASSIVE_API_KEYS=key1,key2` con rotación.
4. **Rate limiting externo**: WAF/Nginx limita antes de llegar a la app.
5. **Log level producción**: `MASSIVE_LOG_LEVEL=WARNING` para reducir volumen, `INFO` para debugging temporal.
6. **SQLite WAL mode**: ya implementado en `run_store.py` (`PRAGMA journal_mode=WAL`).
7. **Security scan en CI**: `bandit`, `semgrep` en pipeline.

---

## 10. Implementación por Fases

### Fase 5.1 — Health check (30 min)
- Mejorar `/health` con más checks.
- Añadir `/ready` endpoint.

### Fase 5.2 — Logging estructurado (2h)
- Añadir `RequestIDMiddleware` a `main.py`.
- Configurar JSON formatter condicional (`MASSIVE_LOG_FORMAT`).
- Propagar `extra` en loggers de routers críticos.

### Fase 5.3 — Metrics SLO (2h)
- Extender `metrics.py` con histogramas y gauges.
- Añadir middleware de duración HTTP.
- Añadir duration histogram a `llm_chat.py`.

### Fase 5.4 — SLOs y alertas (1h doc + deploy)
- Definir recording rules (PromQL).
- Configurar alertrules.
- Dashboard Grafana.

### Fase 5.5 — Auditoría (3h)
- Middleware de auditoría para config changes.
- Tabla `audit_logs` en SQLite.

---

## 11. Referencias rápidas (código existente)

| Concepto | Archivo | Líneas |
|----------|---------|--------|
| Health endpoint | `backend/app/main.py` | 153-162 |
| Metrics endpoint | `backend/app/main.py` | 144-151 + `metrics.py` |
| API key auth | `backend/app/security.py` | 24-45 |
| Rate limiting | `backend/app/rate_limit.py` | 107-138 |
| Security headers | `backend/app/main.py` | 47-55 |
| CORS | `backend/app/main.py` | 117-124 |
| TrustedHost | `backend/app/main.py` | 106-107 |
| Settings | `backend/app/settings.py` | 1-92 |
| LLM provider resolution | `backend/app/llm_chat.py` | 42-66 |
| Docker healthcheck | `massive-ui-ng/infra/Dockerfile.ui-ng` | 35-36 |

---

*Documento generado por el Ingeniero de Observabilidad / Seguridad — Fase 5 del Master Orchestrator.*
