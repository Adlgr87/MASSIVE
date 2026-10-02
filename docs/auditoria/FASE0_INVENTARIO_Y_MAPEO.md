# FASE 0 — Inventario y Mapeo Verificado
## Auditoría integral MASSIVE · Entregable 1/6

> **Repo:** `Adlgr87/MASSIVE` · **Rama:** `arena/01a0fb01-massive` · **Commit base:** `963ff7f`
> **Fecha:** 2026-10-01 · **Auditor:** análisis estático forense, sin modificar código
> **Alcance de esta fase:** mapa verificado de archivos/capas, grafo de dependencias, inventario de endpoints y componentes, detección temprana de nodos sin aristas, y **declaración de cobertura**.
>
> Convención de evidencia: **[HECHO]** = verificado en código · **[INFERENCIA]** = razonamiento · **[DIN]** = requiere verificación dinámica.

---

## 0. Advertencia previa: el contexto del prompt NO coincide con el repo

Antes de auditar nada, verifiqué cada ruta y cifra declarada en la sección 1 del prompt maestro. **Siete afirmaciones del contexto son falsas contra el árbol real.** Esto importa porque un auditor que las asuma produciría hallazgos fantasma.

| # | Afirmación del prompt | Realidad verificada | Evidencia |
|---|---|---|---|
| C1 | `massive-ui-ng/` existe (kit UI next-gen) | **No existe.** Fue eliminado el 2026-09-22 | `ls` falla; `docs/architecture/current-state.md:102` lo documenta como eliminado |
| C2 | `docker-compose.single.yml` existe | **No existe.** Archivado | `README.md:97` dice que está en `docs/examples/`; **tampoco está ahí** → referencia rota en README |
| C3 | `utility_logic.py`, `state_compression.py`, `schemas.py` en la raíz | Están en `massive/core/` | `massive/core/{utility_logic,state_compression,schemas}.py` |
| C4 | «El frontend React usa la capa legacy `/api`» | **Falso.** El frontend está migrado a `/v1` | `frontend/src/services/api.ts:27` → `baseURL: "/v1"` |
| C5 | 530 tests, cobertura 68 % branch | **689 funciones de test** en 61 archivos; umbral de cobertura configurado = **30 %** | `grep "def test_"`; `pyproject.toml` → `fail_under = 30` |
| C6 | 16 checks de CI, incluye **semgrep** | 11 workflows / **52 jobs**; **semgrep no aparece en ningún workflow** | `grep -ril semgrep .github/` → vacío |
| C7 | ~304 commits | El clon tiene **1 commit** (shallow/squash) | `git rev-list --count HEAD` = 1 → **la auditoría de historia Git y de secretos históricos es imposible aquí** [DIN] |

> **Nota metodológica:** trabajaré sobre el árbol real. Donde el prompt pide verificar algo inexistente (ej. `massive-ui-ng/`, checklist §9), el resultado es «no aplica — eliminado», y así lo reportaré.

---

## 1. Cobertura declarada de la Fase 0

| | Archivos | Analizados en Fase 0 | Método |
|---|---:|---:|---|
| Versionados totales | 473 | 473 (100 % inventariados) | `git ls-files` |
| Python | 218 (~46.169 LOC) | 218 parseados con AST | grafo de imports completo, 0 fallos de parseo |
| TypeScript/TSX | 9 (524 LOC) | 9 leídos íntegros | lectura completa |
| Workflows CI | 11 (52 jobs) | 11 | lectura de steps |
| Markdown | 101 | 24 vivos leídos / 77 de `docs/archive` sólo indexados | ver exclusión abajo |
| Datos/binarios | 9 `.pt`, 15 `.csv`, 59 `.json`, 3 `.png` | inventariados, no abiertos | — |

**Exclusiones declaradas (no finjo cobertura total):**
- `docs/archive/**` (77 `.md`, ~1 MB, incl. `AUDIT_REPORT_2026-09-15.md` de 5.440 líneas y `Audit_MASSIVE.patch` de 7.092): **indexados y usados como contexto histórico**, no auditados línea a línea. Son documentos muertos por definición.
- `uv.lock` (1,2 MB) y `frontend/package-lock.json` (6.497 líneas): no leídos; se auditarán por herramienta en la fase de dependencias.
- `node_modules/`, `.venv/`, `site/`: no versionados.
- Contenido numérico de los 9 `.pt` y `predictions.npz`: requiere carga con torch [DIN].

