# Auditoría de Production-Readiness — MASSIVE

> Auditor: Agent (Arena) · Fecha inicio: 2026-08-20 · HEAD: `288ba9a` (main)
> Entorno de verificación: Python 3.11.2 (venv limpio), Node 22.22.3, pytest 8, ruff/black/mypy actuales.
> Sin Docker ni toolchain Rust en el sandbox (limitación documentada; esas verificaciones se delegan a CI).
>
> **Estado Hito 0 (2026-08-20, rama arena/01a01fbd-massive): COMPLETO.**
> Suite completa: 521 tests verdes sin exclusiones (~35 s); ruff/black/mypy-slice limpios; `npm run build` verde; docs de auditoría añadidos. Pendiente de verificación en CI tras el merge.

---

## 1. Estado global

| Dimensión | Estado | Evidencia clave |
|---|---|---|
| Instalación de dependencias | ✅ OK | `pip install -r requirements.txt` exitoso; `pip-audit` → 0 vulnerabilidades conocidas |
| Tests | ❌ | 483 passed / 2 failed / 2 módulos sin colectar (import roto) |
| Lint/Format/Types | ❌ | ruff 28 errores; black 2 archivos; mypy slice 1 error |
| Frontend build | ❌ | Rollup no resuelve alias `@/` |
| Docker | ❌ (CI) | workflow `Docker E2E Health` failure en main |
| CI en main | ❌ | 7/12 workflows en failure (incl. tests, lint, frontend, docker, publish) |
| Secretos en árbol actual | ✅/⚠️ | sin secretos activos en el árbol; **token Zapier en historial** (requiere rotación del owner) |
| Docs vs realidad | ❌ | quickstart README roto (`app.py` inexistente); signoff describe Makefile inexistente |

## 2. Matriz de riesgos

Severidad: 🔴 crítico · 🟠 alto · 🟡 medio · 🔵 bajo. Prob./Impacto: A(lta)/M(edia)/B(aja).

