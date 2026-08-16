# 📘 MASSIVE UI-NG — Ejemplos de Implementación

> Todos los ejemplos fueron **verificados contra la implementación v1.0**.
> URL base: `http://localhost:8000` (producción) o `http://localhost:5173`
> (desarrollo con Vite, que proxya `/api`, `/ws`, `/metrics` y `/health`).

---

## Índice

1. Traductor: conversación (Python + curl)
2. Simulación con reporte científico
3. Streaming SSE (conversación y simulación)
4. WebSocket en vivo (energy + massive + shocks)
5. Re-explicación y CRUD de corridas
6. Auth, rate limiting y métricas Prometheus
7. Evaluación de calidad y tests
8. React: usar el cliente tipado y los componentes
9. Docker y despliegue
10. Variables de entorno útiles

---

## 1. Traductor: conversación

**curl**

```bash
curl -s -X POST http://localhost:8000/api/conversation \
  -H "Content-Type: application/json" \
  -d '{
    "language": "es",
    "messages": [{
      "role": "user",
      "content": "¿Qué pasaría si en mi ciudad lanzan una campaña muy agresiva y la gente ya desconfía de las instituciones? Hay mucha polarización."
    }]
  }'
```

**Respuesta** (contrato invariante — igual con LLM o heurístico):

```json
{
  "reply": "Interpreté tu escenario y preparé un borrador de simulación. Veo una campaña activa sobre una población desconfiada…",
  "action": "propose",
  "mode": "heuristic",
  "assumptions": [
    {"parameter": "opinion_inicial", "value": "0.50 (neutro)",
     "reason": "no mencionaste un punto de partida; asumí una opinión neutra",
     "confidence": 0.5},
    {"parameter": "propaganda", "value": "0.85",
     "reason": "hay una campaña activa descrita como agresiva/intensa",
     "confidence": 0.65},
    {"parameter": "confianza", "value": "0.25",
     "reason": "mencionas desconfianza institucional → mayor volatilidad",
     "confidence": 0.7}
  ],
  "questions": ["Si conoces el apoyo actual aproximado (%), dímelo y lo usaré como punto de partida."],
  "config_draft": {
    "estado_inicial": {"opinion": 0.5, "propaganda": 0.85, "confianza": 0.25},
    "escenario": "campana",
    "pasos": 60,
    "config": {"rango": "[0, 1] — Probabilístico", "sesgo_confirmacion": 0.6,
               "hk_epsilon": 0.2, "ruido_desconfianza": 0.12}
  }
}
```

**Python**

```python
import requests

API = "http://localhost:8000"

r = requests.post(f"{API}/api/conversation", json={
    "language": "es",
    "messages": [{
        "role": "user",
        "content": (
            "Quiero entender la polarización en redes sociales antes de unas "
            "elecciones en México, con un 40% de apoyo inicial."
        ),
    }],
})
turn = r.json()

# El parser detecta: porcentaje → opinión 0.4, elecciones → 90 pasos,
# México → ofrece calibración con World Factbook.
print("action:", turn["action"], "| mode:", turn["mode"])
for a in turn["assumptions"]:
    print(f"  {a['parameter']:<20} = {a['value']:<25} confianza {a['confidence']}")
print("factbook:", turn["config_draft"]["config"].get("factbook_country"))
```

**Salida esperada:**

```
action: propose | mode: heuristic
  opinion_inicial      = 40% → 0.40 en [0,1]   confianza 0.6
  propaganda           = 0.30                  confianza 0.5
  ...
  factbook_country     = MX
  pasos: 90
```

---

## 2. Simulación con reporte científico

```python
draft = turn["config_draft"]   # reutilizar el borrador del traductor

resp = requests.post(f"{API}/api/simulate", json={
    "engine": "scalar",
    "escenario": draft.get("escenario", "campana"),
    "pasos": draft.get("pasos", 60),
    "estado_inicial": draft.get("estado_inicial", {}),
    "config": {**draft.get("config", {}), "seed": 42},
    "scientific": True,
    "language": "es",
    "audience": "general",      # "general" | "tecnico"
}).json()

print("run_id:", resp["run_id"])
print("resumen:", {k: resp["summary"][k] for k in
                   ("opinion_inicial", "opinion_final", "delta_total",
                    "polarizacion_media", "regla_dominante")})
print("estabilidad:", resp["scientific_report"]["stability_label"])
print("narrativa:\n", resp["narrative"][:400])
print("highlights:", [(h["label"], h["value"]) for h in resp["highlights"]])
```

**Salida esperada (ejemplo real):**

