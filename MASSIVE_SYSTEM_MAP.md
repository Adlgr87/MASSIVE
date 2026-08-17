# MASSIVE System Map — Cartógrafo del Sistema

**Versión:** 1.0  
**Fecha:** 2026-08-16  
**Estado:** Fase 0 completada

---

## 1. Diagrama textual de capas

```
┌────────────────────────────────════════════════════════──────────────────────────┐
│                            CAPA 1: INTERFAZ (UI-NG)                              │
│                                                                                   │
│  frontend/src/ (React + Vite + TypeScript)                                        │
│  ├── App.tsx              — enrutador React principal                             │
│  ├── services/api.ts      — cliente Axios (v1 + legacy endpoints)                │
│  ├── hooks/useApi.ts      — hooks React para consume de API                       │
│  ├── types/api.generated.ts — DTOs TypeScript (generados desde backend)          │
│  ├── MASSIVE_UIL_demo.jsx — demo monolítica de la UI UIL                           │
│  └── micro_ui.py          — Streamlit UI para micro-MASSIVE (multi-agente)        │
│                                                                                   │
│  nginx (en Docker): sirve /usr/share/nginx/html + proxy reversa                   │
│    / → frontend SPA                                                               │
│    /api/ → FastAPI gateway (backend/app/main.py o api.py)                         │
│    /ui/ → Streamlit (micro_ui.py)                                                 │
└────────────────────────────────────────────────────────┬──────────────────────────┘
                                                         │
┌────────────────────────────────────────────────────────▼──────────────────────────┐
│                            CAPA 2: API / GATEWAY (Backend)                        │
│                                                                                   │
│  backend/app/main.py      — FastAPI entrypoint (versión /v1, auth, CORS)          │
│  ├── routers/                                                          │
│  │   ├── sim.py (POST /v1/simulate)             → services.simulation_service      │
│  │   ├── engine.py (POST /v1/engine/energy, /architect) → energy_runner / social_arch │
│  │   ├── forecast.py (POST /v1/forecast)        → forecast.engine.forecast          │
│  │   └── benchmark.py (POST /v1/benchmarks)     → benchmarks.runner.main            │
│  ├── models/             — DTOs Pydantic v2 (extra="forbid")                  │
│  │   ├── dto_simulation.py, dto_forecast.py, dto_architect.py, dto_snapshot.py      │
│  ├── security.py         — API key validation + rate limiting                     │
│  └── settings.py         — configuración de entorno                               │
│                                                                                   │
│  api.py                   — FastAPI legacy entrypoint (compat bridge)              │
│                          endpoints: /api/extract, /api/wizard, /api/simulate-uil    │
└────────────────────────────────────────────────────────┬──────────────────────────┘
                                                         │
┌────────────────────────────────────────────────────────▼──────────────────────────┐
│                            CAPA 3: SERVICIOS                                      │
│                                                                                   │
│  services/                              — capa delgada de orquestación              │
│  ├── simulation_service.py             → run_scalar_simulation, run_multilayer_*,   │
│  │                                       run_massive_sim                           │
│  ├── forecast_service.py               → baseline_forecast, walk_forward_evaluate   │
│  ├── factbook_service.py               → country_params, intervention_constraints,  │
│  │                                       build_engine_from_country                   │
│  ├── llm_service.py                    → wizard_config, resolve_llm_credentials      │
│  └── simulation_service.__init__       → re-exporta funciones clave                  │
└────────────────────────────────────────────────────────┬──────────────────────────┘
                                                         │
┌────────────────────────────────────────────────────────▼──────────────────────────┐
│                    CAPA 4: NÚCLEO CIENTÍFICO (massive_core/ + módulos raíz)       │
│                                                                                   │
│  massive_core/                          — adaptador científico canónico             │
│  ├─ contracts.py                        → SimulationState, SimulationResult,          │
│  │                                          EngineProtocol, legacy adapters         │
│  ├─ scientific_runner.py               → run_scientific_simulation,                 │
│  │                                          run_energy_scientific_simulation,        │
│  │                                          run_multilayer_scientific_simulation     │
│  ├─ config/                                                               │
│  │   ├── scientific.py (ScientificRuntimeConfig)                              │
│  │   ├── settings.py (AppSettings)                                            │
│  │   └── defaults.yaml                                                      │
│  ├─ numerics/      — solvers, steppers, stability, sparse multilayer         │
│  ├─ physics/       — hydrodynamics, perturbation_theory, statistical_mechanics │
│  ├─ dynamical_systems/ — bifurcación                                          │
│  ├─ data_assimilation/ — Kalman, workflow (EnKF)                               │
│  ├─ diagnostics/   — ScientificReport, report builder                          │
│  ├─ metalearning/  — CFC training, regime selector                             │
│  ├─ multiscale/    — hierarchical time                                       │
│  ├─ network_inference/ — reconstruct                                        │
│  ├─ neural_physics/ — PINNs                                                   │
│  ├─ analysis/, benchmarks/                                                   │
│  └─ utils/rng.py                                                            │
│                                                                                   │
│  Módulos raíz (engines de simulación)                                          │
│  ├── simulator.py           — núcleo legacy (simular, resumen_historial)          │
│  ├── multilayer_engine.py   — dinámica Langevin multicapa (5D state vector)       │
│  ├── massive_engine.py      — LOD super-agentes, uint8, event-driven, GPU         │
│  ├── energy_engine.py       — SocialEnergyEngine (Langevin 1D + Numba JIT)          │
│  ├── micro_engine.py        — micro-MASSIVE (grupos pequeños)                     │
│  ├── micro_schemas.py       — GroupProfile, MemberProfile (micro)                 │
│  ├── cfc_engine.py          — contrafactual científico                             │
│  ├───────────────────────────────────────────────────────────────────────────────│
│  │  social_architect.py — agente LLM inverso (buscar_estrategia_inversa)           │
│  ├── energy_runner.py       — orquesta ProgrammaticArchitect → EnergyConfig →    │
│  │                             SocialEnergyEngine                                 │
│  ├── programmatic_architect.py — paisaje energético (LangChain + LLM)            │
│  ├── forecast/                — motor temporal (analytical + Monte Carlo)         │
│  │   ├── engine.py → forecast() → ForecastResult                                 │
│  │   ├── temporal_config.py → TemporalConfig                                     │
│  │   ├── scenarios.py, targets.py → targets de validación                        │
│  ├── schemas.py              — StrategyMatrix, etc. (validación social)           │
│  ├── intervention_optimizer.py                                                    │
│  └── empirical_config.py / empirical_calibration.py                               │
└────────────────────────────────────────────────────────┬──────────────────────────┘
                                                         │
┌────────────────────────────────────────────────────────▼──────────────────────────┐
│                    CAPA 5: DATOS                                                 │
│                                                                                   │
│  data/factbook/                                                                   │
│  ├── factbook_sample.json     — 3 países (US, China, Germany)                     │
│  └── factbook_test.json                                                      │
│                                                                                   │
│  massive/core/factbook/                                                           │
│  ├── context.py     — FactbookContext, CountryData (5 puntos de integración)      │
│  ├── mappings.py    — COUNTRY_CODES (17 países), DEMOGRAPHIC/ECONOMIC/SOCIAL      │
│  │                    FIELDS, FACTBOOK_TO_MASSIVE transformaciones               │
│  ├── loader.py      — cargador JSON                                              │
│  └── validator.py   — validación de datos                                         │
│                                                                                   │
│  datasets/                                                                      │
│  ├── pvu_cases/      — casos reales para benchmarks                            │
│  └── real_cases/     — casos de validación                                     │
│                                                                                   │
│  configs/                                                                         │
│  ├── multilayer.yaml — configuración del motor multicapa                          │
│  └── pvu.yaml        — parámetros PVU-BS                                          │
│                                                                                   │
│  reports/                                                                         │
│  ├── factbook_validation_US_2026-08-13.json — validación empírica                 │
│  ├── factbook_validation_US_2026-06-26.json                                       │
│  ├── enkf_*/          — resultados EnKF                                          │
│  └── validation/                                                                 │
└────────────────────────────────────────────────────────┬──────────────────────────┘
                                                         │
┌────────────────────────────────────────────────────────▼──────────────────────────┐
│                    CAPA 6: INFRAESTRUCTURA                                       │
│                                                                                   │
│  Docker (multi-stage)                                                             │
│  ├── Dockerfile (3 stages: builder-py → builder-fe → runtime)                     │
│  ├── Dockerfile.optimized                                                          │
│  ├── docker-compose.yml    (80 nginx, 8000 API, 8501 Streamlit)                    │
│  ├── docker-compose.single.yml                                                    │
│  ├── nginx.conf      — SPA try_files + proxy reversa                              │
│  └── supervisord.conf — api (appuser) + streamlit (appuser) + nginx (root)        │
│                                                                                   │
│  CI/CD (.github/workflows/)                                                        │
│  ├── lint.yml, frontend-build.yml, benchmark.yml, publish.yml                    │
│                                                                                   │
│  Packaging                                                                       │
│  ├── pyproject.toml     — entry: massive-cli, install.sh, deps, extras            │
│  ├── requirements.txt   — versión plana (CI)                                      │
│  ├── install.sh         — install, run, docker, test, benchmark, docs, clean      │
│  └── mkdocs.yml                                                                   │
│                                                                                   │
│  Rust core                                                                    │
│  ├── rust_core/src/  — aceleración numérica (active_mask_step)                    │
│  └── massive_core/rust_core.py — wrapper FFI                                      │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Flujos de trabajo principales

### 2.1. Flujo estratégico (Social Architect — inverso)

```
Usuario → UI-NG → POST /v1/engine/architect
  ↓
