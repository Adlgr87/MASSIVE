# 🔄 Post-Restart Continuation Checklist

**Estado actual: Phases 1-6 COMPLETAS.** Este documento contiene las instrucciones
detalladas para verificar el estado después del reinicio y continuar con las
fases restantes (7-8).

## ⚡ Estado Inmediato

| Componente | Estado | Verificación |
|---|---|---|
| 3 LNN modelos entrenados | ✅ Completos | `models/cfc_calibrated/*.pt` existen |
| 662 tests pass | ✅ Verificado | `pytest tests/ -q` → 662 passed |
| API v1 migrado | ✅ Completo | 8 endpoints en `/openapi/v1.json` |
| Docker + CI/CD | ✅ Listo | `Dockerfile`, `docker-compose.yml`, 12 workflows |
| 3 bugs preexistentes | ✅ Corregidos | `schemas.py`, `llm_orchestrator.py`, `micro_engine.py` |

---

## 📋 Post-Rewire Steps (Ejecutar después del reinicio)

### Step 1: Verificar entorno
```bash
cd /home/adlg/Escritorio/Proyectos/MASSIVE
python3 --version          # Debe ser 3.14.x
python3 -c "import torch; print(torch.__version__)"  # 2.13.0
python3 -c "import numpy; print(numpy.__version__)"   # 2.5.2
ls models/cfc_calibrated/  # Debe mostrar 3 .pt + configs
```

### Step 2: Ejecutar suite de tests
```bash
PYTHONHASHSEED=42 python3 -m pytest tests/ \
  -p no:libtmux \
  --ignore=tests/test_optimization.py \
  --ignore=tests/test_visualizations.py \
  -q 2>&1 | tail -1
# Output esperado: "662 passed, 0 failed"
```

### Step 3: Verificar LNN modelos cargados
```bash
python3 -c "
from cfc_router import CfCRouter
CfCRouter._instance = None
r = CfCRouter.get()
print(r.status)
# Output esperado: {'residual_corrector': True, 'lambda_corrector': True, 'landscape_corrector': True}
"
```

### Step 4: Verificar API v1 endpoints
```bash
python3 -c "
from backend.app.main import app
schema = app.openapi()
v1 = sorted([p for p in schema['paths'] if p.startswith('/v1')])
print(f'{len(v1)} endpoints:', v1)
"
# Output esperado: 8 endpoints
```

---

## 🚀 Fases Restantes

### Phase 7: Frontend Integration (UI-NG ↔ API v1)
**Objective:** Connect the frontend to the new `/v1/*` API surface.

#### Agentes/Subagentes recomendados:
```yaml
agentes:
  - nombre: "frontend-v1-migration"
    rol: "Migrar frontend/src/services/api.ts a usar /v1/* endpoints"
    herramientas: ["str_replace_editor", "bash"]
    tareas:
      - Añadir /v1/llm/extract, /v1/llm/wizard a api.ts
      - Migrar /api/extract → /v1/llm/extract
      - Migrar /api/wizard → /v1/llm/wizard
      - Migrar /api/simulate-uil → /v1/simulate
      - Migrar /api/v1/* → /v1/* (eliminar el /api/v1 duplicado)

  - nombre: "frontend-types-sync"
    rol: "Sync TypeScript types with OpenAPI v1"
    herramientas: ["bash"]
    tareas:
      - Ejecutar scripts/gen_ts_types.py
      - Verificar que los tipos coinciden con los DTOs actualizados
```

