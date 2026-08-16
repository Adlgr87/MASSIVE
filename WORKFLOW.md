# 🌊 MASSIVE UI-NG — Workflow General

> Cómo y por qué funciona todo el sistema, de punta a punta.
> Complemento de `README.md` (instalación) y `EXAMPLES.md` (código).

---

## 1. El problema que resuelve

MASSIVE es un simulador híbrido de dinámica social (opiniones, polarización,
intervenciones) con capas científicas profundas: Langevin, Hegselmann-Krause,
teoría de juegos evolutiva, EnKF, early warning signals, topología.

Su UI original (Streamlit, `app.py`) exponía **~40 parámetros técnicos**
(`hk_epsilon`, `alpha_blend`, `sesgo_confirmacion`, `umbral_std`…)
directamente al usuario. Perfecto para un científico social; **excluyente
para cualquier otra persona** que sí puede describir el problema en lenguaje
natural.

## 2. La solución: el LLM como traductor bidireccional

```
lenguaje natural (usuario)  ──LLM──▶  parámetros MASSIVE validados
                                        + supuestos explícitos (con confianza)
                                        + preguntas sobre lo que falta

resultados técnicos         ──LLM──▶  explicación en prosa
                                        (qué pasó, por qué, qué lo causó)
```

Dos reglas de oro:

1. **Nunca ejecutar a ciegas**: cada supuesto se muestra editable antes de
   simular, con semáforo de confianza (verde > 0.7, naranja > 0.4, rojo).
2. **Nada bloquea a nadie**: sin API key, un parser determinista ES/EN y un
   narrador de plantillas hacen el mismo trabajo (y nunca alucinan). La UX
   es idéntica; solo cambia un badge de modo.

## 3. Flujo del traductor (workflow principal)

```
┌───────────────────────────────────────────────────────────────────┐
│ 1. USUARIO describe su escenario (chat)                            │
│    "¿Qué pasa si lanzan una campaña agresiva y la gente ya        │
│     desconfía de las instituciones? Hay polarización."            │
└────────────────────────────┬──────────────────────────────────────┘
                             ▼
┌───────────────────────────────────────────────────────────────────┐
│ 2. INTERPRETACIÓN  POST /api/conversation(/stream)                │
│    LLM (prompts v1, JSON-mode, few-shot)  o  scenario_parser      │
│    ──▶ config_draft {estado_inicial, escenario, pasos, config}    │
│    ──▶ assumptions[{parameter, value, reason, confidence}]        │
│    ──▶ questions[] (máx. 3, solo lo que falta)                    │
└────────────────────────────┬──────────────────────────────────────┘
                             ▼
┌───────────────────────────────────────────────────────────────────┐
│ 3. REVISIÓN HUMANA (DraftEditor)                                   │
│    Chips editables + semáforo de confianza + preguntas clicables  │
│    (alternativa: pestaña "Guía paso a paso" = formulario clásico) │
└────────────────────────────┬──────────────────────────────────────┘
                             ▼
┌───────────────────────────────────────────────────────────────────┐
│ 4. SIMULACIÓN  POST /api/simulate(/stream)                        │
│    engine: scalar (reglas+IA) · energy (Langevin) ·               │
│            multilayer (sociodemográfico) · massive (super-agentes)│
│    opcional: reporte científico (estabilidad, eigenvalores, EWS)  │
└────────────────────────────┬──────────────────────────────────────┘
                             ▼
┌───────────────────────────────────────────────────────────────────┐
│ 5. TRADUCCIÓN INVERSA (narrative.py + LLM en /api/explain)        │
│    · Lenguaje general: analogías, qué significa para una persona  │
│    · Técnico: métricas, mecanismos, estabilidad, eigenvalores     │
│    · Cadena causal: regla elegida → mecanismo → efecto            │
│    · Aviso honesto (PVU-BS): es simulación, no predicción         │
└────────────────────────────┬──────────────────────────────────────┘
                             ▼
┌───────────────────────────────────────────────────────────────────┐
│ 6. ITERAR  (refinar la conversación, re-explicar, historial)      │
│    o MODO EN VIVO  (tab 🔴): WS /ws/live, tick a tick,            │
│    red de agentes animada, shocks interactivos en mitad de la     │
│    corrida                                                        │
└───────────────────────────────────────────────────────────────────┘
```

