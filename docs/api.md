# MASSIVE API v1 Reference

> **Base URL:** `http://localhost:8000` (dev) or `https://api.massive.example.com` (prod)
> **Auth:** All `/v1/*` endpoints require `X-API-Key` header.

---

## Simulation Endpoints

### POST /v1/simulate

Run a scalar MASSIVE simulation from natural language.

```bash
curl -X POST http://localhost:8000/v1/simulate \
  -H "X-API-Key: $MASSIVE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "Simula la polarización política en una democracia joven",
    "simulation_steps": 100,
    "seed": 42
  }'
```

**Response:**
```json
{
  "sim_id": "sim_abc123",
  "motor": "scalar_engine",
  "config": { ... },
  "summary": { ... },
  "history": [ ... ],
  "narrative": "..."
}
```

---

### POST /v1/forecast

Temporal risk forecasting with analytical or Monte Carlo mode.

```bash
curl -X POST http://localhost:8000/v1/forecast \
  -H "X-API-Key: $MASSIVE_API_KEY" \
  -d '{"simulation_state": {...}, "temporal_horizon_days": 30}'
```

---

### POST /v1/engine/energy

Langevin energy landscape simulation with CfC corrections.

```bash
curl -X POST http://localhost:8000/v1/engine/energy \
  -H "X-API-Key: $MASSIVE_API_KEY" \
  -d '{"user_goal": "...", "n_agents": 500, "steps": 200}'
```

---

### POST /v1/engine/architect

Inverse-strategy search for intervention planning.

```bash
curl -X POST http://localhost:8000/v1/engine/architect \
  -H "X-API-Key: $MASSIVE_API_KEY" \
  -d '{"estado_inicial": {...}, "objetivo_usuario": "..."}'
```

---

## LLM Endpoints

### POST /v1/llm/run_simulation

Full UIL pipeline from natural language intent.

```bash
curl -X POST http://localhost:8000/v1/llm/run_simulation \
  -H "X-API-Key: $MASSIVE_API_KEY" \
  -d '{"intent": "...", "country": "BR", "simulation_steps": 20}'
```

### POST /v1/llm/wizard

Generate simulation config from natural language description.

```bash
curl -X POST http://localhost:8000/v1/llm/wizard \
  -H "X-API-Key: $MASSIVE_API_KEY" \
  -d '{"description": "High polarization scenario with Gini 0.6"}'
```

### POST /v1/llm/extract

Extract simulation config from uploaded document (PDF, DOCX).

```bash
curl -X POST http://localhost:8000/v1/llm/extract \
  -H "X-API-Key: $MASSIVE_API_KEY" \
  -F "file=@policy_paper.pdf"
```

---

## Infrastructure Endpoints

### GET /health
Liveness probe. Returns `200` if process is alive.

### GET /ready
Readiness probe. Returns `200` + checks dict if all dependencies available.

### GET /metrics
Prometheus text-format metrics. Includes:
- `http_requests_total` — request counter
- `http_responses_total` — response counter by status code
- `http_request_duration_seconds` — latency histogram
- `massive_slo_*` — SLO target gauges

### GET /openapi/v1.json
OpenAPI v1 specification (v1 endpoints only).

### GET /version
Build metadata and version info.

---

## Deprecation Notice

Legacy endpoints at `/api/*` are deprecated and return `X-API-Warn` header:

```
X-API-Warn: Deprecated endpoint. Use /v1/* instead. See PRODUCTION_ARCHITECTURE_SPEC.md §5.1
```

| Legacy | New Endpoint |
|--------|--------------|
| `/api/extract` | `/v1/llm/extract` |
| `/api/wizard` | `/v1/llm/wizard` |
| `/api/simulate-uil` | `/v1/llm/run_simulation` |

---

*Auto-generated from OpenAPI spec. Last updated: 2026-09-14*