payload: { estado_inicial, objetivo_usuario, max_intentos, modo_simulacion }
  ↓
social_architect.buscar_estrategia_inversa()
  ├── LLM (OpenAI/Groq/OpenRouter) ←→ programmatic_architect.get_landscape()
  ├── simulator.simular()          ← simulaciones candidato (modo "macro")
  ├── multilayer_engine.step()     ← simulaciones multicapa (modo "corporativo")
  ├── cfc_engine.py                ← cálculo contrafactual (si disponible)
  └── intervention_optimizer.py    ← optimización de intervenciones
  ↓
respuesta: { strategy, narrative, attempts, history_summary, history_length }
  ↓
UI-NG muestra: narrativa, pasos de intervención, simulaciones candidato
```

**Propósito:** Dada un estado inicial y un objetivo en lenguaje natural, el LLM busca iterativamente (máximo `max_intentos`) la secuencia de intervenciones que lleva la red al estado objetivo.

---

### 2.2. Flujo científico (Langevin energy landscape)

```
Usuario → UI-NG → POST /v1/engine/energy
  ↓
payload: { user_goal, n_agents, steps, connectivity, range_type, seed }
  ↓
energy_runner.run_energy_simulation()
  ├── programmatic_architect.get_landscape(user_goal)
  │     ├── LLM (Groq/OpenAI/OpenRouter) → paisaje energético
  │     └── social_architect.setup_client() (lazy)
  ├── energy_schemas.EnergyConfig.model_validate() → validación
  └── energy_engine.SocialEnergyEngine
        ├── Langevin discreta JIT (Numba): x_i(t+η) = x_i - η∇U + ηλ(x̄_nb - x_i) + √(2ηT)ε
        ├── attractores/repulsores gaussianos
        └── system_metrics() (polarización, consenso, etc.)
  ↓