**Lo que NO se puede hacer en este entorno** (lo declaro ya, para la sección 9 del informe final):
- Historia Git = 1 commit → sin auditoría de secretos históricos ni de deriva por commit.
- Sin red/instalación → no ejecuté `pytest`, `mypy`, `ruff`, `docker build`, ni el frontend. Todo lo que diga «falla» en Fase 0 se deriva de evidencia estructural, no de ejecución.

---

## 2. Mapa de arquitectura **verificado** (real, no declarado)

```
                     ┌──────────────────────────────┐
  NAVEGADOR ───────► │ frontend/ (React18+Vite+TS)  │  524 LOC, 9 archivos
                     │  App.tsx(32) main.tsx(13)    │
                     │  services/api.ts(200) ◄──────┼── baseURL "/v1"   [HECHO]
                     │  hooks/useApi.ts(72)  ⚠ NO   │
                     │        USADO POR NADIE       │
                     │  types/api.generated.ts(201) │
                     └───────────┬──────────────────┘
                 vite proxy /v1 y /api → localhost:8000
                                 │
        ┌────────────────────────┴───────────────────────┐
        ▼                                                 ▼
┌───────────────────────────────┐          ┌──────────────────────────────┐
│ backend/app  (CANÓNICA)       │          │ api.py (LEGACY, raíz, 506 L) │
│ main.py:262-273               │          │ app = FastAPI("MASSIVE UIL") │
│  monta routers DOS VECES:     │          │  /api/extract /api/wizard    │
│   prefix=/v1   y  /api/v1  ⚠  │          │  /api/simulate-uil           │
│ routers: sim engine forecast  │          │  /api/v1/{architect,forecast,│
│          benchmark llm        │          │            energy}        ⚠  │
│ /health /ready /version       │          │ /health /ready /version /    │
│ /metrics /openapi/v1.json     │          └──────────────────────────────┘
└───────────┬───────────────────┘            ⚠ COLISIÓN de espacio /api/v1
            ▼                                   entre las dos apps
┌───────────────────────────────────────────────────────────┐
│ services/  — simulation_service · forecast_service ·      │
│              factbook_service · llm_service ·             │
│              llm_orchestrator(874 L)                      │
└───────────┬───────────────────────────────────────────────┘
            ▼
┌───────────────────────────────────────────────────────────┐
│ MOTORES (raíz, py-modules legacy, 13.8k LOC)              │
│  simulator(2467)★ massive_engine(1269) multilayer(1035)   │
│  micro_engine(1038) energy_engine(687) social_architect   │
│  cfc_{engine,router,trainer} uil_adapter interpreter_layer│
└───────────┬───────────────────────────────────────────────┘
            ▼
┌──────────────────────┬──────────────────────┬─────────────┐
│ massive/ (CLI +      │ massive_core/        │ micro_massive│
│  factbook 2.9k LOC)  │  14 subpaquetes      │ forecast/    │
│                      │  numerics physics    │ benchmarks/  │
│                      │  EnKF PINNs …        │ metrics/     │
└──────────────────────┴──────────────────────┴─────────────┘
            ▼
┌───────────────────────────────────────────────────────────┐
│ rust_core/ (maturin) ──► massive_core/rust_core.py        │
│ models/cfc_calibrated/ (9 .pt + npz)                      │
│ datasets/{pvu_cases(2), real_cases(12)} · data/factbook   │
└───────────────────────────────────────────────────────────┘

INFRA: Dockerfile(3 stages) ⛔ROTO · docker-compose.yml · 11 workflows/52 jobs
       monitoring/{prometheus,grafana} · scripts/(11) · Makefile
```
★ = hotspot de tamaño

### Desviaciones del mapa real vs. el declarado (README + prompt)

