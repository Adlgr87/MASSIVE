# FASE 0 — Cartografía y Línea Base

> **Orquestador:** OMNISCIENT (este documento)
> **Fecha:** 2026-10-14
> **Commit HEAD:** `30eee99` (main / prod-readiness)
> **Entorno:** Python 3.14.8 (venv), Node 22.x, Ubuntu
> **Objetivo:** Mapear el repositorio, verificar instalación limpia, establecer línea base de pruebas e imports, y producir el mapa de dependencias entre módulos.

---

## 1. Estado del repositorio

### Sincronización local ↔ GitHub
- **Hecho:** `git log --oneline main` y `origin/main` están ambos en `30eee99` — **local está sincronizado con GitHub**.
- `git merge-base --is-ancestor main prod-readiness` → `main` es ancestro de `prod-readiness` → **sin divergencia**.
- La rama `prod-readiness` está disponible y apunta al mismo commit que `main`.

### Rust layer (confirmado eliminado)
- **Hecho:** La capa Rust fue eliminada en commits `75c2b64` y `3a6a6a3` (ver histórico git).
- `pyproject.toml` línea 63: *"Pure Python build — no native extensions, no Rust toolchain required."*
- No existen archivos `Cargo.toml`, `rust_core/`, ni referencias a Rust en el código (verificado via grep).
- El antecedente conocido (abr 2026: *"main roto por imports de módulos inexistentes"*) **ya no aplica** — todos los imports verificados (§3).

---

## 2. Estructura del árbol (verificado `ls`/`git ls-files`)

```
MASSIVE/
├── backend/app/                     # FastAPI canónico (/v1/*)
│   ├── main.py (390 lines)
│   ├── models/                      # DTOs Pydantic v2 (extra="forbid")
│   ├── routers/                     # sim, forecast, engine, llm, benchmark
│   ├── security.py, metrics.py, settings.py
├── services/                        # Orquestación (llm_orchestrator 874 lines)
│   ├── simulation_service.py, forecast_service.py, factbook_service.py
│   └── llm_service.py, llm_orchestrator.py
├── massive/                         # CLI + core/factbook + empirical
│   ├── cli/main.py, core/{abcsbi,backtesting,convergence_certifier,...}
├── massive_core/                    # Capa científica opt-in
│   ├── numerics/{solvers,steppers,stability,multilayer_engine_sparse}
│   ├── physics/, dynamical_systems/, data_assimilation/, metalearning/
│   ├── diagnostics/, multiscale/, network_inference/, neural_physics/
│   └── config/, analysis/
├── forecast/                        # Motor de riesgo temporal
├── ground_truth/                    # Tier 1 microdata parquet (12 casos)
├── datasets/                        # ground_truth parquet + pvu_cases/ + real_cases/
├── configs/                         # calibrated/, llm_contract/, gitleaks.toml
├── models/                          # cfc_calibrated/ (weights .pt git-ignored)
├── benchmarks/                      # PVU-BS runner + scientific benchmarks
├── scripts/                         # calibración, TS generation, verificación
├── frontend/                        # React 18 + Vite + TS
├── tests/                           # 878 tests totales
├── monitoring/                      # Prometheus + Grafana
├── .github/workflows/               # 11 CI workflows
├── requirements.txt (38 líneas)
├── pyproject.toml (v1.0.0)
├── Makefile
├── README.md, README_ES.md
└── CHANGELOG.md
```