respuesta: { history, metrics_timeline, final_state, summary, config_used, archetype_info }
  ↓
UI-NG muestra: evolución temporal de opiniones, distribución final, polarización
```

**Propósito:** Simular dinámica de opinión bajo un paisaje de energía definido por el LLM (atractores/repulsores) sobre una red social con ruido Langevin.

---

### 2.3. Flujo de simulación legacy (scalar simular)

```
Usuario → UI-NG → POST /v1/simulate
  ↓
payload: { estado_inicial, escenario, pasos, config, verbose }
  ↓
services.simulation_service.run_scalar_simulation()
  ├── simulator.simular(estado, escenario, pasos, config)
  │     ├── reglas heurísticas (campana, bimodal, etc.)
  │     ├── Redes: watts_strogatz, barabasi_albert, erdos_renyi
  │     ├── LLM (opcional, cada N pasos)
  │     └── historial de dicts [{_paso, opinion, propaganda, ...}]
  └── simulator.resumen_historial(history, config)
  ↓
respuesta: { history, summary, config, escenario }
  ↓
UI-NG muestra: línea de tiempo de opiniones, métricas de consenso
```

**Propósito:** Simulación escalar legacy de dinámica de opiniones (unipolar/bipolar) sobre redes sociales con actualización heurística o LLM.

---

### 2.4. Flujo de Forecast (pronóstico temporal)

```
Usuario/servicio → POST /v1/forecast
  ↓