| ID | Desviación | Severidad | Evidencia |
|---|---|---|---|
| M1 | `backend/app` monta los 5 routers **dos veces**: `/v1/*` y `/api/v1/*`. Esto duplica la superficie de API y colisiona nominalmente con los `/api/v1/{architect,forecast,energy}` de `api.py` | **Alto** | `backend/app/main.py:262-273` |
| M2 | Existen **dos aplicaciones FastAPI independientes** (`api:app` y `backend.app.main:app`) con `/health`, `/ready`, `/version` duplicados. El Makefile ofrece ambas (`make api` / `make api-legacy`) | **Alto** | `Makefile`; `api.py:27,467,476,501` vs `backend/app/main.py:289,312,364` |
| M3 | El frontend ya **no** usa la legacy; `api.py` queda sin consumidor conocido | Medio | `frontend/src/services/api.ts:27` |
| M4 | README apunta a `docker-compose.single.yml` en `docs/examples/`: **no está** | Medio | `README.md:97`, `README_ES.md:90` |
| M5 | README_ES declara 530 tests; hay 689 funciones de test | Bajo | `README_ES.md:229,261` |

---

## 3. 🔴 Hallazgo Crítico emergente en Fase 0 — la imagen Docker no puede construirse

**[HECHO]** El `Dockerfile` copia dos archivos que **no existen en la raíz**:

```dockerfile
# Dockerfile (stage 3, runtime)
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
...
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
```

Ubicación real de ambos archivos:
```
docs/archive/legacy_docker/nginx.conf
docs/archive/legacy_docker/supervisord.conf
```

Y, aunque se corrigiera la ruta a `docs/archive/legacy_docker/`, **`.dockerignore` excluye `docs/` por completo**:
```
# Docs, CI, build outputs (not needed in runtime image)
docs/
```

**Impacto en cadena:**
1. `docker compose build` falla → `docker-compose.yml` (único compose existente) es inservible.
2. El workflow `docker-e2e.yml` ejecuta `docker compose build` en su paso 2 → **ese check de CI está roto en `main`** [INFERENCIA fuerte, confirmable viendo el run].
3. La promesa del README de desplegar «frontend + API vía nginx en :80» no se cumple.
4. El `CMD` apunta a supervisord, que nunca estará configurado → el contenedor no arrancaría ni con build parcheado.

**Categoría:** error / infra · **Severidad: Crítico** · **Corrección sugerida:** restaurar `nginx.conf` y `supervisord.conf` a la raíz del repo (fueron movidos a `docs/archive/legacy_docker/` en la «limpieza integral» del commit base, sin actualizar el Dockerfile), o reescribir el Dockerfile para no depender de nginx/supervisord.

**[DIN]** Confirmar con `docker compose build` y revisando el último run de `docker-e2e.yml` en GitHub Actions.

---

## 4. Inventario de endpoints (base para la matriz de Fase 3)

### 4.1 `backend/app` — API canónica
Montada **dos veces**: `prefix=/v1` y `prefix=/api/v1` (`main.py:262-273`).

| Router (archivo:línea) | Path del router | Método + ruta efectiva |
|---|---|---|
| `routers/sim.py:19,25` | — | `POST /v1/simulate` |
| `routers/forecast.py:23,29` | — | `POST /v1/forecast` |
| `routers/engine.py:23` | `/energy` | `POST /v1/engine/energy` |
| `routers/engine.py:64` | `/architect` | `POST /v1/engine/architect` |
| `routers/benchmark.py:17,23` | — | `POST /v1/benchmarks` |
| `routers/llm.py:63` | `/run_simulation` | `POST /v1/llm/run_simulation` |
| `routers/llm.py:150` | `/wizard` | `POST /v1/llm/wizard` |
| `routers/llm.py:180` | `/extract` | `POST /v1/llm/extract` |

Nivel app: `GET /` (277) · `/health` (289) · `/metrics` (299, **protegido por API key**) · `/ready` (312) · `/version` (364) · `/openapi/v1.json` (375). Middlewares HTTP: 4 (`main.py:111,145,162,234`).

> ⚠ El prompt declara `/v1/llm/run_simulation` pero omite `/v1/llm/wizard` y `/v1/llm/extract`, que **sí existen** y son los que consume el frontend.

