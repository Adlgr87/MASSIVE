# 🌊 MASSIVE UI-NG — Paquete de Integración (v1.0)

> **Kit distribuible de la Interfaz de Nueva Generación de MASSIVE**
> El LLM como **traductor bidireccional** entre usuarios no técnicos y las
> capas científicas del simulador de dinámica social MASSIVE.
> Fecha de empaquetado: 2026-08-14 · Estado: production-ready v1.

---

## 1. ¿Qué es este paquete?

Contiene **todos los archivos generados** para reemplazar la UI Streamlit de
MASSIVE por una aplicación web production-ready:

- **Backend FastAPI** (`backend/app/`) — API REST + SSE + WebSocket, auth,
  rate limiting, persistencia SQLite, métricas Prometheus.
- **Frontend React + Vite + TypeScript** (`frontend/`) — chat con el
  traductor, supuestos editables, formulario guiado, dashboard de
  resultados y **simulación en vivo** con red de agentes.
- **Tests** (24 tests), **evaluación de calidad del traductor** (golden set
  ES/EN), **CI**, **Docker**, **compose**, **documentación** y **ejemplos**.

**NO es un proyecto standalone**: es una capa que se fusiona sobre un
checkout existente del repositorio MASSIVE
(https://github.com/Adlgr87/MASSIVE), porque depende de sus motores
(`simulator.py`, `massive_core`, `energy_engine.py`, `multilayer_engine.py`,
`massive_engine.py`, `massive/core/factbook`, `services/`, etc.).

---

## 2. Contenido del paquete

```
massive-ui-ng-package/
├─ README.md                    ← este archivo (instrucciones)
├─ WORKFLOW.md                  ← workflow general del proyecto
├─ EXAMPLES.md                  ← ejemplos de implementación verificados
├─ MANIFEST.txt                 ← inventario de archivos
│
├─ backend/app/                 ← backend FastAPI (fusionar en el repo)
│  ├─ main.py                   fábrica de app: middlewares, SSE, WS, estáticos
│  ├─ settings.py               configuración por variables de entorno
│  ├─ security.py               auth API key (multi-key, tiempo constante)
│  ├─ rate_limit.py             rate limiting por IP (ventana deslizante)
│  ├─ llm_chat.py               cliente OpenAI-compatible (Groq/OpenAI/OpenRouter/Ollama) + streaming
│  ├─ llm_prompts.py            prompts de producción v1 (traductor + narrador)
│  ├─ scenario_parser.py        intérprete determinista ES/EN (fallback sin LLM)
│  ├─ narrative.py              narrador de plantillas (traducción inversa honesta)
│  ├─ run_store.py              persistencia SQLite (WAL) + caché LRU
│  ├─ metrics.py                registro Prometheus (sin dependencias)
│  ├─ live_runner.py            runners en vivo (energy tick-a-tick, massive por chunks)
│  ├─ evaluation.py             evaluador del traductor contra golden set
│  ├─ eval_golden.json          golden set de 8 escenarios (ES/EN)
│  ├─ models/dto_ui.py          DTOs Pydantic v2 del contrato UI-NG
│  └─ routers/                  status · conversation (+stream) · simulation (+stream) · live (WS)
│
├─ frontend/                    ← aplicación React (fusionar en el repo)
│  ├─ package.json / package-lock.json / vite.config.ts / tsconfig.json / index.html
│  ├─ README_ES.md
│  └─ src/
│     ├─ App.tsx                orquestador (chat + guiado + en vivo)
│     ├─ api.ts / stream.ts     clientes HTTP y SSE
│     ├─ live.ts                cliente WebSocket
│     ├─ types.ts + types/api.generated.ts   contrato TS (generado por gen_ts_types)
│     ├─ i18n.ts / theme.css    diccionario ES/EN y sistema de diseño
│     └─ components/            StatusBar · ChatPanel · DraftEditor · GuidedForm ·
│                               ResultsPanel · LiveControls · LiveView
│
├─ tests/                       ← test_ui_ng.py (16) + test_ui_ng_live.py (8)
│
├─ infra/                       ← despliegue y CI
│  ├─ Dockerfile.ui-ng          imagen multi-stage (API + frontend compilado)
│  ├─ docker-compose.yml        servicios massive + ui-ng
│  ├─ env.example               variables de entorno (sección UI-NG)
│  ├─ scripts/gen_ts_types.py   generador de tipos TS desde Pydantic
│  └─ .github/workflows/ui-ng.yml  CI (tests + eval + contract sync + build)
│
└─ docs/                        ← NEXT_GEN_UI_WORKFLOW_ES.md +
                                  NEXT_GEN_UI_PRODUCTION_ES.md
```

---

## 3. Requisitos previos

| Componente | Requisito |
|---|---|
| Repositorio base | Checkout de MASSIVE (rama `main`, commit ≥ `ade5408`) |
| Python | 3.11+ con `pip install -r requirements.txt` |
| Node.js | 20+ con npm |
| LLM (opcional) | API key de Groq/OpenAI/OpenRouter, o un Ollama local |

**Sin API key de LLM todo funciona igual** (modo heurístico): la paridad de
UX es total por diseño.

---

## 4. Instalación (fusionar sobre el repo)

```bash
# 1. Descargar y descomprimir este paquete
unzip massive-ui-ng-package-v1.0.zip

# 2. Fusionar sobre el checkout de MASSIVE (mismas rutas relativas)
cd massive-ui-ng-package
#   backend/app/*      → <MASSIVE>/backend/app/*
#   frontend/*         → <MASSIVE>/frontend/*
#   tests/*            → <MASSIVE>/tests/*
#   infra/Dockerfile.ui-ng     → <MASSIVE>/Dockerfile.ui-ng
#   infra/docker-compose.yml   → <MASSIVE>/docker-compose.yml   (fusionar o reemplazar)
#   infra/env.example          → anexar a <MASSIVE>/.env.example
#   infra/.github/*            → <MASSIVE>/.github/*
#   infra/scripts/gen_ts_types.py → <MASSIVE>/scripts/gen_ts_types.py (reemplaza al existente)
#   docs/*            → <MASSIVE>/docs/*

# 3. Dependencias
cd <MASSIVE>
pip install -r requirements.txt httpx

cd frontend && npm ci && cd ..
```

> 💡 El `.gitignore` del repo ya ignora `frontend/dist/`, `node_modules/`,
> `data/ui_ng/` (persistencia SQLite) y artefactos de build.

---

## 5. Modos de ejecución

### 5.1 Desarrollo (dos procesos)

```bash
# Terminal 1 — backend (desde la raíz del repo)
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — frontend (Vite proxya /api, /ws, /metrics y /health al :8000)
cd frontend && npm run dev
# → http://localhost:5173
```

### 5.2 Producción (un solo servicio)

```bash
cd frontend && npm run build && cd ..
MASSIVE_SERVE_FRONTEND=1 uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
# → http://localhost:8000  (la API sirve el frontend compilado)
```

### 5.3 Docker (recomendado para producción)

```bash
docker build -f Dockerfile.ui-ng -t massive-ui-ng .
docker run -d -p 8000:8000 \
  -e PROVIDER=groq -e GROQ_API_KEY=gsk_... \
  -e MASSIVE_API_KEYS=$(openssl rand -hex 24) \
  -e MASSIVE_ALLOWED_HOSTS=tu-dominio.com \
  -e MASSIVE_TRUST_PROXY=1 \
  -v massive-data:/data \
  massive-ui-ng

# o con compose (servicio ui-ng en el puerto 8010)
docker compose up -d --build ui-ng
```

---

## 6. Configuración mínima

```bash
# LLM (opcional — sin esto la app corre en modo heurístico)
export PROVIDER=groq
export GROQ_API_KEY=gsk_...
# alternativas: PROVIDER=openai OPENAI_API_KEY=... |
#               PROVIDER=openrouter OPENROUTER_API_KEY=... |
#               PROVIDER=ollama OLLAMA_HOST=http://localhost:11434 OLLAMA_MODEL=llama3.2

# Seguridad (producción)
export MASSIVE_API_KEYS=clave1,clave2        # vacío = modo dev abierto (warning en log)
export MASSIVE_ALLOWED_HOSTS=tu-dominio.com
export MASSIVE_TRUST_PROXY=1                 # solo detrás de proxy que filtre X-Forwarded-For
```

Referencia completa de variables: `docs/NEXT_GEN_UI_PRODUCTION_ES.md` §6 y
`infra/env.example`.

---

## 7. Verificación de la instalación

```bash
# 1. Tests del backend (24 tests: REST, SSE, WS en vivo, métricas, auth, rate limit, SQLite)
python -m pytest tests/test_ui_ng.py tests/test_ui_ng_live.py -q

# 2. Evaluación del traductor (golden set, umbral 80%)
python -m backend.app.evaluation
# con LLM real:  EVAL_LLM=1 python -m backend.app.evaluation

# 3. Sincronía del contrato Pydantic ↔ TypeScript
python scripts/gen_ts_types.py && git diff --exit-code frontend/src/types/api.generated.ts

# 4. Build del frontend
cd frontend && npm run build

# 5. Salud del servicio
curl -s http://localhost:8000/health
# → {"status":"healthy","service":"MASSIVE UI-NG API",...}
```

---

## 8. Flujo completo de uso (resumen)

1. **Conversación**: el usuario describe su escenario en lenguaje natural
   ("¿Qué pasaría si lanzan una campaña agresiva y la gente desconfía de las
   instituciones?").
2. **Traducción**: el LLM (o el parser heurístico) genera un `config_draft`
   MASSIVE + **supuestos explícitos con confianza** + preguntas.
3. **Revisión humana**: chips editables en la UI; nada se ejecuta a ciegas.
4. **Simulación**: uno de los 4 motores (scalar/energy/multilayer/massive)
   con reporte científico opcional (estabilidad, EWS).
5. **Traducción inversa**: narrativa en prosa con la cadena causal
   (qué pasó → por qué), en 2 idiomas × 2 audiencias (general/técnico).
6. **Iteración o modo en vivo**: refinar la conversación, o ver la
   simulación tick a tick en el tab 🔴 En vivo (con shocks interactivos).

El detalle completo: `WORKFLOW.md` y `docs/NEXT_GEN_UI_WORKFLOW_ES.md`.
Los ejemplos de código listos para copiar: `EXAMPLES.md`.

---

## 9. Documentos incluidos

| Archivo | Contenido |
|---|---|
| `README.md` | Instrucciones de instalación y operación (este archivo) |
| `WORKFLOW.md` | Workflow general: problema, solución, arquitectura, fases |
| `EXAMPLES.md` | Ejemplos de implementación (Python, curl, WS, React, Docker, Prometheus) |
| `MANIFEST.txt` | Inventario completo de archivos |
| `docs/NEXT_GEN_UI_WORKFLOW_ES.md` | Diseño detallado del flujo del traductor |
| `docs/NEXT_GEN_UI_PRODUCTION_ES.md` | Guía de producción (seguridad, despliegue, observabilidad) |
| `frontend/README_ES.md` | Guía del frontend |

---

## 10. Estado y pendientes

✅ Implementado: traductor (LLM + heurístico), supuestos/preguntas,
narrativa bidireccional ES/EN × 2 audiencias, 4 motores, SSE, WebSocket en
vivo con shocks, persistencia SQLite, auth, rate limiting, métricas
Prometheus, Docker, CI, golden set, tipos generados.

⏳ Pendiente post-v1: dashboards Grafana, multi-tenancy por API key,
rate limiter compartido (Redis) para multi-worker, retiro gradual de
Streamlit (Fase 5).

**Licencia**: Apache 2.0 (misma que MASSIVE). Los archivos de este paquete
respetan las convenciones del repositorio (`CLAUDE.md`): cero cambios al
núcleo, fallbacks en cascada, DTOs `extra="forbid"`.