payload: { simulation_state, temporal_config, mode, n_runs }
  ↓
forecast.engine.forecast()
  ├── Modo "analytical":
  │     ├── extrae EWS (variance, autocorr, skewness)
  │     ├── score = β₀ + β₁·var + β₂·autocorr + β₃·skew
  │     ├── p_event = sigmoid(score)
  │     └── estima steps_to_event / days_to_event por velocidad de tendencia
  └── Modo "monte_carlo":
        ├── N simulaciones estocásticas (drift + ruido)
        ├── Wilson CI para p_event
        └── mediana de steps hasta evento
  ↓
respuesta (ForecastResponse DTO):
  { sim_id, horizon_ticks, points: [{tick, mean_opinion, polarization, ci_low, ci_high}],
    feasibility: {score, label, rationale} }
  ↓
UI-NG muestra: pronóstico de riesgo, banda de confianza, horizonte temporal
```

**Propósito:** Proyectar estados futuros y estimar la probabilidad de un evento umbral (polarización excesiva, viralización, etc.) con intervalos de confianza.

---

### 2.5. Flujo Factbook (contexto de país)

```
Usuario → POST /v1/simulate o POST /v1/engine/energy
  (con parámetro de país: "US", "United States", iso2, iso3)
  ↓
services.factbook_service
  ├── country_params(country) 
  │     ├── FactbookContext.get_massive_params(country)
  │     └── devuelve: n_agents, demographic_matrix, social_groups,
  │                   social_pressure_weights, gini_coefficient,
  │                   economic_potential, cost_scale_factor, fiscal_constraint,
  │                   sector_multipliers, urban_rural_split, health_index
  ├── intervention_constraints(country)
  │     └── devuelve: cost_scale_factor, fiscal_constraint, sector_multipliers
  └── build_engine_from_country(country)
        └── MassiveEngine.from_factbook(country, context, ...)
  ↓
Engine configurado con datos reales del país
  ↓
Validación: reports/factbook_validation_*.json
  ├── 6 métricas comparadas: Population, GDP per Capita, Gini Index,
  │   Unemployment Rate, Ethnic Diversity, Religious Diversity
  ├── scores: 0-100 por métrica
  └── overall_score + passing_percentage
```

**5 puntos de integración Factbook:**
1. **Inicialización de agentes** — Population → n_agents, age_structure → demographic_matrix
2. **Social pressure** — Ethnic/Religious/Language groups → social_pressure_weights (Herfindahl)
3. **Energy engine** — Gini index → gini_coefficient/inequality_factor, income_distribution → economic_potential
4. **Intervention optimizer** — GDP per capita → cost_scale_factor, budget → fiscal_constraint, sectors → sector_multipliers
5. **Validación** — comparación directa de métricas simuladas vs. reales

---

### 2.6. Flujo de benchmarks (PVU-BS)

```
CLI: python -m benchmarks.runner --cases datasets/pvu_cases --offline|--real|--llm
  o  POST /v1/benchmarks (modo offline/real/llm)
  ↓
