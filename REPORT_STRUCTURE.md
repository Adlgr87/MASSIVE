# MASSIVE - Estructura de Archivos

> ⚠️ HISTÓRICO — describe el commit 2b70984 del 14 de septiembre de 2026. No refleja main actual.

> Informe generado automáticamente por análisis estructural del repositorio.
> Fecha: 2026-09-14 | Path: `/home/adlg/Escritorio/Proyectos/MASSIVE`

---

## Resumen

| Métrica | Valor |
|---|---|
| Total archivos Python (proyecto, excl. `.venv`) | **246** |
| Archivos de test | **59** |
| Módulos principales (root-level engines) | **7** |
| Routers API v1 | **5** |
| Endpoints API v1 (implementados) | **8** |
| Endpoints legacy `/api/*` (deprecated) | **3** |
| Scripts de respaldo (/backup) | **5** |
| Servicios de orquestación | **5** |
| DTOs Pydantic v2 | **5** archivos, ~25 clases |

---

## Mapa de Directorios

```
MASSIVE/
│
├── backend/                          # FastAPI production entrypoint
│   └── app/
│       ├── main.py                   # FastAPI app — incluye routers /v1/* + compat /api/v1/*
│       ├── metrics.py                # Prometheus registry (http_requests_total, etc.)
│       ├── security.py               # get_api_key (hmac constant-time) + rate limiter
│       ├── settings.py               # Typed settings (pydantic BaseSettings)
│       ├── models/                   # Pydantic v2 DTOs (extra="forbid")
│       │   ├── __init__.py           # Namespace re-export
│       │   ├── dto_simulation.py     # SimAgentLite, SimSnapshotMessage, SimMode, etc.
│       │   ├── dto_forecast.py       # ForecastPoint, Feasibility, ForecastResponse
│       │   ├── dto_architect.py      # InterventionRecord, InterventionLogEntry, ArchitectEventMessage
│       │   ├── dto_snapshot.py       # SnapshotRecord, TimelineTick, TimelineResponse
│       │   └── dto_llm.py            # LLMRunRequest/Response, LLMWizardRequest/Response, etc.
│       └── routers/                  # API endpoint modules
│           ├── sim.py                # POST /v1/simulate
│           ├── forecast.py           # POST /v1/forecast
│           ├── engine.py             # POST /v1/engine/energy, POST /v1/engine/architect
│           ├── llm.py                # POST /v1/llm/run_simulation, /wizard, /extract
│           ├── benchmark.py          # POST /v1/benchmarks
│           └── __init__.py
│
├── massive_core/                     # Scientific opt-in layer
│   ├── config/                       # API auth, rate limit, logging, settings, scientific
│   │   ├── api_auth.py               # get_api_key implementation (hmac.compare_digest)
│   │   ├── rate_limit.py             # RateLimitMiddleware
│   │   ├── logging_setup.py          # Structured logging
│   │   ├── settings.py               # AppSettings (pydantic)
│   │   └── scientific.py             # Scientific config flags
│   ├── data_assimilation/            # Ensemble Kalman Filter
│   │   ├── kalman.py                 # SparseEnsembleKalmanFilter
│   │   └── workflow.py               # Data assimilation pipeline
│   ├── benchmarks/                   # Canonical benchmark suite
│   ├── diagnostics/                  # Report generation
│   ├── dynamical_systems/            # Bifurcation analysis
│   ├── metalearning/                 # CfC regime selector + training data
│   ├── multiscale/                   # Hierarchical time scaling
│   ├── network_inference/            # Graph reconstruction
│   ├── neural_physics/               # PINNs
│   ├── numerics/                     # MultilayerEngine sparse, solvers, stability, steppers
│   ├── physics/                      # Hydrodynamics, perturbation theory, stat mech
│   ├── utils/                        # RNG helpers, serialization
│   ├── contracts.py                  # LLM contract validation
│   ├── rust_core.py                  # PyO3 Rust kernel wrapper
│   └── scientific_runner.py          # Scientific opt-in simulation runner
│
├── massive/                          # CLI + core module namespace
│   ├── __init__.py
│   ├── cli/                          # Click CLI entrypoint
│   │   ├── main.py                   # massive-cli commands: simulate, scientific, benchmark, forecast, version, serve
│   │   ├── __main__.py
│   │   └── __init__.py
│   └── core/                         # Legacy core modules (duplicates of root-level)
│       ├── empirical_calibration.py
│       ├── empirical_config.py
│       ├── extended_models.py
│       ├── intervention_optimizer.py
│       ├── llm_credentials.py
│       ├── schemas.py
│       ├── state_compression.py
│       ├── utility_logic.py
│       ├── factbook/                 # Factbook data layer
│       │   ├── context.py
│       │   ├── loader.py
│       │   ├── mappings.py
│       │   └── validator.py
│       └── utils/                    # RNG, serialization
│
├── services/                         # Thin service layer over core engines
│   ├── __init__.py                   # Re-exports: run_scalar_simulation, run_multilayer_simulation,
│   │                                  #   run_massive_sim, run_llm_simulation, factbook_service,
│   │                                  #   forecast_service, llm_service
│   ├── simulation_service.py         # run_scalar_simulation, run_multilayer_simulation, run_massive_sim
│   ├── forecast_service.py           # baseline_forecast, walk_forward_evaluate
│   ├── llm_service.py                # wizard_config, extract_config
│   ├── llm_orchestrator.py           # classify_motor, run_llm_simulation (NL → engine dispatch)
│   └── factbook_service.py           # Factbook augmentation for country-specific params
│
├── forecast/                         # Temporal risk forecasting engine
│   ├── engine.py                     # forecast() → ForecastResult (analytical + MC)
│   ├── temporal_config.py            # TemporalConfig (pydantic)
│   ├── scenarios.py                  # Scenario definitions
│   ├── targets.py                    # Event target definitions
│   └── intervention_map.py           # Intervention-to-effect mapping
│
├── benchmarks/                       # PVU-BS benchmark suite
│   ├── runner.py                     # main() — CLI + programmatic entry
│   ├── baselines.py                  # Baseline models
│   ├── fidelity.py                   # Fidelity checks
│   ├── metrics.py                    # Benchmark metrics
│   ├── io.py                         # I/O utilities
│   ├── massive_real.py               # Real-case benchmarks
│   ├── turning_points.py             # Turning point detection
│   ├── walk_forward.py               # Walk-forward evaluation
│   ├── bench_perf_f.py               # Performance benchmark functions
│   └── butterfly_diagnostic.py       # Butterfly effect diagnostics
│
├── tests/                            # pytest test suite (59 archivos)
│   ├── __init__.py
│   ├── test_simulator.py             # simulator.py tests
│   ├── test_energy_engine.py         # energy_engine.py tests
│   ├── test_massive_engine.py        # massive_engine.py tests
│   ├── test_multilayer.py            # multilayer_engine.py tests
│   ├── test_micro.py                 # micro_engine.py tests
│   ├── test_social_architect.py      # social_architect.py tests
│   ├── test_forecast.py              # forecast engine tests
│   ├── test_cfc_*.py                 # CfC engine/router/trainer tests
│   ├── test_llm_*.py                 # LLM integration tests
│   ├── test_scientific_*.py          # Scientific runner tests
│   ├── test_brexit_calibration.py     # Brexit 2016 calibration
│   ├── test_api_security.py           # Auth + rate-limit tests
│   ├── test_backend_observability.py  # Metrics + middleware tests
│   ├── test_dto_models.py            # Pydantic DTO validation tests
│   └── ... (59 total)
│
├── scripts/                          # DevOps & utility scripts
│   ├── backup_factbook.sh            # Backup Factbook data
│   ├── backup_models.sh              # Backup ML models
│   ├── backup_simulations.sh         # Backup simulation results
│   ├── verify_backup.sh              # Integrity verification
│   ├── security_audit.sh             # Security audit helper
│   ├── gen_ts_types.py               # Generate TypeScript types from Python DTOs
│   ├── profile_hotspot.py            # Performance profiling
│   ├── todo_triage.py                # Issue triage automation
│   └── typecheck_slice.py            # Partial mypy type-checking
│
├── experiments/                      # One-off experiment scripts
│   ├── 00_smoke/run_smoke_tests.py
│   ├── 01_unit/run_invariant_tests.py
│   ├── 02_parameter_sweep/run_parameter_sweep.py
│   ├── 03_calibration/run_calibration.py
│   ├── 04_benchmark/run_pvu_benchmark.py
│   ├── 05_reproducibility/run_reproducibility.py
│   ├── 08_enkf_delta/exp_003_enkf.py
│   └── real_validation/generate_real_cases.py
│
├── adapters/                         # External adapter layer
│   └── mutalambda/
│       ├── __init__.py
│       └── massive_target.py         # MutualLambda integration
│
├── massive-ui-ng/                    # Separate next-gen UI kit (not in root CI)
│   ├── backend/app/
│   │   ├── main.py                   # Standalone FastAPI for UI-NG
│   │   ├── routers/                  # simulation, live, conversation, status
│   │   ├── models/                   # DTOs (subset of main backend)
│   │   ├── security.py
│   │   ├── settings.py
│   │   ├── metrics.py
│   │   ├── scenario_parser.py
│   │   ├── narrative.py
│   │   ├── evaluation.py
│   │   ├── run_store.py
│   │   ├── rate_limit.py
│   │   ├── llm_chat.py
│   │   └── llm_prompts.py
│   ├── tests/
│   │   ├── test_ui_ng.py
│   │   └── test_ui_ng_live.py
│   └── infra/scripts/gen_ts_types.py
│
├── frontend/                         # React 18 + Vite + TypeScript SPA
│   ├── src/
│   ├── dist → ../massive-ui-ng/frontend/dist   (symlink)
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── configs/                          # Configuration files
│   ├── llm_contract/                 # MASSIVE-LLM contract v1.1.0
│   │   └── massive_llm_contract.json
│   ├── multilayer.yaml               # Multilayer engine defaults
│   └── pvu.yaml                      # PVU benchmark config
│
├── datasets/                         # Validation datasets
│   ├── pvu_cases/                    # Pre-registered offline cases
│   └── real_cases/                   # Real-world validation cases
│
├── models/                           # Trained ML model artifacts
│   └── cfc_calibrated/              # CfC residual corrector weights
│
├── metrics/                          # Unified metrics utilities
│   ├── __init__.py
│   └── unified_metrics.py
│
├── docs/                             # Documentation
│   ├── api.md                        # API reference (v1 endpoints)
│   ├── LLM_PROMPTS.md                # LLM prompt templates
│   ├── MASSIVE_LLM_INTERFACE.md      # Full LLM interface docs
│   ├── OBSERVABILITY_AND_SECURITY.md # Security + observability guide
│   ├── FACTBOOK_*.md                 # Factbook integration docs
│   ├── DOCKER.md                     # Docker deployment guide
│   ├── ENV_VARS.md                   # Environment variables reference
│   ├── performance_report.md         # Performance benchmark results
│   ├── production-readiness-audit.md # Production readiness assessment
│   ├── backup_restore.md             # Backup/restore procedures
│   ├── disaster_recovery_plan.md     # DR plan
│   └── architecture/                 # Architecture decision records
│
├── .github/workflows/                # CI/CD pipelines (13 workflows)
│   ├── lint.yml                      # ruff + black + isort + mypy
│   ├── pytest.yml                    # Test suite
│   ├── benchmark.yml                 # PVU-BS benchmark (offline/LLM)
│   ├── frontend-build.yml            # Vite build + type check
│   ├── publish.yml                   # PyPI + GHCR publish
│   ├── docker-e2e.yml                # Docker compose E2E
│   ├── secret_scan.yml               # gitleaks
│   └── ...
│
├── micro_massive/                    # Micro-simulation engine (small groups)
│   ├── core/                         # Agent, game, influence, orchestrator
│   └── utils/                        # Metrics, forer
│
├── rust_core/                        # Optional PyO3 Rust kernels (PoC)
│   ├── Cargo.toml
│   └── src/lib.rs
│
├── app/                              # (Empty — placeholder)
│
├── ─── Root-level engine modules ───
│   simulator.py                      # simular(), DEFAULT_CONFIG, resumen_historial
│   massive_engine.py                 # MassiveSimEngine (LOD super-agent, 100M scale)
│   multilayer_engine.py              # MultilayerEngine (5D Langevin)
│   energy_engine.py                  # SocialEnergyEngine (Langevin SDE)
│   energy_runner.py                  # run_energy_simulation()
│   micro_engine.py                   # MicroEngine (bifurcation analysis)
│   social_architect.py               # buscar_estrategia_inversa()
│   cfc_engine.py                     # CfCResidualCorrector (liquid NN)
│   cfc_router.py                     # CfCRouter (singleton with fallback)
│   cfc_trainer.py                    # Training loop for CfC
│   api.py                            # Legacy FastAPI monolith (deprecated, /api/*)
│   schemas.py                        # Root-level Pydantic schemas
│   energy_schemas.py                 # Energy engine input/output schemas
│   micro_schemas.py                  # Micro engine schemas
│   interpreter_layer.py              # NL interpreter layer
│   langchain_workflows.py            # LangChain workflow definitions
│   uil_adapter.py                    # UIL adapter factory
│   gen_report.py                     # Report generation utility
│   document_intelligence.py          # Document parsing (PDF/DOCX → config)
│   i18n.py                           # Internationalization
│   cache_manager.py                  # Simulation result caching
│   brexit_calibration.py             # Brexit 2016 calibration script
│   benchmark_scalability.py          # Scalability benchmark (1K→100M agents)
│   train_cfc_*.py                    # CfC training scripts (lambda, landscape, temp)
│   programmatic_architect.py         # Programmatic architect interface
│   social_connectors.py              # Social connectivity helpers
│   visualizations.py                 # Plotting utilities
│
├── pyproject.toml                    # Project metadata, deps, scripts, tool config
├── requirements.txt                  # Flat dependency mirror
├── install.sh                        # Unified install/run/test/lint/benchmark/clean
├── Makefile                          # Make-based task runner
├── Dockerfile                        # 3-stage multi-stage build
├── docker-compose.yml                # Multi-service orchestration
├── nginx.conf                        # Reverse proxy + SPA serving
├── supervisord.conf                  # Process supervisor config
├── .env.example                      # Environment variable reference
├── .dockerignore                     # Docker build exclusions
├── README.md                         # Main documentation (English)
├── README_ES.md                      # Main documentation (Spanish)
├── AGENTS.md                         # Agent memory / context file
├── CLAUDE.md                         # Behavior guidelines
├── PRODUCTION_ARCHITECTURE_SPEC.md   # Production architecture spec
├── MASSIVE_SYSTEM_MAP.md             # Complete system map
└── CHANGELOG.md                      # Version history
```