### Contrato JSON del traductor (invariante)

```json
{
  "reply": "texto corto en lenguaje natural",
  "action": "clarify | propose | ready",
  "assumptions": [
    {"parameter": "n_agents", "value": "10,000",
     "reason": "no especificaste tamaño; usé ciudad media",
     "confidence": 0.55}
  ],
  "questions": ["¿La campaña empuja a favor o en contra?"],
  "config_draft": {
    "estado_inicial": {"opinion": 0.35, "propaganda": 0.8, "confianza": 0.3},
    "escenario": "campana", "pasos": 60,
    "config": {"rango": "[-1, 1] — Bipolar", "sesgo_confirmacion": 0.5}
  },
  "mode": "llm | heuristic"
}
```

El frontend **nunca distingue** quién respondió: LLM o heurística producen
exactamente la misma estructura (validada con Pydantic `extra="forbid"`).

## 4. Arquitectura

```
frontend/  (React + Vite + TS)               backend/  (FastAPI)
┌──────────────────────────────┐            ┌────────────────────────────────┐
│ App (ES/EN)                  │            │ main.py (fábrica de app)        │
│ ├─ StatusBar (modo LLM/CfC)  │  /api/*    │  middlewares:                   │
│ ├─ ChatPanel (conversación)  │ ─────────▶ │  · security headers             │
│ │   └─ AssumptionsPanel      │   (Vite    │  · contador HTTP (Prometheus)   │
│ ├─ DraftEditor (supuestos)   │    proxy)  │  · TrustedHost / CORS           │
│ ├─ GuidedForm (formulario)   │            │  · RateLimitMiddleware          │
│ ├─ ResultsPanel (dashboard)  │            │ routers:                        │
│ └─ LiveControls + LiveView   │  /ws/live  │  · status   /api/status         │
│    (WebSocket)               │ ─────────▶ │  · conversation /api/conversation│
└──────────────────────────────┘            │    (+ /stream SSE)              │
                                            │  · simulation /api/simulate     │
                                            │    (+ /stream SSE, /explain,    │
                                            │     /runs CRUD)                 │
                                            │  · live  /ws/live (WS)          │
                                            │ infra:                          │
                                            │  · llm_chat (proveedores+SSE)   │
                                            │  · llm_prompts (prompts v1)     │
                                            │  · scenario_parser (fallback)   │
                                            │  · narrative (narrador)         │
                                            │  · run_store (SQLite WAL)       │
                                            │  · live_runner (tick-a-tick)    │
                                            │  · metrics (Prometheus)         │
                                            └──────────────┬─────────────────┘
                                                           ▼
                                      MASSIVE existente (SIN MODIFICAR):
                                      simulator.py · massive_core ·
                                      energy_engine · multilayer_engine ·
                                      massive_engine · factbook · services
```

### Fallbacks en cascada (filosofía MASSIVE)

| Capa | Preferido | Fallback |
|---|---|---|
| Interpretación | LLM (JSON-mode) | `scenario_parser.py` (keywords ES/EN) |
| Streaming conversación | SSE con deltas | endpoint síncrono (el frontend lo detecta) |
| Narración | LLM generativa | `narrative.py` (plantilla determinista, sin alucinaciones) |
| Simulación | reporte científico opt-in | resumen legacy |
| GPU | CuPy → PyTorch | NumPy (dentro de los motores) |
| Persistencia | SQLite | memoria (si no hay data dir) |