benchmarks/runner.py
  ├── benchmarks/io.py: load_cases() → carga casos PVU
  ├── Para cada caso:
  │     ├── train/test split (70/30)
  │     ├── mode "offline": _massive_offline_forecast() → AR(1) + damped noise proxy
  │     ├── mode "real": _massive_real_forecast() → simulator.simular() con calibración
  │     └── mode "llm": _massive_llm_forecast() → LLM-backed (requiere API key)
  │   ├── benchmarks/baselines.py: get_all_baselines() → AR1, Naive, Mean, Drift, Seasonal
  │   ├── benchmarks/metrics.py: MAE, RMSE, MAPE, Dir. Acc., Diebold-Mariano, Holm-Bonferroni
  │   ├── benchmarks/turning_points.py: detección de puntos de inflexión
  │   └── benchmarks/walk_forward.py: validación walk-forward
  ↓
reports/validation/ci/
  ├── metrics.json  — resultados completos por caso
  └── report.md     — reporte Markdown resumen

Validación: experiments/TEST_SUMMARY.md, MASSIVE_BENCHMARK_REPORT.md
```

**Propósito:** Validar el motor MASSIVE contra 12 casos reales de puntos de inflexión políticos (PVU) usando múltiples baselines y tests estadísticos.

---

## 3. Relación entre backend FastAPI, UI-NG y motores de simulación

### Arquitectura de comunicación

```
                    ┌──────────────────────────────────────────────┐
                    │           UI-NG (frontend/src/)              │
                    │  React + Vite + TypeScript + TailwindCSS     │
                    │                                              │
                    │  Axios client (services/api.ts)              │
                    └─────────────┬────────────────────────┬───────┘
                                  │                        │
                              HTTP POST                  WebSocket*
                                  │                        │
                                  ▼                        │
                    ┌──────────────────────────────────────┴───────┐
                    │  FastAPI Backend (backend/app/main.py)       │
                    │  Auth: X-API-Key (fail-closed)               │
                    │  Rate limit: 60/min/IP                       │
                    │                                              │
                    │  /v1/simulate    → simulation_service         │
                    │  /v1/engine/*    → energy_runner / social_arch  │
                    │  /v1/forecast    → forecast_service / engine    │
                    │  /v1/benchmarks  → benchmarks.runner             │
                    │  /api/*         → legacy api.py compat (extract,│
                    │                   wizard, simulate-uil)        │
                    └──────────────────────┬─────────────────────────┘
                                           │
                    ┌──────────────────────┴─────────────────────────┐
                    │  Service Layer (services/)                     │
                    │  Orquestación delgada + adaptación de DTOs     │
                    └──────┬──────────┬──────────────┬───────────────┘
                           │          │              │
                    ┌──────▼──┐  ┌───▼────┐   ┌─────▼────────┐
                    │ Legacy  │  │ Energy │   │ Forecast     │
                    │ simul.  │  │ Engine │   │ Engine       │
                    │ simula- │  │Langevin│   │(analytical   │
                    │ tor.py  │  │ +NumB  │   │ +MC)         │
                    └─────────┘  └────────┘  └──────────────┘

                    ┌──────────────────────────────────────────────┐
                    │  Núcleo científico: massive_core/              │
                    │  Contracts, numerics, diagnostics              │
                    └──────────────────────────────────────────────┘

                    ┌──────────────────────────────────────────────┐
                    │  Factbook integration                        │
                    │  massive/core/factbook/ → 5 puntos            │
                    └──────────────────────────────────────────────┘

                    ┌──────────────────────────────────────────────┐
                    │  Micro-MASSIVE (multi-agente)                │
                    │  micro_massive/core/ → orchestrator, agent   │
                    │  micro_engine.py, micro_schemas.py           │
                    └──────────────────────────────────────────────┘

                    ┌──────────────────────────────────────────────┐
                    │  Streamlit UI (micro_ui.py)                  │
                    │  Tablas interactivas, futuros posibles       │
                    └──────────────────────────────────────────────┘
```

### Matriz de responsabilidades

| Capa | FastAPI Backend | UI-NG Frontend | Motores de simulación |
|------|-----------------|-----------------|-----------------------|
| **Routing** | `/v1/*` versionados, `/api/*` legacy | `/api/v1/*` via Axios | N/A |
| **Auth** | API key (X-API-Key), rate-limit | Envia header, maneja 401/429 | N/A |
| **Validación de entrada** | dict payload + type coercion | Typescript types (generados) | N/A |
| **Validación de salida** | DTOs Pydantic (`backend/app/models/`) | Typescript DTOs (`types/api.generated.ts`) | ScientificReport, ForecastResult |
| **Orquestación** | routers → services | hooks/useApi, services/api | N/A |
| **Simulación** | services.* → engine | N/A | `simulator.py`, `multilayer_engine.py`, `energy_engine.py`, `massive_engine.py`, `micro_engine.py` |
| **LLM** | `social_architect.py`, `programmatic_architect.py` | N/A | social_architect.llm_client |
| **Factbook** | `factbook_service.py` | N/A | `massive/core/factbook/` |
| **Forecast** | `forecast_service.py` → `forecast.engine.forecast()` | ForecastResponse DTO | `forecast/engine.py` |
| **Reporte científico** | `scientific_runner.py` | N/A | `massive_core/diagnostics/` |
| **Benchmark** | `benchmarks/runner.py` | N/A | `benchmarks/` |

### DTOs compartidos (contrato frontend-backend)

```
backend/app/models/ (Pydantic v2, extra="forbid")
  ├── dto_simulation.py  → SimSnapshotMessage (WebSocket), SimEventMessage
  ├── dto_forecast.py    → ForecastPoint, Feasibility, ForecastResponse
  ├── dto_architect.py   → InterventionRecord, InterventionLogEntry, ArchitectEventMessage
  └── dto_snapshot.py    → SnapshotRecord, TimelineTick, TimelineResponse

frontend/src/types/api.generated.ts (generado desde DTOs)
  └── Script: python scripts/gen_ts_types.py
```

---

## 4. Micro-MASSIVE (sistema multi-agente)

```
micro_massive/                  — agente multi-partícula ligero
  core/
  ├── agent.py       → SocialParticle (mood, energy, 2D position, strategy)
  ├── game.py        → EvolutionaryGame (juego evolutivo, 3 pasos)
  ├── influence.py   → InfluenceMatrix (matriz de influencia)
  └── orchestrator.py → MicroOrchestrator (coordina influence+game+metrics)
  utils/
  ├── forer.py       → generación de perfiles para "para todos"
  └── metrics.py     → GroupMetrics (cohesión, presión, diversidad)

micro_ui.py          — Streamlit UI interactiva para familias de futuros
micro_schemas.py     → GroupProfile, MemberProfile (DTOs)
micro_engine.py      → analyze_group() (ensemble + clustering de futuros)
```

**Workflow micro-MASSIVE:**
1. Usuario configura perfil grupal (n miembros, contexto, sliders de cohesión/presión/diversidad)
2. `analyze_group()` ejecuta N simulaciones con variación de parámetros
3. Clasificación en "familias de futuros" (clusters)
4. Identificación de parámetros determinantes (qué predictores dicen qué familia)

**Contraste con macro-MASSIVE:**
- **macro:** 1 simulación, N=10K-1M agentes, 1 resultado a largo plazo
- **micro:** N=200 simulaciones paralelas, grupos de 3-15 agentes, familias de futuros

---

## 5. Infraestructura: Docker + CI/CD

### Stack Docker Compose (docker-compose.yml)

| Servicio | Puerto | Imagen Base | Rol |
|----------|--------|-------------|-----|
| nginx | 80 | python:3.11-slim | Frontend SPA + proxy reversa |
| api | 8000 | (build /v3 runtime) | FastAPI backend |
| streamlit | 8501 | (runtime) | UI micro-MASSIVE |

### Multi-stage Dockerfile

```dockerfile
# Stage 1: builder-py (wheels cacheados)
python:3.11-slim → pip wheel -r requirements.txt → /wheels

# Stage 2: builder-fe (frontend estático)
node:20-alpine → npm ci + npm run build → /src/dist → /usr/share/nginx/html

# Stage 3: runtime (slim + nginx + supervisor)
python:3.11-slim → pip install --no-index (from /wheels) → supervisord
```

### Health checks
- `GET /health` — liveness (200 si el servicio responde)
- `GET /ready` — readiness (503 si no hay LLM key o el adapter falla)
- `GET /version` — metadata de build

---

## 6. Resumen de endpoints API

### v1 endpoints (backend/app/main.py → routers/)

| Método | Endpoint | Router | Engine/Serivce | Auth |
|--------|----------|--------|----------------|------|
| POST | `/v1/simulate` | sim.py | simulation_service.run_scalar_simulation | X-API-Key |
| POST | `/v1/engine/energy` | engine.py | energy_runner.run_energy_simulation | X-API-Key |
| POST | `/v1/engine/architect` | engine.py | social_architect.buscar_estrategia_inversa | X-API-Key |
| POST | `/v1/forecast` | forecast.py | forecast.engine.forecast | X-API-Key |
| POST | `/v1/benchmarks` | benchmark.py | benchmarks.runner.main | X-API-Key |

### Legacy endpoints (api.py)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/extract` | Subir documento → extraer config |
| POST | `/api/wizard` | NL description → config dict |
| POST | `/api/simulate-uil` | Pipeline completo UIL demo |
| GET | `/health`, `/ready`, `/version` | Infra |

---

## 7. Dependencias externas (llaves)

| Servicio | Variable de entorno | Uso |
|----------|---------------------|-----|
| Groq | `GROQ_API_KEY` | LLM Social Architect, Energy Landscape |
| OpenAI | `OPENAI_API_KEY` | Alternativa LLM |
| OpenRouter | `OPENROUTER_API_KEY` | Alternativa LLM (benchmark LLM mode) |
| CIA Factbook | `data/factbook/factbook_sample.json` | Contexto de país (5 puntos) |

---

## 8. Tests (453 tests documentados)

```
tests/
├── test_api_security.py         — auth, rate-limit, errores 400/500
├── test_cfc_engine.py           — motor contrafactual
├── test_cfc_router.py           — router CfC
├── test_contracts.py            — SimulationState, SimulationResult, adapters
├── test_dto_models.py           — validación DTOs Pydantic
├── test_empirical_calibration.py
├── test_empirical_integration.py
├── test_energy_core.py          — energy_engine + runner
├── test_engine_reproducibility.py
├── test_factbook_integration.py — 5 puntos Factbook
├── test_fidelity.py             — benchmarks.fidelity
├── test_forecast.py             — forecast.engine (analytical + MC)
├── test_game_theory.py
├── test_integrated_dynamics.py
├── test_integration_llm.py      — con mocks de LLM
├── test_mamba_engine.py
├── test_massive_engine.py
├── test_micro.py                — micro_massive/orchestrator
├── test_multilayer.py           — multilayer_engine
├── test_opt_phase2-5*.py        — fases de optimización
├── test_optimization.py
├── test_pvu_runner.py           — pipeline benchmarks
├── test_rng_reproducibility.py
├── test_runner_wiring.py
├── test_rust_core_wrapper.py
├── test_scientific_*.py         — runner + reportes
├── test_services_layer.py       — simulation_service
├── test_simulator.py
├── test_social_architect.py
├── test_sparse_refactor.py
├── test_uil_mappings.py
├── test_visualizations.py
└── test_workflow_closeout.py
```

**Comando de test:** `PYTHONHASHSEED=42 python -m pytest tests/ -q --tb=short`
**Benchmark:** `python -m benchmarks.runner --offline|--real|--llm`

---

*Generado por Cartógrafo del Sistema — Fase 0*
*Contexto del informe previo integrado.*