```
resumen: {'opinion_inicial': 0.4, 'opinion_final': 0.72,
          'delta_total': 0.32, 'polarizacion_media': 0.24,
          'regla_dominante': 'polarizacion'}
estabilidad: stable
narrativa:
## ¿Qué pasó?
La opinión partió de **+0.40** y terminó en **+0.72** (neutro = +0.5)…
## ¿Por qué pasó?
El mecanismo dominante fue **polarizacion**: las posiciones se alejaron
del centro: la moderación perdió terreno…
```

**Los 4 motores disponibles:** `scalar`, `energy` (Langevin),
`multilayer` (sociodemográfico), `massive` (super-agentes, 99% ahorro RAM):

```python
# Energy
resp = requests.post(f"{API}/api/simulate", json={
    "engine": "energy", "pasos": 40, "n_agents": 60,
    "range_type": "bipolar", "scientific": False,
    "language": "es", "audience": "general",
    "estado_inicial": {}, "config": {},
}).json()

# Massive (escala poblacional)
resp = requests.post(f"{API}/api/simulate", json={
    "engine": "massive", "pasos": 40, "n_agents": 20_000,
    "scientific": False, "language": "es", "audience": "general",
    "estado_inicial": {}, "config": {},
}).json()
print("meta:", {k: resp["meta"].get(k) for k in
                ("n_agents", "n_clusters", "memory_savings_pct", "steps_per_second")})
```

---

## 3. Streaming SSE

### 3.1 Conversación con tokens en vivo (modo LLM)

```python
import json
import requests

with requests.post(
    f"{API}/api/conversation/stream",
    json={"language": "es",
          "messages": [{"role": "user",
                        "content": "hay mucha polarización y desconfianza"}]},
    stream=True,
) as r:
    for line in r.iter_lines(decode_unicode=True):
        if not line:
            continue
        event, _, data = line.partition(":")
        if event == "event":
            pass  # nombre del próximo evento
        elif data.strip():
            payload = json.loads(data.strip())
            # eventos: status → token* → done   (*solo modo LLM)
```

**JavaScript (como lo hace el frontend, `src/stream.ts`):**

```ts
import { api } from "./api";

await api.conversationStream(msgs, "es", (event, data) => {
  if (event === "token") appendToChat(data.text);   // delta del LLM
  if (event === "done") applyTurn(data);            // ConversationResponse completa
});
// fallback automático al endpoint síncrono si el stream falla
```

### 3.2 Simulación con progreso

```bash
curl -sN -X POST http://localhost:8000/api/simulate/stream \
  -H "Content-Type: application/json" \
  -d '{"engine":"scalar","pasos":30,"scientific":true,"language":"es",
       "audience":"general","estado_inicial":{"opinion":0.4,"propaganda":0.8,"confianza":0.3},
       "config":{"seed":1}}'
```

**Eventos emitidos:**

```
event: status
data: {"state": "queued", "engine": "scalar"}

event: progress
data: {"state": "running", "elapsed": 0.4}

event: progress
data: {"state": "running", "elapsed": 0.7}

event: done
data: {"run_id": "3c9e6b05934b", "engine": "scalar", …}
```

---

## 4. WebSocket en vivo (`/ws/live`)

### 4.1 Motor de energía: red de agentes tick a tick

```python
import asyncio
import json

import websockets


async def main():
    uri = (
        "ws://localhost:8000/ws/live"
        "?engine=energy"
        "&n_agents=60"
        "&pasos=120"
        "&user_goal=polarizacion_extrema"   # arquetipo de paisaje
        "&tick_interval_ms=30"
        "&seed=42"
    )
    async with websockets.connect(uri) as ws:
        async for raw in ws:
            msg = json.loads(raw)
            if msg["type"] == "event":
                print("EVENTO:", msg["event"], msg.get("detail"))
                if msg["event"] in ("stopped", "error"):
                    break
            elif msg["type"] == "snapshot":
                p = msg["payload"]
                m = p["metrics"]
                print(
                    f"tick={p['tick']:3d}  mean={m['mean_opinion']:+.3f}  "
                    f"pol={m['polarization']:.3f}  consenso={m['consensus_rate']:.2f}  "
                    f"agentes={len(p['agents'])}"
                )


asyncio.run(main())
```

**Salida real verificada:**

```
EVENTO: started engine=energy agents=60 pasos=120
tick=  1  mean=+0.045  pol=0.628  consenso=0.15  agentes=60
tick=  2  mean=+0.051  pol=0.631  consenso=0.15  agentes=60
...
EVENTO: stopped horizon reached
```

Cada `agents[i]` trae `{id, layer, x, y, opinion}` — el frontend dibuja la
red con opinión mapeada a color (rojo rechazo → gris neutro → cian apoyo).

### 4.2 Motor masivo + shock interactivo a mitad de corrida