| ID | Área | Hallazgo | Evidencia | Sev | Prob | Imp | Corrección propuesta | Riesgo reg. | Criterio de aceptación |
|----|------|----------|-----------|-----|------|-----|----------------------|-------------|------------------------|
| SEC-01 | Secretos | Token Zapier MCP (108 chars) queda en historial git público (commit `dc2240c`, `.codebuff/config.json`); borrado en PR #81 pero sin rotar | `gh api repos/.../commits/dc2240c...` → campo `ZAPIER_MCP_TOKEN` (valor redactado en este informe) | 🔴 | A | A | **Rotar el token en Zapier (acción del owner)**; opcional: purga de historial (destructivo, requiere aprobación) | n/a (acción externa) | Token antiguo invalidado por el owner; `gitleaks` limpio en HEAD |
| SEC-02 | Auth | `api.py` valida `MASSIVE_ENV == "dev"` pero el valor documentado/usado en el backend canónico es `"development"` → con `MASSIVE_ENV=development` sin `MASSIVE_API_KEY`, legacy responde 503 en vez del fallback dev documentado | `api.py:24` vs `backend/app/security.py:50-53` vs `.env.example:8` | 🟠 | A | M | Unificar semántica de entornos en un solo helper compartido | B | Test que cubra dev/staging/production en ambos backends |
| SEC-03 | Auth | Comparación de API key no constant-time (`!=`) en ambos backends raíz | `api.py:29`, `backend/app/security.py:60` | 🟡 | B | M | `hmac.compare_digest` | B | Test unitario + revisión |
| SEC-04 | Auth | Fallback `dev-secret-key` documentado en README; si alguien despliega con `MASSIVE_ENV` distinto de production acepta clave conocida | `README.md` (tabla endpoints), `backend/app/security.py:53` | 🟡 | M | A | Warning en arranque + negar fallback salvo `development` explícito (ya casi lo hace); documentar | B | Test: `staging` sin key → 503 (ya se cumple en backend canónico; añadir a legacy) |
| OPS-01 | CI | main rojo desde PR #84 (7/12 workflows); PR se mergueó sin gates | `gh run list` run 32084191350 etc. | 🔴 | A | A | Arreglar bloqueos + branch protection (acción owner) | B | Todos los workflows esenciales verdes en main |
| TEST-01 | Tests | `tests/test_llm_endpoint.py` y `tests/test_llm_orchestrator_coverage.py` no importan (`create_app` ya no existe en `backend.app.main`) — reescritos en PR #84 contra contrato del kit UI-NG | `pytest --collect-only` → 2 ImportError; contrato canónico en `configs/llm_contract/massive_llm_contract.json` | 🔴 | A | M | Reescribir contra contrato canónico v1.1.0 (`app` + `X-API-Key`) | B | `pytest tests/` colecta y pasa sin exclusiones |
| TEST-02 | Tests | `test_estimate_intervention_cost` pasa array 1D a función documentada como matriz 2D | `tests/test_factbook_integration.py:232` vs `massive/core/intervention_optimizer.py:275` | 🟠 | A | M | Corregir el test (reshape a `(n_phases, n_agents)` + seed) | B | Test pasa; función intacta |
| TEST-03 | Tests | `test_describe_families_smoke_4clusters`: fixture de 20 sims hace imposible k=4 (`max_k=n//10=2`) | `micro_engine.py` `_kmeans_fallback`; experimento: con 60 sims silhouette k=4=0.952 | 🟠 | A | M | Fixture `n_per=15` (60 sims); sin tocar el motor | B | Test pasa; `test_micro.py` sigue verde |
| FE-01 | Frontend | `vite.config.ts` sin `resolve.alias` para `@` → build roto (CI Frontend + Docker build + TS validate en cascada) | `npm run build` → Rollup error `@/components/ui/button`; `frontend/vite.config.ts` | 🔴 | A | M | Añadir alias `@ → ./src` (patrón estándar Vite) | B | `npm run build` exitoso localmente; workflow verde |
| LINT-01 | Calidad | ruff 28 errores + black 2 archivos + mypy 1 error → workflow Lint rojo | `/tmp/ruff.txt`, `/tmp/black.txt`, `/tmp/mypy.txt` | 🟠 | A | M | `ruff --fix` + `black` en 2 archivos; fix tipado en `services/llm_orchestrator.py:683` | B | `ruff check .` y `black --check .` y slice mypy → 0 errores |
| DOCS-01 | Docs | README Quick Start referencia `python app.py` (Streamlit) inexistente; streamlit no está en requirements | `ls app.py` → no existe; `grep streamlit requirements.txt` → vacío | 🟠 | A | M | Reemplazar quickstart por API/UI reales; decidir destino de `/ui/` (streamlit) en nginx+supervisord | B | README ejecutado desde clonación limpia |
| OPS-02 | Contenedores | supervisord arranca `streamlit` (binario no instalado en imagen) → reinicio eterno dentro del contenedor; puerto 8501 y ruta `/ui/` muertos | `supervisord.conf:23-24`, `requirements.txt` sin streamlit | 🟠 | A | M | Quitar programa streamlit + puerto 8501 + location `/ui/` (o instalar streamlit si el owner lo quiere) | B | Contenedor arranca sin procesos en respawn loop (verificable en CI docker-e2e) |
| ARCH-01 | Arquitectura | 3 backends/contratos conviven; `backend/app/services/llm_orchestrator.py` es un duplicado huérfano con contrato divergente (riesgo de que alguien lo cablee) | `ls backend/app/services/`, diff de contratos | 🟡 | M | M | Marcar/aislar el kit UI-NG; eliminar el duplicado huérfano tras caracterización | M | Ningún import al duplicado; contract tests del canónico |
| ARCH-02 | Arquitectura | Kit `massive-ui-ng/` completo (backend+frontend+tests+infra) mezclado en el árbol del repo; sus tests no corren en CI raíz | `massive-ui-ng/README.md` ("NO es standalone") | 🟡 | M | M | Decisión de producto: fusionar de verdad o mover a subdir ignorado — **requiere decisión del owner** | M | Docs de arquitectura reflejan la decisión |
| HYG-01 | Higiene | Archivos basura: `0`, `test-zapier.txt`, `.github/test-zapier-dir.txt`, `README.backup.md`, `site/` (build MkDocs commiteado) | `ls` raíz; `git ls-files site/` | 🔵 | A | B | Eliminar basura; ignorar `site/` | B | Árbol limpio; CI docs sigue verde |
| PERF-01 | Rendimiento | Sin baseline reproducible de rendimiento en CI/CD verificable desde clonación limpia (benchmarks existen pero informales) | `benchmarks/`, `benchmark_scalability.py` (con errores de lint) | 🟡 | M | M | Crear `docs/performance/baseline.md` con método reproducible | B | Baseline documentado + script ejecutable |
| REL-01 | Release | Sin tags, sin releases, CHANGELOG mínimo; publish depende de tags que nunca se crearon | `git tag` → vacío; `gh release list` → vacío | 🟡 | M | M | Checklist de release + flujo semver documentado | B | `docs/release-checklist.md` ejecutado en un RC |

### Riesgos detectados y descartados (con evidencia)

- **Secretos en árbol actual**: regex de patrones (sk-, gsk_, xox, AKIA, ghp_, hf_, Bearer largos) sobre `.py/.md/.yml/.json/.txt/.ts/.sh` → 0 hallazgos.
- **Vulnerabilidades de dependencias Python**: `pip-audit -r requirements.txt` → "No known vulnerabilities found" (2026-08-20).
- **gitleaks en HEAD**: workflow `Secret scan` verde en main.

## 3. Plan por hitos

### Propuesta de mejora CI (requiere owner — el agente no puede pushear `.github/workflows/*`)

`secret_scan.yml` actual usa `gitleaks/gitleaks-action@v2`, que ante push de rama nueva/forzada (sin `before` válido) escanea el **historial completo heredado** y falla siempre por el token Zapier histórico (SEC-01). Variante determinista propuesta (escanear exactamente el cambio propuesto, binario pinneado):