---

## Endpoints API vs Implementación

### Endpoints Implementados en `backend/app/routers/` (v1)

| Router | Path | Method | Function | Estado |
|--------|------|--------|----------|--------|
| `sim.py` | `/v1/simulate` | POST | `v1_simulate` | ✅ Activo |
| `forecast.py` | `/v1/forecast` | POST | `v1_forecast` | ✅ Activo |
| `engine.py` | `/v1/engine/energy` | POST | `v1_energy` | ✅ Activo |
| `engine.py` | `/v1/engine/architect` | POST | `v1_architect` | ✅ Activo |
| `llm.py` | `/v1/llm/run_simulation` | POST | `v1_llm_run_simulation` | ✅ Activo |
| `llm.py` | `/v1/llm/wizard` | POST | `v1_llm_wizard` | ✅ Activo |
| `llm.py` | `/v1/llm/extract` | POST | `v1_llm_extract` | ✅ Activo |
| `benchmark.py` | `/v1/benchmarks` | POST | `v1_benchmarks` | ✅ Activo |
| `main.py` | `/` | GET | `root` | ✅ Infra |
| `main.py` | `/health` | GET | `health_check` | ✅ Infra |
| `main.py` | `/ready` | GET | `readiness_check` | ✅ Infra |
| `main.py` | `/version` | GET | `version_info` | ✅ Infra |
| `main.py` | `/metrics` | GET | `metrics` | ✅ Infra |
| `main.py` | `/openapi/v1.json` | GET | `openapi_v1_spec` | ✅ Infra |

