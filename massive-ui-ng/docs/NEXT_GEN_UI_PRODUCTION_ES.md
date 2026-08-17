# MASSIVE UI-NG — Guía de Producción

> **Estado:** v1 production-ready · **Fecha:** 2026-08-14
> Complemento de `NEXT_GEN_UI_WORKFLOW_ES.md` (diseño) y
> `frontend/README_ES.md` (desarrollo). Aquí: despliegue, seguridad,
> operación y observabilidad.

---

## 1. Arquitectura en producción

Un **único servicio** sirve la API y el frontend compilado:

```
                 ┌─────────────────────────────────────────────┐
  navegador ───▶ │  MASSIVE UI-NG (uvicorn, puerto 8000)       │
   https://…     │  ├─ FastAPI /api/*                          │
                 │  │   ├─ rate limit (sliding window por IP)  │
                 │  │   ├─ auth X-API-Key (multi-key, hmac)    │
                 │  │   ├─ SSE: /conversation/stream,          │
                 │  │   │        /simulate/stream              │
                 │  │   └─ persistencia SQLite (WAL)           │
                 │  └─ StaticFiles / ← frontend/dist (React)   │
                 └──────────────┬──────────────────────────────┘
                                ▼
                 MASSIVE core (simulator, massive_core, motores,
                 Factbook, CfC) + LLM provider (Groq/OpenAI/…)
```

En desarrollo, Vite (5173) proxya `/api` al backend. En producción no hay
proxy: el backend sirve `frontend/dist` (build con `npm run build`).

---

## 2. Despliegue

### 2.1 Docker (recomendado)

```bash
# Build
docker build -f Dockerfile.ui-ng -t massive-ui-ng .

# Run
docker run -d -p 8000:8000 \
  -e PROVIDER=groq -e GROQ_API_KEY=gsk_... \
  -e MASSIVE_API_KEYS=$(openssl rand -hex 24) \
  -e MASSIVE_ALLOWED_HOSTS=tu-dominio.com \
  -e MASSIVE_TRUST_PROXY=1 \
  -v massive-data:/data \
  massive-ui-ng

# o con docker compose (servicio ui-ng, puerto 8010)
docker compose up -d --build ui-ng
```

### 2.2 Sin Docker

```bash
pip install -r requirements.txt
cd frontend && npm ci && npm run build && cd ..
MASSIVE_SERVE_FRONTEND=1 uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### 2.3 Detrás de un reverse proxy (Nginx/Caddy/Traefik)

- Pasar `X-Forwarded-For` (clave para el rate limit por IP real).
- Activar `MASSIVE_TRUST_PROXY=1` **solo** cuando el proxy filtre cabeceras
  falsas. Sin él, un atacante podría rotar IPs con cabeceras falsificadas.
- Configurar `MASSIVE_ALLOWED_HOSTS` con el dominio real (rechaza Hosts
  desconocidos).
- Ejemplo nginx:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_buffering off;          # SSE
    proxy_read_timeout 300s;      # simulaciones largas
}
```

---

## 3. Seguridad