## 5. Superficie de la API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Liveness/readiness (verifica SQLite) |
| GET | `/metrics` | Prometheus text-format |
| GET | `/api/status` | Capacidades (LLM, CfC, Rust, motores, Factbook) |
| POST | `/api/conversation` | Turno del traductor (JSON) |
| POST | `/api/conversation/stream` | Idem con SSE (`status` → `token`* → `done`) |
| POST | `/api/simulate` | Simulación → resultado + narrativa |
| POST | `/api/simulate/stream` | Idem con SSE (`status` → `progress` → `done`) |
| POST | `/api/explain` | Re-narra una corrida (idioma × audiencia) |
| GET / GET / DELETE | `/api/runs`, `/api/runs/{id}` | Historial / detalle narrado / borrado |
| WS | `/ws/live` | En vivo: `SimSnapshotMessage` por tick + eventos + comandos `stop`/`shock` |

\* `token` solo en modo LLM.

## 6. Fases ejecutadas

| Fase | Entregable | Estado |
|---|---|---|
| 1 · Contrato y backend | DTOs, routers, parser heurístico, narrador, run store | ✅ |
| 2 · Frontend | Chat + supuestos + formulario + dashboard + historial | ✅ |
| 3 · LLM real | Prompts v1 (few-shot + JSON-mode), golden set (8 casos, 100%), SSE | ✅ |
| 4 · Producción | Auth multi-key, rate limit, SQLite WAL, tipos generados + CI, Docker, estáticos, health | ✅ |
| 5 · En vivo + métricas | WebSocket `/ws/live` (red de agentes, shocks), `/metrics` Prometheus | ✅ |
| 6 · Retiro de Streamlit | Redirigir `app.py` cuando haya paridad total | ⏳ |

## 7. Garantías de calidad

- **24 tests** (`tests/test_ui_ng*.py`): contrato del traductor, 4 motores,
  SSE, WS (energy/massive/shock/stop/auth 4401), métricas, auth, rate limit,
  persistencia cross-instancia.
- **Golden set** (`eval_golden.json`): 8 escenarios ES/EN con expectativas
  estructuradas; `python -m backend.app.evaluation` (umbral 80% en CI;
  `EVAL_LLM=1` evalúa el camino LLM real).
- **Contrato sincronizado**: `scripts/gen_ts_types.py` regenera los tipos
  TypeScript desde los DTOs Pydantic; el CI falla si difieren.
- **Honestidad PVU-BS**: las narrativas siempre declaran que es una
  simulación basada en supuestos, nunca una predicción empírica.

## 8. Decisiones de diseño clave (por qué funciona así)

1. **Contrato único, dos intérpretes**: si el LLM falla o falta la key, el
   usuario no se entera de la diferencia — solo cambia el badge.
2. **Supuestos como ciudadanos de primera clase**: la confianza se modela
   por parámetro, no como nota al pie; es la herramienta anti-alucinación.
3. **Reutilizar los DTOs existentes**: el WS en vivo usa
   `SimSnapshotMessage`/`SimEventMessage` que el repo ya había reservado
   (`backend/app/models/dto_simulation.py`) — cero invención de contrato.
4. **SQLite como fuente de verdad** (no la memoria): las corridas
   sobreviven reinicios y los borrados son consistentes entre instancias.
5. **Un solo servicio en producción**: el backend sirve el frontend
   compilado → sin CORS, sin proxy extra, despliegue trivial.
6. **Rate limiter por-proceso a propósito**: la imagen corre 1 worker;
   escalar es horizontal (más réplicas) o migrar el backend del limiter a
   Redis sin tocar los routers.
7. **Métricas sin dependencias**: registro propio en formato texto
   Prometheus; si se necesita más, se cambia el interior por
   `prometheus_client` sin tocar los call sites.

## 9. Requisitos para integrarlo (recapitulación)

- Checkout de MASSIVE (los motores y `massive_core` no viajan en este
  paquete).
- Fusionar respetando las rutas relativas (ver `README.md` §4).
- `pip install -r requirements.txt httpx` + `npm ci` en `frontend/`.
- Verificar con `README.md` §7 antes de desplegar.