**Total endpoints v1: 8 API + 6 infra = 14**

### Endpoints Legacy en `api.py` (deprecated, warning header)

| Path | Method | Estado |
|------|--------|--------|
| `/api/extract` | POST | ⚠️ Deprecated |
| `/api/wizard` | POST | ⚠️ Deprecated |
| `/api/simulate-uil` | POST | ⚠️ Deprecated |
| `/api/v1/architect` | POST | ⚠️ Deprecated (duplicado de engine router) |
| `/api/v1/forecast` | POST | ⚠️ Deprecated (duplicado de forecast router) |
| `/api/v1/energy` | POST | ⚠️ Deprecated (duplicado de engine router) |

### Endpoints Documentados vs Implementados

| Endpoint (docs/api.md) | ¿Implementado? | Notas |
|------------------------|----------------|-------|
| `POST /v1/simulate` | ✅ | Coincide |
| `POST /v1/forecast` | ✅ | Coincide |
| `POST /v1/engine/energy` | ✅ | Coincide |
| `POST /v1/engine/architect` | ✅ | Coincide |
| `POST /v1/benchmarks` | ✅ | Coincide |
| `POST /v1/llm/run_simulation` | ✅ | Coincide |
| `POST /v1/llm/wizard` | ✅ | Coincide (en código, no mencionado explícitamente en api.md) |
| `POST /v1/llm/extract` | ✅ | Coincide |
| `GET /health` | ✅ | Coincide |
| `GET /ready` | ✅ | Coincide |
| `GET /version` | ✅ | Coincide |
| `GET /metrics` | ✅ | Coincide |
| `GET /openapi/v1.json` | ✅ | Implementado, no listado en api.md |