```python
import asyncio
import json

import websockets


async def main():
    uri = ("ws://localhost:8000/ws/live"
           "?engine=massive&n_agents=5000&pasos=15&tick_interval_ms=0&seed=9")
    async with websockets.connect(uri) as ws:
        async for raw in ws:
            msg = json.loads(raw)
            if msg["type"] == "event":
                if msg["event"] == "stopped":
                    break
                continue
            m = msg["payload"]["metrics"]
            print(f"tick={msg['payload']['tick']:2d}  mean={m['mean_opinion']:+.3f}  "
                  f"activos={m['active_agents']}")
            if msg["payload"]["tick"] == 5:
                # ¡Shock! evento externo: noticia viral, crisis, cambio de política
                await ws.send(json.dumps({"action": "shock", "value": 0.6, "fraction": 0.4}))
                print("  → shock enviado (magnitud 0.6, 40% de los super-agentes)")


asyncio.run(main())
```

**Salida real verificada:**

```
tick= 5  mean=+0.027  activos=70
  → shock enviado (magnitud 0.6, 40% de los super-agentes)
tick=10  mean=+0.210  activos=70     ← la media saltó tras el shock
tick=15  mean=+0.198  activos=70
```

Otros comandos del cliente: `{"action": "stop"}` (detención limpia).

**En el navegador** (así lo usa el frontend, `src/live.ts`):

```ts
import { openLiveStream } from "./live";

const conn = openLiveStream(
  { engine: "energy", n_agents: 60, connectivity: 0.25, range_type: "bipolar",
    seed: 42, pasos: 150, user_goal: "polarizacion_moderada" },
  {
    onOpen: () => console.log("conectado"),
    onSnapshot: (snap) => renderNetwork(snap),   // snap.agents + snap.metrics
    onEvent: (event, detail) => console.log(event, detail),
    onClose: () => console.log("cerrado"),
    onError: (err) => console.error(err),
  }
);
conn.send({ action: "shock", value: 0.5, fraction: 0.3 });
conn.send({ action: "stop" });
```

**Arquetipos de paisaje disponibles (energy):** `polarizacion_extrema`,
`polarizacion_moderada`, `consenso_moderado`, `consenso_forzado`,
`fragmentacion_3_grupos`, `fragmentacion_4_grupos`, `caos_social`,
`radicalizacion_progresiva`.

---

## 5. Re-explicación y CRUD de corridas

```python
# Re-narrar una corrida guardada en otro idioma/audiencia
resp = requests.post(f"{API}/api/explain", json={
    "run_id": run_id, "language": "en", "audience": "tecnico",
}).json()
print(resp["mode"])          # "llm" (si hay proveedor) | "template"
print(resp["narrative"][:300])

# Historial
runs = requests.get(f"{API}/api/runs").json()
for r in runs:
    print(r["run_id"], r["engine"], r["headline"], r["dominant_rule"])

# Detalle completo narrado
det = requests.get(f"{API}/api/runs/{run_id}?language=es&audience=general").json()

# Borrar
requests.delete(f"{API}/api/runs/{run_id}")
```

Las corridas persisten en SQLite (`MASSIVE_DATA_DIR/runs.db`, modo WAL) y
sobreviven reinicios del servicio.

---

## 6. Auth, rate limiting y métricas

### 6.1 API key

```bash
# Con MASSIVE_API_KEYS configurada, los endpoints protegidos exigen cabecera:
curl -s http://localhost:8000/api/runs -H "X-API-Key: mi-clave"

# WebSocket: la key viaja por query (los navegadores no mandan cabeceras en WS)
ws://localhost:8000/ws/live?api_key=mi-clave&engine=energy&...
# Key inválida → cierre con código 4401
```

### 6.2 Rate limiting

Exceder `MASSIVE_RATE_LIMIT_SIMULATE_PER_MIN` (default 12) produce:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 37
{"detail": "Too many requests"}
```

### 6.3 Métricas Prometheus

```bash
curl -s http://localhost:8000/metrics
```

```text
# HELP http_requests_total HTTP requests served (counter)
# TYPE http_requests_total counter
http_requests_total{group="simulate",method="POST"} 4
# HELP simulations_total Simulation runs by engine (counter)
simulations_total{engine="scalar"} 3
ws_connections_total 2
ws_snapshots_total 18
ws_shocks_total 1
rate_limit_hits_total{group="simulate"} 0
llm_requests_total{outcome="ok",provider="groq"} 12
```

`prometheus.yml`:

```yaml
scrape_configs:
  - job_name: massive-ui-ng
    metrics_path: /metrics
    scrape_interval: 30s
    static_configs:
      - targets: ["tu-servicio:8000"]
```

---

## 7. Evaluación de calidad y tests

```bash
# Golden set del traductor (8 escenarios ES/EN, umbral 80%)
python -m backend.app.evaluation
#   ✓ es_campana_polarizada        100.0%
#   ✓ es_elecciones_mexico_40      100.0%
#   …                                …
#   Overall score: 100.0% (8 cases) PASSED