```yaml
name: Secret scan
on: [pull_request, push]
permissions:
  contents: read
jobs:
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - id: range
        run: |
          set -eu
          if [ "${{ github.event_name }}" = "pull_request" ]; then
            RANGE="origin/${{ github.base_ref }}...HEAD"
          elif [ -n "${{ github.event.before }}" ] && git cat-file -e "${{ github.event.before }}"^{commit} 2>/dev/null; then
            RANGE="${{ github.event.before }}..HEAD"
          else
            RANGE="HEAD~1..HEAD"
          fi
          echo "range=${RANGE}" >> "$GITHUB_OUTPUT"
      - run: |
          set -eu
          VERSION=8.24.3
          curl -sL "https://github.com/gitleaks/gitleaks/releases/download/v${VERSION}/gitleaks_${VERSION}_linux_x64.tar.gz" | tar xz -C /usr/local/bin gitleaks
          gitleaks git --redact --config .gitleaks.toml --verbose --log-opts "${{ steps.range.outputs.range }}"
```

### Hito 0 — Desbloquear ejecución y reproducibilidad (S)
**Objetivo:** CI verde en lo esencial; clonación limpia funciona.
- T0.1 (TEST-01/02/03): reparar 2 módulos de tests + 2 tests contra contrato canónico. [S/M] — rollback: revert commit.
- T0.2 (FE-01): alias Vite. [S]
- T0.3 (LINT-01): ruff/black/mypy. [S]
- Criterio: `pytest tests/`, `ruff`, `black --check`, `npm run build`, slice mypy — todos verdes localmente.

### Hito 1 — Seguridad crítica/alta (S/M)
- T1.1 (SEC-02/03): unificar helper de entornos + `compare_digest` + tests. [M]
- T1.2 (SEC-01): solicitar rotación del token Zapier (owner). [acción humana]
- Criterio: tests de auth cubren dev/staging/production; comparación constant-time.

### Hito 2 — Correctitud funcional y contratos (M)
- T2.1 (ARCH-01): eliminar duplicado huérfano tras caracterización. [M]
- T2.2 (DOCS-01/Ops README): quickstart real. [S]
- T2.3 (OPS-02): supervisord sin streamlit fantasma. [S] *(cambia comportamiento Docker → aviso en PR)*
- Criterio: contract tests del endpoint LLM; README verificado; docker-e2e verde en CI.

### Hito 3 — Test suite, CI y calidad (M/L)
- T3.1: CI con gates obligatorios en PR (no solo push a main). [M]
- T3.2: smoke test de imagen en CI (ya existe `docker-e2e.yml`, mantener). [S]
- T3.3: umbral de cobertura razonable medido desde el actual (medir con `--cov`). [M]
- Criterio: PRs bloqueados si tests/lint/build fallan; cobertura reportada.

### Hito 4 — Observabilidad, contenedores y operación (M)
- T4.1: `/ready` que refleje dependencias reales; logs estructurados con request-id. [M]
- T4.2: runbooks completos (operations/incidents). [S]
- Criterio: runbooks ejecutables; health/readiness probados.

### Hito 5 — Rendimiento y escalabilidad (M)
- T5.1: baseline reproducible (`docs/performance/baseline.md`). [M]
- Criterio: benchmark ejecutable en <10 min que registre tiempo/memoria por motor.

### Hito 6 — Endurecimiento final y release candidate (M)
- T6.1: branch protection (owner), tag semver, CHANGELOG, release checklist ejecutado. [M]
- Criterio: definición estricta de "production-ready" (§5) cumplida y documentada.

## 4. Cobertura actual

Medida en este entorno: pendiente de ejecutar `pytest --cov` completo (Hito 3).
Referencia previa del repo (MASSIVE_PRODUCTION_SIGNOFF.md, 2026-08-16): 47% agregado (5142 stmts).
No se fija umbral arbitrario hasta medir en HEAD actual.

## 5. Definición de "production-ready" (checklist ejecutable)

- [ ] Clonación limpia + instalación + arranque documentados y verificados.
- [ ] Build Python/Rust/frontend aplicable verde (Rust: vía CI mientras el sandbox no tenga toolchain).
- [ ] Docker/Compose construye y pasa smoke (CI).
- [ ] Rutas y flujos críticos con tests automatizados verdes.
- [ ] Sin fallos bloqueantes ni vulns críticas/altas sin aceptación explícita documentada.
- [ ] Secretos fuera del repo y de los logs.
- [ ] Configuración tipada, validada, segura por defecto.
- [ ] Health/readiness funcionales.
- [ ] Logs operables + métricas mínimas + runbooks.
- [ ] CI protege main (branch protection — owner).
- [ ] Release/rollback/recuperación documentados y probados.
- [ ] Benchmarks con baseline; optimizaciones con evidencia.
- [ ] README/docs de producción verificados desde cero.
- [ ] Cambios en PRs pequeños con pruebas.