---

## Archivos Obsoletos Detectados

### Backups en raíz del proyecto (deben eliminarse)
| Archivo | Líneas | Notafixed_width |
|---------|--------|-----------------|
| `extended_models.py.backup_1789386230` | ~382 | Backup de refactor |
| `intervention_optimizer.py.backup_1789386230` | ~446 | Backup de refactor |
| `state_compression.py.backup_1789386230` | ~265 | Backup de refactor |
| `utility_logic.py.backup_1789386230` | ~409 | Backup de refactor |
| `.env.backup` | 1 | Credenciales potenciales |

### Legacy monolítico
| Archivo | Uso actual | Recomendación |
|---------|-----------|---------------|
| `api.py` | Still imported by fallback in `install.sh` | Migrar clientes restantes a `/v1/*` y eliminar |

### Directorios vacíos/inutilizados
| Path | Estado |
|------|--------|
| `app/` | Directorio vacío (solo `__pycache__`) |
| `target/` | Build artifacts de Rust (ignorable) |

### Duplicados de módulos
| Módulo duplicado | Ubicación 1 | Ubicación 2 |
|-----------------|-------------|-------------|
| `empirical_calibration.py` | Raíz | `massive/core/` |
| `empirical_config.py` | Raíz | `massive/core/` |
| `extended_models.py` | Raíz | `massive/core/` |
| `intervention_optimizer.py` | Raíz | `massive/core/` |
| `llm_credentials.py` | Raíz | `massive/core/` |
| `schemas.py` | Raíz | `massive/core/` |
| `state_compression.py` | Raíz | `massive/core/` |
| `utility_logic.py` | Raíz | `massive/core/` |