# Evaluar el camino LLM real (requiere API key configurada)
EVAL_LLM=1 python -m backend.app.evaluation

# Suite completa del backend UI-NG (24 tests)
python -m pytest tests/test_ui_ng.py tests/test_ui_ng_live.py -q

# Sincronía de contrato Pydantic → TypeScript
python scripts/gen_ts_types.py && git diff --exit-code frontend/src/types/api.generated.ts
```

---

## 8. React: cliente tipado y componentes

El contrato TS se **genera desde los DTOs Pydantic**
(`scripts/gen_ts_types.py` → `frontend/src/types/api.generated.ts`).
El módulo `types.ts` re-exporta y añade vistas tipadas:

```tsx
import { api } from "./api";
import type { SimulateResponse, ConversationResponse } from "./types";

// 1) Conversación con streaming y fallback automático
async function ask(messages: ChatMessage[]): Promise<ConversationResponse> {
  let done: ConversationResponse | null = null;
  await api.conversationStream(messages, "es", (event, data) => {
    if (event === "token") showDelta(data.text);
    if (event === "done") done = data;
  });
  return done ?? (await api.conversation(messages, "es"));
}

// 2) Simulación tipada (el servidor valida extra="forbid")
const run: SimulateResponse = await api.simulate({
  engine: "scalar",
  escenario: "campana",
  pasos: 60,
  estado_inicial: { opinion: 0.4, propaganda: 0.8, confianza: 0.3 },
  config: { sesgo_confirmacion: 0.6, seed: 42 },
  scientific: true,
  language: "es",
  audience: "general",
});

// 3) Componentes listos para armar la UI
// <ChatPanel messages thinking streamingText turn lang onSend onAsk />
// <DraftEditor draft lang running elapsed onRun onDiscard />
// <GuidedForm lang running elapsed onRun />
// <ResultsPanel run runs lang audience onAudience onRegenerate
//              onExample onLoadRun onDeleteRun />
// <LiveControls lang live onState />  +  <LiveView lang live bipolar />
// <StatusBar status lang />
```

---

## 9. Docker y despliegue

```bash
# Build (multi-stage: Node 20 build → Python 3.11 slim, usuario no-root)
docker build -f Dockerfile.ui-ng -t massive-ui-ng .

# Run (un solo servicio: API + frontend compilado)
docker run -d -p 8000:8000 \
  -e PROVIDER=groq \
  -e GROQ_API_KEY=gsk_... \
  -e MASSIVE_API_KEYS=$(openssl rand -hex 24) \
  -e MASSIVE_ALLOWED_HOSTS=tu-dominio.com \
  -e MASSIVE_TRUST_PROXY=1 \
  -v massive-data:/data \
  massive-ui-ng

# Healthcheck incluido (curl /health cada 30s)
docker inspect --format '{{.State.Health.Status}}' <container>

# Con compose (levanta el servicio ui-ng en el puerto 8010)
docker compose up -d --build ui-ng
```

Reverse proxy nginx (SSE requiere `proxy_buffering off`):

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_buffering off;          # SSE y WebSocket
    proxy_read_timeout 300s;      # simulaciones largas
}
```

---

## 10. Variables de entorno útiles

| Variable | Default | Uso |
|---|---|---|
| `PROVIDER` | `groq` | Proveedor LLM (`groq`/`openai`/`openrouter`/`ollama`) |
| `GROQ_API_KEY` / `OPENAI_API_KEY` / `OPENROUTER_API_KEY` | — | Claves LLM |
| `OLLAMA_HOST` / `OLLAMA_MODEL` | `localhost:11434` / `llama3.2` | LLM local |
| `MASSIVE_API_KEYS` | *(vacío)* | Keys API (coma-separada); vacío = modo dev abierto |
| `MASSIVE_ALLOWED_HOSTS` | `*` | Hosts permitidos |
| `MASSIVE_TRUST_PROXY` | `0` | Confiar `X-Forwarded-For` (solo tras proxy) |
| `MASSIVE_RATE_LIMIT_PER_MIN` / `_SIMULATE_PER_MIN` | `120` / `12` | Límites por IP |
| `MASSIVE_DATA_DIR` | `data/ui_ng` | Persistencia SQLite |
| `MASSIVE_RUN_STORE_CAPACITY` | `500` | Corridas retenidas |
| `MASSIVE_SERVE_FRONTEND` | `1` | Servir `frontend/dist` desde el backend |
| `MASSIVE_ENV` | `development` | `production` endurece convenciones |

Referencia completa: `docs/NEXT_GEN_UI_PRODUCTION_ES.md` §6 y
`infra/env.example`.