| Control | Configuración | Comportamiento |
|---|---|---|
| **API key** | `MASSIVE_API_KEYS` (coma-separada, o `MASSIVE_API_KEY`) | Requiere cabecera `X-API-Key` en `/api/conversation*` y `/api/simulate*`/`/api/runs*`. Comparación en tiempo constante (`hmac.compare_digest`). Sin claves → modo dev abierto con warning en log. |
| **Rate limit** | `MASSIVE_RATE_LIMIT_PER_MIN` (120) y `MASSIVE_RATE_LIMIT_SIMULATE_PER_MIN` (12) | Ventana deslizante por IP; 429 + `Retry-After`. Desactivable con `MASSIVE_RATE_LIMIT_ENABLED=0`. |
| **Cabeceras** | automáticas | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`, `Permissions-Policy` restrictiva. |
| **Hosts** | `MASSIVE_ALLOWED_HOSTS` | TrustedHostMiddleware (default `*` en dev). |
| **CORS** | `MASSIVE_CORS_ORIGINS` | Solo desarrollo (Vite); en producción el frontend es same-origin. |
| **Subida de archivos** | n/a en UI-NG | La UI-NG no expone subida de archivos; el endpoint legacy `/api/extract` mantiene sus propios límites. |

> **Nota multi-worker:** el rate limiter vive en memoria del proceso. La
> imagen Docker corre **1 worker por contenedor** a propósito; escála
> horizontalmente (más réplicas) detrás de un balanceador con afinidad de
> sesión o migra a un backend compartido (Redis) reemplazando
> `backend/app/rate_limit.py` — la interfaz no cambia.

---

## 4. Persistencia

- SQLite en `MASSIVE_DATA_DIR/runs.db` (default `data/ui_ng/runs.db`,
  ignorado por git). Modo WAL + busy timeout → lecturas concurrentes seguras.
- La BD es la **fuente de verdad**; la memoria es solo caché LRU
  (`MASSIVE_RUN_STORE_CAPACITY`=500 corridas retenidas).
- **Backup:** copiar `runs.db` (con `sqlite3 runs.db ".backup runs.bak"` para
  consistencia). Es un archivo único; se puede montar como volumen (compose:
  `massive-ui-ng-data`).

---

## 5. Observabilidad

| Señal | Dónde |
|---|---|
| Liveness/readiness | `GET /health` → `{status, store}` (verifica SQLite). Usado por el HEALTHCHECK de Docker. |
| Capacidades | `GET /api/status` → proveedor LLM, CfC, Rust, motores, países Factbook. |
| Logs | stdout, nivel `MASSIVE_LOG_LEVEL` (default INFO). Eventos clave: modo dev sin API key, fallos LLM→fallback heurístico, hits de rate limit, errores de simulación (con traza). |
| Métricas | `GET /metrics` (formato texto Prometheus, sin dependencias): `http_requests_total{method,group}`, `simulations_total{engine}`, `ws_connections_total`, `ws_snapshots_total`, `ws_shocks_total`, `ws_stops_total`, `rate_limit_hits_total{group}`, `llm_requests_total{provider,outcome}`. |
| Errores de cara al usuario | Nunca se filtran trazas: respuestas 4xx/5xx con `detail` genérico. |

Ejemplo de scrape config:

```yaml
scrape_configs:
  - job_name: massive-ui-ng
    metrics_path: /metrics
    static_configs:
      - targets: ["tu-servicio:8000"]
```

---

## 6. Variables de entorno (referencia)

| Variable | Default | Descripción |
|---|---|---|
| `PROVIDER` | `groq` | Proveedor LLM: `groq` \| `openai` \| `openrouter` \| `ollama` |
| `GROQ_API_KEY` / `OPENAI_API_KEY` / `OPENROUTER_API_KEY` | — | Claves de proveedor |
| `OLLAMA_HOST` / `OLLAMA_MODEL` | `http://localhost:11434` / `llama3.2` | LLM local |
| `MASSIVE_LLM_MODEL` | por proveedor | Override de modelo |
| `MASSIVE_LLM_TIMEOUT` / `MASSIVE_LLM_MAX_TOKENS` | `45` / `1400` | Límites de llamadas LLM |
| `MASSIVE_ENV` | `development` | `production` cambia convenciones de log/seguridad |
| `MASSIVE_API_KEYS` | *(vacío)* | Claves API separadas por coma |
| `MASSIVE_ALLOWED_HOSTS` | `*` | Hosts permitidos (coma-separada) |
| `MASSIVE_CORS_ORIGINS` | localhost dev | Orígenes CORS |
| `MASSIVE_TRUST_PROXY` | `0` | Confiar en `X-Forwarded-For` (solo tras proxy que lo filtre) |
| `MASSIVE_RATE_LIMIT_ENABLED` | `1` | Activar rate limiting |
| `MASSIVE_RATE_LIMIT_PER_MIN` | `120` | Peticiones/min por IP (general) |
| `MASSIVE_RATE_LIMIT_SIMULATE_PER_MIN` | `12` | Peticiones/min por IP (simulación/explicación) |
| `MASSIVE_DATA_DIR` | `data/ui_ng` | Directorio de persistencia SQLite |
| `MASSIVE_RUN_STORE_CAPACITY` | `500` | Corridas retenidas |
| `MASSIVE_SERVE_FRONTEND` | `1` | Servir `frontend/dist` (auto-detecta si existe) |
| `MASSIVE_LOG_LEVEL` | `INFO` | Nivel de logging |