---

## Correcciones Necesarias en README

### Discrepancias detectadas

1. **Conteo de tests**: El README dice "597 tests" pero se encontraron **59 archivos de test**. El conteo real de tests (funciones `test_*`) debe verificarse ejecutando `pytest --collect-only`.

2. **Endpoint `/v1/scientific`**: El docstring de `engine.py` menciona `POST /v1/scientific` pero **no existe** en la implementación actual. Los únicos endpoints en `engine.py` son `/energy` y `/architect`.

3. **`/v1/engine/scientific` ausente**: La referencia en `main.py` línea 157 agrupa `/v1/scientific` con `/v1/simulate` en el path_group, pero no hay router que lo implemente.

4. **Documentación de `/openapi/v1.json`**: No aparece en `docs/api.md` ni en la tabla de endpoints del README, pero está implementado en `main.py`.

5. **README menciona `app/` en el mapa**: El layout del README muestra `backend/app/` correctamente, pero el directorio `app/` en raíz existe y está vacío — no debería estar en el mapa.

6. **Symlink `frontend/dist`**: El README no documenta que `frontend/dist` es un symlink a `../massive-ui-ng/frontend/dist`.

7. **Sección "HTTP API" — faltan `/wizard` y `/extract`**: La tabla de endpoints en README solo lista `/v1/llm/run_simulation` pero omite `/v1/llm/wizard` y `/v1/llm/extract`.

8. **`massive-ui-ng` no en CI raíz**: El README dice "(not in CI root — see ARCH-02)" pero no hay referencia a ARCH-02 en la documentación disponible.

### Correcciones sugeridas para README