### 4.2 `api.py` — API legacy
`POST /api/extract` (153) · `POST /api/wizard` (200) · `POST /api/simulate-uil` (221) · `POST /api/v1/architect` (269) · `POST /api/v1/forecast` (326) · `POST /api/v1/energy` (413) · `GET /` (457) · `/health` (467) · `/ready` (476) · `/version` (501).

### 4.3 Llamadas del frontend (`frontend/src/services/api.ts`)
`baseURL = "/v1"`, con `X-API-Key` inyectado en el constructor.

| Método del cliente (línea) | Request | Endpoint canónico correspondiente | ¿Existe? |
|---|---|---|---|
| `forecast()` ~108 | `POST /forecast` | `POST /v1/forecast` | ✅ |
| `architect()` ~127 | `POST /engine/architect` | `POST /v1/engine/architect` | ✅ |
| `energy()` ~160 | `POST /engine/energy` | `POST /v1/engine/energy` | ✅ |
| `simulateUil()` ~175 | `POST /simulate` | `POST /v1/simulate` | ✅ |
| `extractDocument()` ~183 | `POST /llm/extract` (multipart) | `POST /v1/llm/extract` | ✅ |
| `wizard()` ~195 | `POST /llm/wizard` | `POST /v1/llm/wizard` | ✅ |

**Endpoints del backend que ningún cliente consume:** `POST /v1/benchmarks`, `POST /v1/llm/run_simulation`, `GET /metrics`, `GET /openapi/v1.json`, y **la totalidad de `api.py`**.

**Señales tempranas del frontend para Fase 4:**
- **F1 [HECHO]** `src/hooks/useApi.ts` (72 LOC, 6 hooks exportados) **no es importado por ningún archivo** → código muerto. Además su `execute` recibe `config` pero para `post/put/patch` lo pasa como **segundo argumento**, que en `ApiService.post(url, data, config)` corresponde a **`data`**, no a `config` → el hook enviaría el config de axios como body. **Severidad: Alto** (si alguna vez se usa).
- **F2 [HECHO]** `App.tsx` son 32 líneas: importa `Routes/Route` y `Button`. **No llama a `api` en ningún punto.** La GUI real es un esqueleto; `src/services/api.ts` (200 LOC) tampoco tiene consumidor. → **toda la capa de datos del frontend está desconectada.** **Severidad: Crítico** para la pretensión de «GUI funcional».
- **F3 [HECHO]** `api.ts:35-38` cablea el fallback `"dev-secret-key"` en el cliente cuando `MODE === "development"`. Choca con el invariante «la clave fallback de dev está prohibida y debe loguearse ruidosamente».
- **F4 [HECHO]** `lib/utils.ts` (6 LOC) no lo importa nadie. `components/ui/button.tsx` sólo lo usa `App.tsx`.
- **F5 [HECHO]** No hay manejo de `422 + requested_fields` ni de `503` en el interceptor (`api.ts:44-53`): sólo loguea 401 y 429 por consola, sin `retry-after`.

---

## 5. Grafo de dependencias — nodos sin aristas

Construí el grafo por AST sobre **todos** los `.py` (incluidos `tests/`, `scripts/` y `docs/examples/`), 0 fallos de parseo, y filtré los falsos positivos por re-export en `__init__.py`.

### 5.1 Huérfanos duros confirmados (0 imports, 0 menciones externas)

| Módulo | LOC | Evidencia |
|---|---:|---|
| `social_connectors.py` | 332 | `grep` en todo el repo: **ninguna** mención fuera del propio archivo |
| `benchmark_scalability.py` | 908 | ningún import; menciones sólo en docs archivadas |
| `benchmarks/bench_perf_f.py` | — | única mención en `docs/archive/reports/REPORT_STRUCTURE.md:124` |

**1.240+ LOC de código muerto duro.** Nota: `social_connectors.py` depende de `tweepy`/`praw` (extra `social` en `pyproject`) → arrastra dependencias para código que nadie ejecuta.

### 5.2 Módulos de consumo exclusivamente por test (sin consumidor en producción)
`brexit_calibration.py` (257) · `visualizations.py` (124) · `micro_schemas.py` (113) · `massive_core/metalearning/cfc_training_data.py` · `massive_core/multiscale/hierarchical_time.py`. **[INFERENCIA]** Son capacidades declaradas en el README que ninguna ruta de usuario alcanza.