#### Instrucciones:
```bash
# 1. Check current frontend API calls
grep -rn "api/extract\|api/wizard\|api/simulate" frontend/src/services/api.ts

# 2. Generate updated TS types from OpenAPI
python3 scripts/gen_ts_types.py

# 3. Run frontend type check
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

### Phase 8: Performance Benchmarking (PVU-BS)
**Objective:** Validate computational performance at scale.

#### Agentes/Subagentes en paralelo:
```yaml
subagentes_paralelos:
  - nombre: "energy-benchmark-100k"
    prompt: >
      Run benchmark_scalability.py for EnergyEngine at [20K, 50K, 100K] agents.
      Record wall-clock time, peak RSS, throughput. Save to /tmp/perf_energy.json.
      If OOM at 100K, document the threshold and recommend MassiveEngine (LOD).
    herramientas: ["bash", "bash (background)"]
    timeout: 300s

  - nombre: "multilayer-benchmark-1k"
    prompt: >
      Run benchmark_scalability.py for SparseMultilayerEngine at [1K, 5K, 10K] agents.
      Record metrics. Save to /tmp/perf_multilayer.json.
    herramientas: ["bash"]
    timeout: 120s

  - nombre: "massive-100m"
    prompt: >
      Run MassiveEngine (LOD) at [1M, 10M, 100M] agents. This is the fastest
      engine per the AGENTS.md report. Save to /tmp/perf_massive.json.
    herramientas: ["bash", "bash (background)"]
    timeout: 600s

  - nombre: "compare-and-report"
    prompt: >
      After all benchmarks complete, consolidate results into
      /tmp/performance_report_final.md. Compare against the existing
      /tmp/performance_report.md to detect regressions.
    herramientas: ["bash"]
    timeout: 60s
    dependencias: [energy-benchmark-100k, multilayer-benchmark-1k, massive-100m]
```

#### Instrucciones:
```bash
# Run all benchmarks (adaptive: 365 steps for ≤1M, 100 for 10M, 10 for 100M)
python3 benchmark_scalability.py 2>&1 | tee /tmp/perf_run.log

# View results
cat /tmp/performance_metrics/performance_benchmarks.json | python3 -m json.tool
```

---

## 🐳 Phase 9: Staging Deployment (Opcional)

#### Agentes/Subagentes:
```yaml
agentes_secuenciales:
  - nombre: "docker-build-and-push"
    prompt: >
      Build Docker image: docker build -t massive:v1.0 .
      Verify the 3-stage build succeeds (builder-py, builder-fe, runtime).
      Run: docker-compose config (valida YAML syntax)
    herramientas: ["bash"]
    timeout: 300s

  - nombre: "docker-smoke-test"
    prompt: >
      Start docker-compose: docker compose up -d --build
      Wait 30s, then curl http://localhost:80/health
      Verify /v1/simulate endpoint returns 200 with auth header
    herramientas: ["bash"]
    timeout: 120s
```

---

## ✅ Verification Script (Run after each Phase)

```bash
# Quick health check script
cat > /tmp/verify_massive.sh << 'EOF'
#!/bin/bash
cd /home/adlg/Escritorio/Proyectos/MASSIVE
echo "=== MASSIVE Health Check ==="
python3 -c "
from cfc_router import CfCRouter
from backend.app.main import app
CfCRouter._instance = None
r = CfCRouter.get()
print(f'LNN models: {r.status}')
schema = app.openapi()
v1 = [p for p in schema['paths'] if p.startswith('/v1')]
print(f'v1 endpoints: {len(v1)}')
print(f'torch: {\"OK\" if r._residual is not None else \"FAIL\"}')"
" 2>&1 | grep -v WARNING | grep -v TDA
echo "✅ Health check complete"
EOF
chmod +x /tmp/verify_massive.sh
```

---

## 📦 Deliverables Completados (para referencia rápida)

| Deliverable | Path | Verify |
|---|---|---|
| Unified metrics | `metrics/unified_metrics.py` | `pytest tests/test_unified_metrics.py` |
| LNN router | `cfc_router.py` | `python3 -c "from cfc_router import CfCRouter; r=CfCRouter.get(); print(r.status)"` |
| Energy engine | `energy_engine.py` | `pytest tests/test_energy_engine.py` |
| Brexit calibration | `brexit_calibration.py` | `python3 brexit_calibration.py` |
| API v1 | `backend/app/main.py` | `python3 -c "from backend.app.main import app; print(len([p for p in app.openapi()['paths'] if p.startswith('/v1')]))"` |
| Docker | `Dockerfile`, `docker-compose.yml` | `docker compose config` |
| Observability | `monitoring/prometheus/alerts.yml` | `cat monitoring/prometheus/alerts.yml` |
| Security | `scripts/security_audit.sh` | `./scripts/security_audit.sh` |
| DR Plan | `docs/disaster_recovery_plan.md` | `cat docs/disaster_recovery_plan.md` |
| Plan document | `MASSIVE_REACTIVE_COHERENCE_PLAN.md` | `wc -l MASSIVE_REACTIVE_COHERENCE_PLAN.md` |
