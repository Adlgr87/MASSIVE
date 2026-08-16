# MASSIVE — Workflow de la UI de Nueva Generación (UI-NG)

> **Estado:** Implementado (v1) · **Fecha:** 2026-08-14
> **Alcance:** Reemplazo de la UI Streamlit (`app.py`) por una aplicación web
> production-ready con el LLM actuando como **traductor** entre el usuario y las
> capas científicas de MASSIVE.

---

## 1. Motivación

La UI actual (`app.py`, Streamlit) expone ~40 parámetros técnicos directamente
al usuario: `hk_epsilon`, `alpha_blend`, `sesgo_confirmacion`, `umbral_std`, etc.
Eso es correcto para un científico social, pero excluye a cualquier otra
persona (comunicadores, analistas, docentes, tomadores de decisión) que sí
puede describir el problema en lenguaje natural pero no domina la jerga.

**Principio rector:** MASSIVE ya tiene un LLM integrado. Usémoslo no solo para
elegir regímenes, sino como **traductor bidireccional**:

```
lenguaje natural (usuario)  ──LLM──▶  parámetros MASSIVE validados
                                        + supuestos explícitos
                                        + preguntas sobre lo que falta

resultados técnicos         ──LLM──▶  explicación en prosa
                                        (qué pasó, por qué, qué lo causó)
```

Un segundo principio: **nada de esto puede bloquear a nadie**. Si no hay API key
configurada, la aplicación completa sigue funcionando en **modo heurístico**
(parser determinista + narrador de plantillas), exactamente con la misma
filosofía de fallbacks del resto de MASSIVE (CfC→LLM→heurística).

---