---

## 7. API (resumen)

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/health` | — | Liveness/readiness |
| GET | `/metrics` | —* | Prometheus (text format): contadores HTTP, simulaciones, WS, rate limit, LLM |
| GET | `/api/status` | — | Capacidades (UI bootstrap) |
| POST | `/api/conversation` | ✓ | Turno del traductor (JSON) |
| POST | `/api/conversation/stream` | ✓ | Idem con **SSE**: `status` → `token`* → `done` |
| POST | `/api/simulate` | ✓ | Ejecuta motor → resultado + narrativa |
| POST | `/api/simulate/stream` | ✓ | Idem con **SSE**: `status` → `progress` → `done`/`error` |
| POST | `/api/explain` | ✓ | Re-narra una corrida (audiencia/idioma) |
| GET | `/api/runs` | ✓ | Historial (últimas 50) |
| GET | `/api/runs/{id}` | ✓ | Corrida completa + narrativa |
| DELETE | `/api/runs/{id}` | ✓ | Eliminar corrida |
| WS | `/ws/live` | ✓† | **Simulación en vivo**: snapshots por tick (`SimSnapshotMessage`) y eventos de ciclo (`started`/`stopped`/`error`). Motores: `energy` (agentes + red) y `massive` (agregado + **shocks interactivos**). Parámetros por query: `engine`, `n_agents`, `pasos`, `seed`, `user_goal` (arquetipo de paisaje), `tick_interval_ms` |

\* `token` solo en modo LLM (deltas de streaming); en modo heurístico se
emiten `status` y `done` directamente.

\* `/metrics` queda abierto para el scraping de Prometheus; restringirlo a
nivel de red (firewall/Ingress) si se expone públicamente.

† Los navegadores no pueden enviar cabeceras en WebSocket: la key se pasa
como `?api_key=...` cuando `MASSIVE_API_KEYS` está configurado (validación
idéntica, cierre con código 4401 si es inválida). Comandos del cliente:
`{"action":"stop"}` y `{"action":"shock","value":…,"fraction":…}` (masivo).

---

## 8. Calidad y CI

- **Suite backend**: `pytest tests/test_ui_ng.py tests/test_ui_ng_live.py`
  (24 tests: contrato del traductor, 4 motores, SSE, CRUD + persistencia
  SQLite, auth, rate limit, **WebSocket en vivo** (energy/massive, shock,
  stop del cliente, auth 4401) y **endpoint /metrics**).
- **Evaluación del traductor**: `python -m backend.app.evaluation` corre un
  **golden set** de 8 escenarios (ES/EN) con umbral 80% (falla el CI).
  `EVAL_LLM=1` evalúa el camino LLM real cuando hay API key.
- **Sincronía de contrato**: `python scripts/gen_ts_types.py` regenera
  `frontend/src/types/api.generated.ts`; el CI falla si el archivo
  comprometido difiere.
- **Workflow**: `.github/workflows/ui-ng.yml` (backend: pytest + eval +
  contract-sync · frontend: `npm ci && npm run build`).

---

## 9. Modos de operación (paridad UX)

| | LLM configurado | Sin LLM |
|---|---|---|
| Interpretación | LLM con JSON-mode + few-shot (prompts v1) | Parser determinista ES/EN |
| Streaming | Deltas de tokens en tiempo real | `done` inmediato |
| Narración | Generativa (prompt con datos del run) | Plantilla determinista (nunca alucina) |
| Badge UI | `LLM: groq` | `Modo heurístico (sin LLM)` |

---

## 10. Roadmap pendiente (post-v1)

- [x] `/metrics` Prometheus (contadores v1, sin dependencias)
- [x] WebSocket de simulación en vivo (`/ws/live`): snapshots por tick
      (energy con red de agentes; massive con shocks interactivos)
- [ ] Dashboards Grafana sobre `/metrics`
- [ ] Multi-tenancy (carpetas de corridas por API key)
- [ ] Migración del rate limiter a Redis para multi-worker sin afinidad
- [ ] Retiro de la UI Streamlit (`app.py`) al alcanzar paridad total