### 5.3 Módulos de entrada legítimos (huérfanos por diseño, no son hallazgo)
`api.py`, `backend/app/main.py`, `massive/cli/*`, `scripts/*`, `docs/examples/train_cfc_*.py`, `benchmarks/runner.py`, `cfc_trainer.py` — se invocan por consola/uvicorn/CI.

### 5.4 Nodos más acoplados (prioridad de auditoría profunda en Fase 1)

| Importadores | Módulo | LOC |
|---:|---|---:|
| 15 | `simulator` | 2.467 |
| 8 | `multilayer_engine` | 1.035 |
| 7 | `massive_core.config` | — |
| 6 | `backend.app.security` / `backend.app.models` / `massive_engine` / `cfc_router` | — |
| 5 | `energy_engine`, `massive_core.numerics`, `uil_adapter`, `metrics.unified_metrics`, `micro_massive.core.agent` | — |

---

## 6. Inventario por capa (resumen tabular)

| Capa | Archivos | LOC aprox | Notas de riesgo |
|---|---:|---:|---|
| Motores raíz | 23 `.py` | 13.830 | 3 god-files; 2 huérfanos duros |
| `massive/` | 16 | ~5.500 | `factbook/loader.py` 1.228 LOC; `empirical_config.py` 646 |
| `massive_core/` | 36 en 14 subpaquetes | ~7.000 | `multilayer_engine_sparse.py` 789 con opt-out de mypy (issue #42) |
| `backend/app/` | 20 | ~2.000 | 5 routers, 8 DTOs, doble montaje |
| `services/` | 6 | ~2.000 | `llm_orchestrator.py` 874 |
| `micro_massive/` | 8 | ~900 | |
| `forecast/` | 6 | ~1.000 | |
| `benchmarks/` | 11 | ~1.800 | 1 huérfano |
| `metrics/`, `adapters/` | 5 | ~500 | |
| `frontend/` | 9 TS/TSX | 524 | capa de datos desconectada |
| `rust_core/` | 1 `.rs` + Cargo | — | fuera del wheel; paridad sin verificar [DIN] |
| `tests/` | 61 | 9.373 | 689 test funcs; 33 ocurrencias de `skip`/`xfail` a revisar |
| `scripts/` | 11 | ~2.000 | `verify_harness.py` (7 etapas, guardrails G-1) |
| CI | 11 workflows | 52 jobs | sin semgrep; `docker-e2e` presumiblemente roto |
| Docs vivas | 24 `.md` | — | referencias rotas detectadas (M4) |
| Docs archivadas | 77 `.md` | ~1 MB | ruido; 76 % del corpus documental |

### Datos y artefactos
- `datasets/real_cases/`: **12 casos** (brexit_2016, us_2020, brazil_2022, chile_2019, colombia_2021, egypt_2011, france_2018, germany_2014, hong_kong_2019, iran_2022, myanmar_2021, south_korea_2016), cada uno `meta.json` + `timeseries.csv` + `interventions.json`.
- `datasets/pvu_cases/`: 2 casos sintéticos.
- `models/cfc_calibrated/`: 9 checkpoints `.pt` + `predictions.npz` + 3 configs + logs, **versionados en Git**.
- `configs/`: `pvu.yaml`, `multilayer.yaml`, `gitleaks.toml`, `llm_contract/massive_llm_contract.json` (838 líneas).
- `.env.example`: **42 variables**, incluidas `MASSIVE_DEV_FALLBACK=1`, y **dos** variables de clave distintas y potencialmente contradictorias: `MASSIVE_API_KEY` (singular) y `MASSIVE_API_KEYS` (plural) → a trazar en Fase 2.

---

## 7. Backlog de hipótesis priorizado para las fases siguientes

| ID | Hipótesis | Cat. | Sev. prelim. | Fase |
|---|---|---|---|---|
| **H-01** | Docker build roto (`nginx.conf`/`supervisord.conf` ausentes + `.dockerignore`) | error/infra | **Crítico** | ✅ ya probado |
| **H-02** | Capa de datos del frontend desconectada: `api.ts`, `useApi.ts`, `lib/utils.ts` sin consumidor; `App.tsx` = 32 LOC | desconectado/GUI | **Crítico** | 4 |
| **H-03** | `useApi.execute` pasa `AxiosRequestConfig` en la posición de `data` en post/put/patch | error | Alto | 4 |
| **H-04** | `dev-secret-key` cableada en el bundle del frontend (`api.ts:37`) viola invariante fail-closed | seguridad | Alto | 1/4 |
| **H-05** | Doble montaje `/v1` + `/api/v1` en `backend/app` y colisión con `api.py` | fuera-de-lugar | Alto | 3 |
| **H-06** | Dos apps FastAPI con `/health`,`/ready`,`/version` duplicados y deriva de lógica | duplicación | Alto | 1/3 |
| **H-07** | 1.240+ LOC de huérfanos duros (`social_connectors`, `benchmark_scalability`, `bench_perf_f`) | desconectado | Medio | 6 |
| **H-08** | Correlaciones Factbook→motor (Gini→atractor, GDP→presupuesto, diversidad→presión): signo/escala/clip sin verificar | **correlación** | ? | **2 (núcleo)** |
| **H-09** | 5D Langevin: simetría de acoplamiento, autovalores, ruido no negativo, estabilidad de `dt` | **correlación** | ? | **2** |
| **H-10** | LOD/super-agentes: conservación de media/varianza/población al colapsar; sesgo de cuantización uint8 | **correlación** | ? | **2** |
| **H-11** | CfC residual: forma de la corrección (aditiva/multiplicativa/clip), rango entrenamiento vs inferencia, paridad engine/router/trainer | **correlación** | ? | **2** |
| **H-12** | EnKF: inflación, localización, tamaño de ensamble, mapeo observador→estado | **correlación** | ? | **2** |
| **H-13** | Paridad numérica Rust↔Python del fallback | correlación | ? | 2 |
| **H-14** | Determinismo: `PYTHONHASHSEED`, orden de sets/dicts, RNG por motor | error | ? | 2 |
| **H-15** | Contrato LLM v1.1.0 vs `llm_orchestrator.py` (¿adivina campos faltantes en vez de 422?) | contrato | ? | 3 |
| **H-16** | 33 ocurrencias `skip`/`xfail` en tests; cobertura real vs `fail_under=30` | tests | Medio | 5 |
| **H-17** | CI sin semgrep pese a lo documentado; `docker-e2e` presumiblemente en rojo | CI | Medio | 5 |
| **H-18** | God-files: `simulator.py` 2.467 · `massive_engine.py` 1.269 · `factbook/loader.py` 1.228 | optimización | Medio | 1/7 |
| **H-19** | `MASSIVE_API_KEY` vs `MASSIVE_API_KEYS`: dos mecanismos de auth coexistiendo | seguridad | Alto | 1 |
| **H-20** | Artefactos ML binarios (9 `.pt`) y 1 MB de PNG versionados en Git | higiene | Bajo | 6 |
| **H-21** | `torch`/`dask`/`pgmpy` como deps **core** en `pyproject` rompe el invariante «optional means optional» | dependencias | Alto | 1 |
| **H-22** | Referencias rotas en README (`docker-compose.single.yml`) y cifras obsoletas (530 tests) | docs | Bajo | 6 |

---

## 8. Checkpoint de continuidad

**Completado:** Fase 0 íntegra — inventario 473/473, grafo AST de 218 módulos, endpoints de ambas APIs, cliente y árbol del frontend, verificación del contexto del prompt, 22 hipótesis priorizadas y 1 hallazgo crítico ya probado (Docker).

**Punto exacto de reanudación:** **Fase 1 — análisis estático por capas**, empezando por el orden de riesgo: (1) `backend/app/{main,security,settings}.py` + `massive_core/config/*` para los invariantes de seguridad (H-04, H-19, H-21); (2) motores raíz por acoplamiento descendente (`simulator` → `multilayer_engine` → `massive_engine` → `energy_engine`); (3) `services/llm_orchestrator.py`.

**Entregables pendientes:** matriz de endpoints completa (Fase 3), **matriz de correlación de variables** (Fase 2 — la más extensa, H-08 a H-14), verificación de GUI (Fase 4), informe priorizado (Fase 5).