## 2. El flujo del traductor (workflow principal)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. USUARIO describe su escenario                                        │
│    "¿Qué pasa si en mi ciudad lanzan una campaña muy agresiva           │
│     cuando la gente ya desconfía de las instituciones?"                 │
└──────────────────────────────┬──────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. INTERPRETACIÓN (LLM o parser heurístico)                             │
│    · Deriva un config_draft MASSIVE (opinión inicial, propaganda,       │
│      confianza, pasos, rango, sesgo de confirmación…)                   │
│    · Genera SUPUESTOS EXPLÍCITOS:                                        │
│        - parámetro           valor   por qué lo asumió   confianza      │
│        - "tamaño de la ciudad" → 10,000 agentes → "no lo especificaste; │
│           usé una ciudad media" → 0.55                                   │
│    · Detecta lo que FALTA y formula PREGUNTAS (máx. 3):                  │
│        "¿La campaña es a favor o en contra de qué posición?"            │
└──────────────────────────────┬──────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. REVISIÓN HUMANA (nunca se ejecuta a ciegas)                          │
│    El usuario ve los supuestos como chips editables (con semáforo de    │
│    confianza), responde preguntas opcionales, o confirma.               │
│    Puede alternar a la pestaña "Guía paso a paso" si prefiere un        │
│    formulario clásico.                                                  │
└──────────────────────────────┬──────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. SIMULACIÓN (POST /api/simulate)                                      │
│    Engine elegible: scalar (reglas+LLM) · energy (Langevin) ·           │
│    multilayer (sociodemográfico) · massive (super-agentes).             │
│    Con reporte científico opcional (estabilidad, EWS).                  │
└──────────────────────────────┬──────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. TRADUCCIÓN INVERSA (narrador)                                        │
│    Misma respuesta, dos idiomas:                                        │
│    · LENGUAJE GENERAL: analogías, qué significa para una persona        │
│    · TÉCNICO: métricas, reglas dominantes, estabilidad, EWS             │
│    Ambas explican el CÓMO y el PORQUÉ (cadena causal), no solo el qué.  │
│    Con LLM configurado: narración generativa. Sin LLM: plantilla        │
│    determinista honesta (nunca se inventa nada).                        │
└──────────────────────────────┬──────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 6. ITERACIÓN conversacional                                              │
│    "Ahora haz que la desconfianza sea mayor" → se re-ajusta el draft    │
│    y se re-ejecuta. Historial de corridas conservado en memoria.        │
└─────────────────────────────────────────────────────────────────────────┘
```

### El contrato JSON del traductor

Cada respuesta del asistente es estructurada, no solo texto:

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

Con LLM configurado, este JSON lo produce el modelo (vía prompt con contrato
estricto). Sin LLM, lo produce `scenario_parser.py` (keywords + heurística).
**El frontend es idéntico en ambos casos.**

---

## 3. Arquitectura

```
frontend/  (React + Vite + TypeScript)          backend/  (FastAPI)
┌─────────────────────────────┐                ┌──────────────────────────────┐
│ App (ES/EN, estado global)  │                │ main.py (CORS, auth opcional)│
│ ├─ StatusBar (modo LLM/CfC) │─── /api/* ───▶ │ routers:                     │
│ ├─ ChatPanel (conversación) │    (Vite      │  · status.py      /api/status │
│ │   └─ AssumptionsPanel     │     proxy)    │  · conversation.py /api/conv. │
│ ├─ GuidedForm (formulario)  │                │  · simulation.py  /api/simul.│
│ └─ ResultsPanel             │                │ infraestructura:             │
│    ├─ Charts (recharts)     │                │  · llm_chat.py (proveedores) │
│    ├─ NarrativePanel        │                │  · scenario_parser.py (fall.)│
│    └─ TechnicalJSON         │                │  · narrative.py (narrador)   │
└─────────────────────────────┘                │  · run_store.py (memoria)    │
                                               └──────────────┬───────────────┘
                                                              ▼
                                            MASSIVE ya existente (sin tocar):
                                            simulator.py · massive_core ·
                                            uil_adapter.py · services/ ·
                                            energy_runner · multilayer_engine ·
                                            massive_engine · factbook
```

**Reglas de integración (respetan CLAUDE.md):**

1. **Cero cambios al núcleo.** Todo lo nuevo vive en `backend/app/` y
   `frontend/`. Las APIs legacy (`simular`, etc.) no se tocan.
2. **Reutilización**: la interpretación NL→config usa `uil_adapter`/`llm_chat`
   cuando hay LLM; la simulación usa `services/` y los motores existentes.
3. **DTOs tipados**: los DTOs viven en `backend/app/models/dto_ui.py`
   (Pydantic v2, `extra="forbid"`), siguiendo la convención del repo, y las
   interfaces TS en `frontend/src/types.ts` (en una fase posterior se generan
   con `scripts/gen_ts_types.py`).
4. **Auth**: si `MASSIVE_API_KEY` está definida, se exige cabecera
   `X-API-Key`; si no, modo desarrollo abierto con warning (mismo patrón que
   `api.py`).
5. **El viejo `api.py` y `app.py` (Streamlit) se conservan** durante la
   transición; UI-NG es el reemplazo gradual. `frontend/src/MASSIVE_UIL_demo.jsx`
   queda como referencia de lenguaje visual (paleta, chips de confianza).

---

## 4. Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/status` | Capacidades: proveedor LLM configurado, CfC, motores, países Factbook, Rust |
| POST | `/api/conversation` | Turno del traductor → `reply + action + assumptions + questions + config_draft` |
| POST | `/api/conversation/stream` | Idem con SSE (deltas de tokens en modo LLM) |
| POST | `/api/simulate` | Ejecuta simulación (scalar/energy/multilayer/massive) → resumen + series + reporte + narrativa |
| POST | `/api/simulate/stream` | Idem con SSE (eventos de progreso) |
| POST | `/api/explain` | Re-narra un run almacenado con audiencia (`general`/`tecnico`) e idioma |
| GET | `/api/runs` | Historial de corridas de la sesión |
| GET / DELETE | `/api/runs/{id}` | Corrida completa narrada / eliminar corrida |
| WS | `/ws/live` | **Simulación en vivo**: snapshots por tick (`SimSnapshotMessage` DTO existente) con red de agentes (energy) o métricas agregadas + shocks interactivos (massive) |
| GET | `/metrics` | Prometheus text-format (contadores) |
| GET | `/health` | Liveness/readiness |

---

## 5. Modos de operación (paridad total de UX)

| | LLM configurado | Sin LLM (heurístico) |
|---|---|---|
| Interpretación | LLM (Groq/OpenAI/OpenRouter/Ollama) | `scenario_parser.py` (keywords ES/EN, países, porcentajes) |
| Supuestos/preguntas | Generados por el LLM | Derivados del parser (con confianza conservadora) |
| Narración | Generativa (prompt con datos del run) | `narrative.py` (plantilla determinista, honesta) |
| Selección de régimen en simulación | LLM/CfC según config | Heurístico determinista |
| Badge en UI | "LLM: groq" | "Modo heurístico — sin API key" |

---

## 6. La narrativa (traducción inversa)

El narrador recibe el run completo y produce:

- **Lenguaje general**: qué pasó con la opinión (subió/bajó), cuán dividida
  quedó la población, qué "fuerza" dominó (p. ej. "la gente reaccionó en
  contra de la propaganda"), y **qué significa** para un no-experto, con la
  advertencia honesta de que es una simulación, no una predicción empírica
  (alineado con el protocolo PVU-BS).
- **Técnico**: `opinion_inicial → opinion_final`, Δ, polarización media,
  regla dominante (con el porqué registrado en `_razon` de cada paso),
  estabilidad del punto fijo (eigenvalores), señales EWS (critical slowing
  down), parámetros del rango.

Ambas versiones explican la **cadena causal**: *regla elegida → mecanismo →
 efecto en la trayectoria*, usando los metadatos que el simulador ya guarda
(`_regla_nombre`, `_razon`) en cada paso.

---

## 7. Plan de fases (resto del camino)

- [x] **Fase 1 — Contrato y backend**: DTOs, routers, parser heurístico,
      narrador de plantillas, run store.
- [x] **Fase 2 — Frontend**: chat + supuestos editables + formulario guiado +
      dashboard de resultados + historial.
- [x] **Fase 3 — LLM real**: prompts de producción (v1, few-shot + JSON-mode),
      evaluación de calidad (golden set ES/EN, 8 casos), streaming SSE en
      conversación y simulación.
- [x] **Fase 4 — Producción** (ver `NEXT_GEN_UI_PRODUCTION_ES.md`): auth
      multi-key, rate limiting por IP, persistencia SQLite (WAL),
      tipos TS generados con `gen_ts_types.py` + check en CI, workflow
      `ui-ng.yml`, imagen Docker multi-stage, servido estático del frontend,
      health/readiness, **WebSocket de simulación en vivo** (`/ws/live`) y
      **métricas Prometheus** (`/metrics`). Pendiente post-v1: dashboards
      Grafana, multi-tenancy, Redis para multi-worker.
- [ ] **Fase 5 — Retiro de Streamlit**: redirigir `app.py` a la nueva UI
      cuando la paridad de features sea total.

---

## 8. Cómo ejecutar (desarrollo)

```bash
# Backend (desde la raíz del repo)
pip install -r requirements.txt
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm install && npm run dev
# → http://localhost:5173 (el proxy de Vite reenvía /api al :8000)

# Opcional: activar LLM real
export PROVIDER=groq
export GROQ_API_KEY=gsk_...
# o bien: PROVIDER=ollama OLLAMA_HOST=http://localhost:11434 OLLAMA_MODEL=llama3.2
```