### Tamaños de módulos clave (líneas)
| Archivo | Líneas | Rol |
|---|---|---|
| `simulator.py` | 2,463 | Engine escalar legacy |
| `massive_engine.py` | 1,271 | LOD super-agents (100M) |
| `multilayer_engine.py` | 1,035 | Langevin sociodemográfico 5D |
| `micro_engine.py` | 1,038 | Familias de futuros / bifurcatación |
| `energy_engine.py` | 687 | Social-energy SDE (Euler-Maruyama) |
| `social_architect.py` | 706 | Búsqueda inversa de intervenciones |
| `cfc_engine.py` | 356 | Corrector residual CfC |
| `cfc_router.py` | 460 | Router singleton CfC + fallbacks |
| `api.py` | 506 | FastAPI legacy (/api/*) |
| `backend/app/main.py` | 390 | FastAPI canónico (/v1/*) |
| `services/llm_orchestrator.py` | 874 | NL→engine dispatch (contract v1.1.0) |

---

## 3. Verificación de imports (smoke test)

### Root modules (22 verificados)
```
✅ 21/22 OK
❌ benchmark_scalability: ModuleNotFoundError psutil  →  RESUELTO (instalar from requirements.txt)
```

### Packages + subpackages (38 + 23 submódulos verificados)
```
✅ 38/38 packages OK
✅ 23/23 submódulos corregidos OK
  (Nota: smoke test inicial usó nombres erróneos massive.core.empirical, 
   massive.core.intervention, massive.core.utility — los módulos reales son
   empirical_calibration, intervention_optimizer, utility_logic respectivamente.
   Estos existen y se importan correctamente.)
```

### Import cycles
- **Ningún ciclo detectado** (verificado importando módulos uno a uno y monitoreando sys.modules).

### Dependencias opcionales
| Dependencia | Estado | Nota |
|---|---|---|
| `torch` (>=2.2.0) | ✅ Instalable via requirements.txt | CfC engines; fallback transparente si no está |
| `pyarrow` (>=14.0) | ✅ Instalable via requirements.txt | Parquet (ground_truth microdata) |
| `psutil` (>=5.9.0) | ✅ Instalable via requirements.txt | Benchmarking de recursos |
| `ripser/persim` | ⚠️ No en requirements.txt | TDA: se desactiva con warning (`[TDA] ripser/persim no instalados`) |
| LLM keys (OpenAI/Groq/OpenRouter) | ⚠️ Opcional | Fallback determinista cuando no configurados |

---

## 4. Línea base de pruebas

### Resultados (`PYTHONHASHSEED=42 .venv/bin/python -m pytest tests/ --tb=line`)
```
866 passed, 12 skipped, 17 warnings in 25.94s
878 tests collected (866 + 12)
```

### Tests omitidos (12) — TODOS por pesos .pt git-ignored
| Archivo | Tests omitidos | Razón |
|---|---|---|
| `test_cfc_lambda_integration.py` | 3 | `cfc_lambda_corrector.pt` no existe (git-ignored) |
| `test_cfc_landscape_integration.py` | 9 | `cfc_landscape.pt` no existe (git-ignored) |

**Verificado:** Los 12 skips están correctamente marcados con `pytest.mark.skipif` y la razón documentada. El comportamiento de fallback (passthrough) está cubierto por tests no marcados que pasan.

### Discrepancia README vs realidad
| Ítem | README dice | Realidad verificada | Ajuste necesario |
|---|---|---|---|
| Count de tests | "887 tests" | 878 (866+12) | Actualizar README |
| Cobertura | "68 % branch" | 71.12% | Actualizar README |

### Coverage report (módulos clave)
| Módulo | Cobertura | Archivos críticos sin cobertura |
|---|---|---|
| `multilayer_engine.py` | 95% | Líneas 368, 370, 553-554, 569, 845-859 |
| `micro_engine.py` | 89% | Líneas 297-298, 302-314, 392-405, 541-558 |
| `massive_engine.py` | 77% | Líneas 60-66, 75-79, 635-653, 764-813 (bloques de fallback) |
| `simulator.py` | 67% | Líneas 976-1004, 1184-1188, 1284-1285, 2327-2428 |
| `cfc_engine.py` | — | Ver detalle en test-cov |
| `cfc_router.py` | — | Ver detalle en test-cov |
| `services/llm_orchestrator.py` | 82% | Líneas 407-435 (fallback LLM), 583-608 (error handling) |
| `backend/app/main.py` | — | Ver detalle en test-cov |
| `massive_core/neural_physics/pinns.py` | **0%** | **0% cobertura — módulo entero** |
| `massive_core/network_inference/reconstruct.py` | 21% | Muy bajo |
| `massive_core/physics/perturbation_theory.py` | 33% | Muy bajo |
| `massive_core/analysis/` | 0% | Módulo sin tests |

### CI workflows (11 archivos)
| Workflow | Propósito |
|---|---|
| `pytest.yml` | Core (6 archivos), Scientific (5 archivos), API, Full-suite con coverage gate (30%) |
| `lint.yml` | ruff + black + mypy slice |
| `benchmark.yml` | PVU-BS offline validation |
| `frontend-build.yml` | React build + lint + tsc |
| `docker-e2e.yml` | Docker compose health check |
| `mkdocs.yml` | Build docs site |
| `typecheck.yml` | Mypy full (services/ + slice) |
| `pvu-validation.yml` | Pre-registro PVU |
| `secret_scan.yml` | Gitleaks |
| `validate_ts_types.yml` | DTOs→TypeScript sync |
| `publish.yml` | Release/publicación |

---

## 5. Instalación limpia (verificación del README)

### Pasos del README (§Quick start)
```bash
git clone https://github.com/Adlgr87/MASSIVE.git && cd MASSIVE
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Resultado:
- ✅ `pip install -r requirements.txt` incluye torch, pyarrow, psutil (líneas 28, 33, 38 del requirements.txt).
- ✅ CLI responde: `python -m massive.cli version` → "MASSIVE CLI v1.0.0"
- ✅ Simulación: `python -m massive.cli simulate --pasos 30` produce JSON válido.
- ✅ Backend arranca: `python -c "from api import app; print(app.title)"` → "MASSIVE API"
- ✅ Frontend build: `cd frontend && npm run build` → ✓ built in 544ms.

### **PROBLEMA CRÍTICO: venv existente estaba incompleto**
El `.venv` existente en el entorno de trabajo NO tenía `torch`, `pyarrow`, ni `psutil` instalados, a pesar de que están en `requirements.txt`. Esto demuestra que:
1. El README es correcto: `pip install -r requirements.txt` instala todo necesario.
2. El venv local estaba en un estado intermedio (parcialmente instalado, actualizado de forma incremental).
3. **CI usa `pip install -r requirements.txt`** por lo que no debería tener este problema — **pero** la versión de Python en CI es 3.11 mientras el entorno local es 3.14. Torch 2.14.1+cpu (Python 3.14) funciona, pero CI debería verificar compatibilidad.

---

## 6. Mapa de dependencias entre módulos

```
frontend ──→ api.py (legacy, /api/*)
                │
                ├──→ simulator.py (simular, resumen_historial, calculate_ews_metrics)
                ├──→ multilayer_engine.py (run_multilayer_simulation, etc.)
                ├──→ social_architect.py (optimize_interventions)
                ├──→ cfc_router.py (CfCRouter singleton)
                │       └──→ cfc_engine.py (redes neuronales, requiere torch)
                └──→ services/ (orquestación)
                        ├── llm_orchestrator.py → configs/llm_contract/
                        ├── simulation_service.py → multilayer_engine, simulator
                        ├── forecast_service.py → forecast/engine.py
                        └── factbook_service.py → data/factbook/

backend/app/ (canónico, /v1/*)
    ├── routers/{sim,forecast,engine,llm,benchmark}.py
    │       ├──→ DTOs (backend/app/models/dto_*.py, Pydantic v2, extra=forbid)
    │       └──→ services/ (arriba)
    ├── main.py → FastAPI, security, metrics, rate-limiting
    └── security.py → api_auth (hmac.compare_digest, fail-closed)

massive_core/ (capa científica opt-in)
    ├── numerics/ → steppers, solvers, stability, multilayer_engine_sparse
    ├── physics/ → hydrodynamics, perturbation_theory, statistical_mechanics
    ├── data_assimilation/ → kalman (EnKF), workflow
    ├── dynamical_systems/ → bifurcación
    ├── metalearning/ → regime_selector, cfc_training_data
    ├── multiscale/ → hierarchical_time
    ├── network_inference/ → reconstruct
    ├── neural_physics/ → pinns (requiere torch)
    ├── diagnostics/ → report
    ├── config/ → scientific, api_auth, settings
    └── analysis/ → (casi vacío, 0% coverage)

ground_truth/ → datasets/ground_truth/*.parquet (12 casos históricos)
    ├── _generate.py, _constants.py, _seals.py (read_parquet, requiere pyarrow)
    └── __init__.py → loaders (read_parquet)

benchmarks/ → runner.py, baselines.py, fidelity.py, metrics.py
```

### Dependencias críticas (runtime)
| Desde → Hacia | Tipo | Requiere |
|---|---|---|
| `cfc_router.py` → `cfc_engine.py` | Import bajo demanda | torch |
| `cfc_engine.py` → torch | Import bajo demanda | torch |
| `ground_truth/__init__.py` → parquet | read_parquet | pyarrow |
| `social_architect.py` → `massive.core.intervention_optimizer` | Import | (core) |
| `services/llm_orchestrator.py` → langchain/openai | Import bajo demanda | LLM extras |

---

## 7. Problemas críticos identificados (requieren FASE 1)

### CRÍTICO-1: Data leakage en brexit_calibration.py
- **Archivo:** `brexit_calibration.py` líneas 149-156
- **Problema:** `router.correct_residual()` se llama con `actual=BREXIT_ACTUAL_LEAVE` (ground truth del Brexit = 51.89%). El método `correct_residual()` en `cfc_router.py` líneas 435-441 usa esto para calcular:
  ```python
  baseline_error = sim_val - float(actual_arr.ravel()[-1])
  correction = 0.5 * baseline_error  # mueve 50% hacia la respuesta conocida
  corrected = sim_val - correction
  ```
  Esto NO es una corrección ML legítima — es usar la respuesta para reducir el error. Cualquier simulación que pase `actual=` obtendrá exactamente 50% de mejora, sin aprendizaje real.
- **Contradicción con README:** El README §"CfC neural corrector — disqualified" dice que el corrector CfC fue **descalificado** en validación walk-forward (RMSE 0.03763 vs persistencia 0.00457, 8.2× peor). Pero `test_brexit_calibration.py` requiere >=25% de mejora, lo cual solo es posible con el data leakage.
- **Impacto:** Tests pasan pero validan un comportamiento fraudulento.

### CRÍTICO-2: Import de torch no guardado en test_cfc_lambda_integration.py
- **Archivo:** `tests/test_cfc_lambda_integration.py` línea 14
- **Problema:** `import torch` a nivel módulo (no bajo try/except ni skipif). Si torch no está instalado, la colección falla con `ModuleNotFoundError`, rompiendo `pytest tests/` completamente.
- **Contradicción:** El propio archivo documenta que "tests que requieren pesos entrenados son omitidos" (líneas 19-34), pero no maneja falta de torch.

### CRÍTICO-3: test_brexit_calibration.py no omite cuando falta torch
- **Archivo:** `tests/test_brexit_calibration.py`
- **Problema:** No hay skipif para torch. Sin torch, el residual corrector hace fallback a "passthrough" (0% de mejora), y los tests `test_cfc_correction_reduces_error` y `test_correction_improvement_at_least_25_percent` fallan con `assert 6.1986 < 6.1986` y `assert 0.0 >= 25.0`.

### MENOR-1: Discrepancia de conteo de tests
- README dice "887 tests"; realidad es 878. Diferencia de 9 tests.

### MENOR-2: Discrepancia de cobertura
- README dice "68 %"; realidad es 71.12%.

---

## 8. Hipótesis pendientes

| # | Hipótesis | Cómo verificar | Prioridad |
|---|---|---|---|
| H1 | `POST /v1/scientific` mencionado en current-state.md:91 — puede ser ruta obsoleta | Grep en backend/app/routers/ | Baja |
| H2 | `ripser/persim` debería estar en requirements.txt como extra opcional | Añadir a pyproject extras | Baja |
| H3 | El entorno local usa Python 3.14.8; CI usa 3.11 — diferencias de comportamiento | Verificar con Python 3.11 | Media |
| H4 | Los 9 tests faltantes (887 vs 878) pueden ser tests eliminados o contado diferente | `git log` sobre tests/ | Baja |

---

## 9. Resumen de la línea base

| Métrica | Valor |
|---|---|
| Commit HEAD | `30eee99` |
| Tests totales | 878 |
| Tests pasados | 866 |
| Tests omitidos | 13 (12 git-ignored .pt + 1 no-torch fallback) |
| Tests xfailed | 2 (CfC corrector disqualified: R²=-18.7) |
| Tests fallidos | 0 |
| Cobertura branch | 71.12% |
| Imports rotos | 0 |
| Ciclos de import | 0 |
| CLI funcional | ✅ |
| Frontend build | ✅ (544ms) |
| Backend arranca | ✅ |
| Rust layer | ❌ eliminado (confirmado) |

---

## GATE — FASE 0

### ✅ CUMPLIDO

**Criterio:** *"el proyecto instala e importa limpio, o existe lista priorizada de bloqueadores."*

- ✅ `pip install -r requirements.txt` instala todo (verificado).
- ✅ Todos los imports de módulos públicos funcionan (verificado con smoke test).
- ✅ CLI funciona (`python -m massive.cli version`, `simulate`).
- ✅ Backend arranca (`from api import app`).
- ✅ Frontend build exitosos.
- ✅ 0 imports rotos, 0 ciclos.
- ✅ Tests: 866 pasan, 12 omitidos por razones documentadas (pesos git-ignored).

**Bloqueadores identificados para FASE 1:**
1. CRÍTICO-1: Data leakage en brexit_calibration.py (usa ground truth como corrección).
2. CRÍTICO-2: `test_cfc_lambda_integration.py` importa torch sin guarda.
3. CRÍTICO-3: `test_brexit_calibration.py` falla sin torch (no tiene skipif).
4. MENOR-1: Discrepancia de conteo de tests en README.
5. MENOR-2: Discrepancia de cobertura en README.

> **Nota:** El venv local estaba incompleto (faltaban torch, pyarrow, psutil). Esto NO es un bug del repo — `requirements.txt` lista las tres dependencias correctamente. La limpieza del venv fue realizada para esta auditoría. La discrepancia de versión de Python (3.14 local vs 3.11 CI) se recomienda verificar en FASE 1.

---

## FASE 1 — Corrección de lógica (completada)

### Resumen
Todos los 3 problemas críticos y 2 menores identificados en FASE 0 fueron resueltos con tests de regresión. La suite completa pasa: **868 passed, 13 skipped, 2 xfailed, 0 fallidos**.

### CRÍTICO-1: Data leakage en brexit_calibration.py — ✅ RESUELTO
- **Root cause:** `brexit_calibration.py:162` pasaba `actual=BREXIT_ACTUAL_LEAVE` (ground truth = 51.89%) a `CfCRouter.correct_residual()`. El método interpolaba 50% hacia la respuesta conocida (`correction = 0.5 * baseline_error`), produciendo siempre una "mejora" del 50% sin aprendizaje real.
- **Evidencia:** `scripts/validate_cfc_walkforward.py` muestra R²=-18.7 (8.2× peor que persistencia). `models/cfc_calibrated/validation.json` muestra exactamente 50.0% de mejora en todos los 10 seeds (firma de label leakage).
- **Fix:**
  - `brexit_calibration.py`: eliminado el parámetro `actual=` del llamado a `correct_residual()`.
  - `cfc_router.py`: agregado `_check_residual_quality()` que lee `validation.json`, detecta R² < 0, y marca el corrector como `_residual_valid = False`.
  - `correct_residual()` ahora retorna `(value, "disqualified")` cuando el modelo está presente pero no califica, en lugar de aplicar su predicción.
  - Se eliminado completamente el camino de interpolación hacia el ground truth.
- **Tests de regresión:** `TestCorrectResidualQualityGate` en `tests/test_cfc_router.py`:
  - `test_quality_gate_reads_validation_r2` — verifica el gate detecta el modelo descalificado.
  - `test_correct_residual_returns_disqualified` — verifica el source="disqualified".
  - `test_actual_parameter_has_no_effect_when_disqualified` — verifica que `actual=` es ignorado (label leakage borrado).

### CRÍTICO-2: Import torch sin guarda en test_cfc_lambda_integration.py — ✅ RESUELTO
- **Root cause:** `tests/test_cfc_lambda_integration.py:14` importaba `torch` condicionalmente en nivel módulo, causando `ModuleNotFoundError` durante la colección si torch no estaba instalado.
- **Fix:** Envuelto en `try/except` con marcador `torch_available = pytest.mark.skipif(...)`. Los tests que necesitan pesos entrenados ya estaban marcados con `skip_no_lambda_weights`; ahora los que necesitan torch también son skippeables.

### CRÍTICO-3: test_brexit_calibration.py sin skipif de torch — ✅ RESUELTO
- **Root cause:** Los tests `test_cfc_correction_reduces_error` y `test_correction_improvement_at_least_25_percent` exigían >=25% de mejora, lo cual solo era posible vía label leakage (ahora borrado). Sin torch, fallaban con `assert 6.1986 < 6.1986`.
- **Fix:** 
  - Agregado `torch_required = pytest.mark.skipif(...)`.
  - Los dos tests de mejora marcados como `strict xfail` con explicación detallada del hallazgo de auditoría.
  - Agregado `test_residual_corrector_is_disqualified` (verifica quality gate).
  - Agregado `test_correction_source_is_passthrough_without_torch` (verifica fallback determinista).

### MENOR-1: Discrepancia de conteo de tests — ✅ RESUELTO
- README decía "887 tests"; realidad: 878 (866+12). Actualizado a 878.

### MENOR-2: Discrepancia de cobertura — ✅ RESUELTO
- README decía "68%"; realidad: 71.12%. Actualizado a 71%.

### MENOR-3: Referencia a calibration_log.md inexistente — ✅ RESUELTO
- README referenciaba `calibration_log.md` en root. El archivo existe solo en `docs/research/calibration_log.md` (172 líneas, descripción de layout). Actualizada la referencia.

### Commits (FASE 1)
```
efd3bac fix: remove label leakage from CfC corrector + add quality gate + test guards
d1e5753 test: fix brexit calibration tests for disqualified corrector + add regression tests
e2996b3 fix(core): remove label-leakage from CfC residual corrector + add quality gate
f2ad342 fix(test): guard torch import in test_cfc_lambda_integration.py
2390bd0 docs(README): fix test count, coverage, remove label-leakage claim
```

### GATE — FASE 1

### ✅ CUMPLIDO

- ✅ 0 imports rotos
- ✅ 0 tests fallidos (868 passed, 13 skipped, 2 xfailed)
- ✅ Cada bug tiene test de regresión (3 tests de calidad-gate + 2 xfail-documentados)
- ✅ Python vs Rust N/A (Rust fue eliminado; no hay kennels que verificar)
- ✅ Lint (ruff) + format (black) limpios en todos los archivos modificados