```markdown
# En la tabla de endpoints HTTP API, agregar:
| `/v1/llm/wizard` | POST | Generate simulation config from natural language |
| `/v1/llm/extract` | POST | Extract config from uploaded document |
| `/openapi/v1.json` | GET | Export OpenAPI v1 spec (v1 endpoints only) |

# En el mapa de directorios, agregar nota sobre symlink:
├── frontend/             # React 18 + Vite SPA
│   └── dist → ../massive-ui-ng/frontend/dist  # symlink

# Corregir conteo de tests: ejecutar pytest --collect-only para número real
# Eliminar referencia a app/ vacío del mapa
```

---

## Mappings de Importación

### `services/__init__.py` — Superficie pública
```python
__all__ = [
    "run_scalar_simulation",
    "run_multilayer_simulation",
    "run_massive_sim",
    "run_llm_simulation",
    "factbook_service",
    "forecast_service",
    "llm_service",
]
```

### `backend.app.models.__init__` — Re-exports DTOs
```python
# simulation: SimAgentLite, SimAggregateMetrics, SimulationSnapshotPayload,
#             SimSnapshotMessage, SimEventMessage, SimMode, SimEventKind
# snapshot:   SnapshotRecord, TimelineTick, TimelineResponse
# forecast:   ForecastPoint, Feasibility, ForecastResponse
# architect:  InterventionRecord, InterventionLogEntry, ArchitectEventMessage
# llm:        LLMRunRequest, LLMRunResponse, LLMSummary, LLMResults,
#             LLMTimelinePoint, LLMLlmHint, LLMAmbiguityResponse,
#             LLMExtractResponse, LLMWizardRequest, LLMWizardResponse
```

### `massive_core/__init__.py` — Re-exports
```python
# massive_core.config: configure_logging, get_logger, AppSettings
# massive_core.contracts: LLMContract
# massive_core.scientific_runner: run_scientific_simulation
```

---

## Coverage Gaps Detectados

| Módulo | Tests existentes | Observación |
|--------|-----------------|-------------|
| `simulator.py` | `test_simulator.py` | Cubierto |
| `energy_engine.py` | `test_energy_engine.py`, `test_energy_core.py` | Cubierto |
| `massive_engine.py` | `test_massive_engine.py` | Cubierto |
| `multilayer_engine.py` | `test_multilayer.py`, `test_multilayer_engine_coverage.py` | Cubierto |
| `micro_engine.py` | `test_micro.py`, `test_micro_engine_coverage.py` | Cubierto |
| `social_architect.py` | `test_social_architect.py` | Cubierto |
| `forecast/engine.py` | `test_forecast.py` | Cubierto |
| `cfc_engine.py` | `test_cfc_engine.py`, `test_cfc_router.py` | Cubierto |
| `services/` | `test_services_layer.py` | Parcial |
| `backend/app/routers/` | `test_api_security.py`, `test_backend_observability.py` | **Parcial** — no hay tests unitarios por router |
| `benchmarks/` | `test_pvu_runner.py` | **Parcial** — solo runner, no sub-módulos |
| `massive_core/data_assimilation/` | `test_data_assimilation_workflow.py` | Cubierto |
| `massive_core/numerics/` | `test_sparse_refactor.py` | **Parcial** |

**Gap crítico**: Los 5 routers (`sim`, `forecast`, `engine`, `llm`, `benchmark`) no tienen tests unitarios propios — solo `test_api_security.py` y `test_backend_observability.py` cubren auth/middleware a nivel general.

---

## Notas de Arquitectura

1. **Doble superficie API**: `api.py` (legacy, `/api/*`) coexiste con `backend/app/main.py` (canonical, `/v1/*`). Los legacy routes tienen middleware `deprecation_warning` que añade `X-API-Warn` header.

2. **Compatibilidad `/api/v1/*`**: `main.py` registra los mismos routers bajo `/api/v1/*` como alias de compatibilidad para el frontend existente.

3. **JIT warm-up**: `main.py` ejecuta `_warm_jit_sync()` en el lifespan para pre-compilar kernels Numba y evitar latencia en la primera petición.

4. **CLI entry-point**: `massive-cli = "massive.cli.main:main"` en `pyproject.toml` expone subcomandos: `simulate`, `scientific`, `benchmark`, `forecast`, `version`, `serve`.

5. **Docker multi-stage**: 3 stages (`builder-py` → `builder-fe` → `runtime`) con supervisord corriendo como `appuser` no-root.

6. **Massive-ui-ng es subsistema separado**: Tiene su propio FastAPI, routers, tests y estructura. No está integrado en el pipeline CI principal del repositorio raíz.
