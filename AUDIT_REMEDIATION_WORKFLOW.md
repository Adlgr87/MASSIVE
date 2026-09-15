# WORKFLOW DE REMEDIACIÓN — MASSIVE

**Derivado de:** `AUDIT_REPORT_2026-09-15.md` (148 hallazgos, commit `473b04a6`)
**Fecha:** 2026-09-15
**Formato:** plan de ejecución por olas, listo para asignar a un equipo de agentes pre-configurado

---

## 0. CONVENCIONES DE ESTE DOCUMENTO

Cada tarea se identifica con `W{ola}-T{nn}` y declara cinco campos:

| Campo | Significado |
|---|---|
| **Hallazgos** | IDs del reporte de auditoría que la tarea cierra (o avanza) |
| **Resultado esperado** | El estado del repositorio al terminar — no el procedimiento |
| **Criterio de aceptación** | Comandos ejecutables y su salida esperada. Si el comando no pasa, la tarea no está hecha |
| **Depende de** | IDs de tareas que deben estar cerradas antes de empezar |
| **Tamaño** | XS · S · M · L · XL (mismo criterio que el reporte) |

Reglas globales que aplican a **todas** las tareas:

- **G-1 · No regresión de los 17 hallazgos 🟢.** Los activos `D1-007` `D1-010` `D2-007` `D2-015` `D3-015` `D3-020` `D4-013` `D5-017` `D5-018` `D6-018` `D6-019` `D7-017` `D7-018` `D8-008` `D8-009` `D8-012` `D9-011` deben seguir cumpliéndose al cierre de cada ola. El gate `make verify` de `W0-T01` los incluye.
- **G-2 · Un commit por tarea**, con el ID de tarea y los IDs de hallazgo en el mensaje (`fix(W1-T01): init CfC fallback attrs [D1-001 D1-003]`).
- **G-3 · Ninguna tarea introduce superficie nueva** (módulo, endpoint, workflow, documento, paquete) salvo que el resultado esperado lo requiera explícitamente. Es el correctivo del Patrón 9 del reporte.
- **G-4 · Los criterios de aceptación se ejecutan desde la raíz del repo**, en un venv con `pip install -r requirements.txt` y nada más, salvo que la tarea diga lo contrario.
- **G-5 · Cuando una tarea declare una decisión binaria** (p. ej. `D5-008`: torch duro vs. fallback real), la decisión se registra en `docs/architecture/CANONICAL_SOURCES.md` antes de ejecutar, y se cita el ID del hallazgo.
- **G-6 · Orden dentro de la ola:** los tracks son paralelizables entre sí; dentro de un track las tareas son secuenciales.

---

## 1. PRECONDICIÓN EXTERNA

**PE-1 · Restaurar la ejecución de GitHub Actions.** Los 13 workflows fallan por bloqueo de facturación (`D7-001`). Ninguna tarea de este plan depende de que PE-1 esté resuelta — todas incluyen verificación local — pero **las olas 3, 4 y 5 no pueden declararse cerradas** sin al menos un run completo verde en `main`. PE-1 está fuera del alcance del código.

**PE-2 · Decisión sobre el nombre de distribución en PyPI.** `pyproject.toml` publica `massive`. Verificar disponibilidad antes de `W3-T01`; si está tomado, la decisión de renombrado entra en `W3-T01` y afecta a `D8-002`.

---

## 2. GRAFO DE DEPENDENCIAS Y RUTA CRÍTICA

```
                         ┌──────────────────────────── WAVE 0 ────────────────────────────┐
                         │  W0-T01 harness+baseline   W0-T02 gobernanza   W0-T03 registro │
                         └───────────────┬──────────────────────┬─────────────────────────┘
                                         │ (todas las olas)     │
        ┌────────────────────────────────┼──────────────────────┼───────────────────────────────┐
        │                                ▼                      ▼                               │
        │  ┌───────────────────────── WAVE 1 · DESBLOQUEO (10 tareas, 5 tracks paralelos) ─────┐│
        │  │  A  W1-T01 ─► W1-T02 ─► W1-T03          B  W1-T04 ─► W1-T05                       ││
        │  │  C  W1-T06 ─► W1-T07                    D  W1-T08                                 ││
        │  │  E  W1-T09 ─► W1-T10                                                              ││
        │  └──────┬──────────────────────────┬──────────────────────────────────────────────────┘│
        │         │                          │                                                   │
        │         ▼                          ▼                                                   │
        │  ┌──── WAVE 2 · CANÓNICO (10 tareas, 4 tracks paralelos) ────┐                         │
        │  │  A  W2-T01 ─► W2-T02 ─► W2-T03                            │                         │
        │  │  B  W2-T04 ─► W2-T05                                      │                         │
        │  │  C  W2-T06 ─► W2-T07 ─► W2-T08                            │                         │
        │  │  D  W2-T09 ─► W2-T10                                      │                         │
        │  └──────┬────────────────────────────────────────────────────┘                         │
        │         │                                                                              │
        │         ▼                                                                              │
        │  ┌──── WAVE 3 · BUILD Y DESPLIEGUE (5 tareas) ────┐                                     │
        │  │  W3-T01 ─► W3-T04          W3-T02   W3-T03     │                                     │
        │  │  W3-T05 (gate agregado, requiere W1+W2+W3-T01..04)                                   │
        │  └──────┬─────────────────────────────────────────┘                                     │
        │         │                                                                              │
        │         ├───────────────► ┌── WAVE 4 · VERDAD DOCUMENTAL (5 tareas, paralelas) ──┐      │
        │         │                 │  W4-T01 ─► W4-T05 · W4-T02 ─► W4-T04 · W4-T03        │      │
        │         │                 └──────────────────────┬───────────────────────────────┘      │
        │         │                                        │                                      │
        │         └───────────────► ┌── WAVE 5 · CONSOLIDACIÓN (6 tareas, secuencial en track) ─┐ │
        │                           │  W5-T01 ─► W5-T02 ─► W5-T04                               │ │
        │                           │  W5-T03 ─► W5-T05     W5-T06                               │ │
        │                           └──────────────────────┬────────────────────────────────────┘ │
        │                                                  │                                      │
        │                                                  ▼                                      │
        │                           ┌── WAVE 6 · RENDIMIENTO Y CIENCIA (4 tareas) ──┐             │
        │                           │  W6-T01 · W6-T02 · W6-T03 · W6-T04 (cierre)   │             │
        │                           └───────────────────────────────────────────────┘             │
        └─────────────────────────────────────────────────────────────────────────────────────────┘

RUTA CRÍTICA (la cadena más larga que determina la duración total):
  W0-T01 → W1-T01 → W1-T02 → W1-T03 → W2-T01 → W2-T02 → W3-T01 → W3-T04 → W5-T01 → W5-T02 → W6-T04

Ancho máximo de paralelismo:
  Wave 0 → 3 pistas   Wave 1 → 5 pistas (10 tareas)   Wave 2 → 4 pistas (10 tareas)
  Wave 3 → 4 pistas   Wave 4 → 3 pistas              Wave 5 → 2 pistas   Wave 6 → 3 pistas
```

**Por qué este orden.** Tres restricciones de precedencia dominan:

1. **`W1-T01` precede a casi todo.** Mientras `import simulator` falle sin torch, no se puede ejecutar el job `core` de CI, no se puede medir cobertura de forma estable, y 21 archivos de test no se recolectan. Es una corrección de una línea con el mayor radio de desbloqueo del plan.
2. **`W2-T01` (DTOs cableados) precede a `W2-T02` (seguridad HTTP) y a `W3-T01` (empaquetado).** Las cotas anti-DoS de `D5-001` se implementan *como* DTOs; sin ellos, cada endpoint habría que protegerlo a mano y se repetiría el Patrón 5.
3. **`W5-T01` (decisión massive-ui-ng) precede a `W5-T02` (split de módulos).** No tiene sentido reorganizar la raíz mientras exista un tercer backend cuyo destino está sin decidir; se moverían archivos dos veces.

**Lo que puede empezar en cualquier momento** (sin dependencias): `W0-T02`, `W0-T03`, `W1-T04`, `W1-T05`, `W1-T06`, `W1-T08`, `W4-T02`, `W4-T03`, `W6-T02`.

---

## 3. WAVE 0 — Harness y gobernanza

Objetivo de la ola: que exista un comando único que mida el estado del repo, y que los 148 hallazgos sean trabajo seguible. Sin esta ola no hay forma de saber si las olas siguientes convergen — que es exactamente el fallo del Patrón 3.

---

### W0-T01 · Harness de verificación unificado + línea base

| | |
|---|---|
| **Hallazgos** | `D7-001` (gate local mientras Actions esté bloqueado) · `D7-018` · `D7-019` |
| **Tamaño** | S |
| **Depende de** | — |

**Resultado esperado.** Un target `make verify` ejecuta, en orden y con salida resumida por etapa: ruff, black --check, mypy-slice, pytest con cobertura, regeneración de tipos TS con diff, `mkdocs build --strict`, y el set de guardarraíles G-1. Existe `make verify-baseline` que escribe `reports/audit_baseline.json` con las cifras medidas (nº tests, passed, failed, coverage %, ruff count, black count, mypy count, LOC, entradas root). El archivo de línea base con los valores del commit `473b04a6` está commiteado. `make help` lista ambos targets. `CONTRIBUTING.md` documenta `make verify` como requisito pre-push.

**Criterio de aceptación.**
```bash
make help | grep -E "verify|verify-baseline"          # → 2 líneas
make verify-baseline && test -f reports/audit_baseline.json && echo OK
python -c "import json,sys; d=json.load(open('reports/audit_baseline.json'));
assert set(d) >= {'tests_total','tests_passed','tests_failed','coverage_pct','ruff_issues','black_files','mypy_errors'};
print('baseline keys OK:', sorted(d))"
make verify ; echo "exit=$?"                          # → rojo hoy; es la línea base, no un fallo de la tarea
```
Adicional: el bloque de guardarraíles G-1 dentro de `make verify` ejecuta al menos
```bash
python -m mkdocs build --strict                                    # D6-018
python -c "import ast,sys; [ast.parse(open(f).read(),f) for f in __import__('glob').glob('**/*.py',recursive=True) if '.venv' not in f]"   # D1-010
grep -rq "except:" --include="*.py" . && exit 1 || true            # D2-007
python scripts/todo_triage.py                                      # D2-015
pip-audit -r requirements.txt --no-deps                            # D5-017
python scripts/gen_ts_types.py && git diff --exit-code frontend/src/types/api.generated.ts   # D3-020
python - <<'PY'                                                    # D8-008 / D8-009 smoke
from simulator import simular, resumen_historial
h = simular({'opinion':0.5,'propaganda':0.7,'confianza':0.4,'opinion_grupo_a':0.72,
             'opinion_grupo_b':0.28,'pertenencia_grupo':0.65}, pasos=30, verbose=False)
assert resumen_historial(h)['pasos'] == 30
PY
```

---

### W0-T02 · Gobernanza mínima del repositorio

| | |
|---|---|
| **Hallazgos** | `D5-024` · `D8-006` |
| **Tamaño** | S |
| **Depende de** | — |

**Resultado esperado.** Existen `.github/ISSUE_TEMPLATE/{bug_report.yml, feature_request.yml, documentation.yml}` como formularios estructurados; `SECURITY.md` en root con canal de reporte privado y referencia a `docs/security/threat-model.md`; `.github/CODEOWNERS`; `.github/dependabot.yml` cubriendo `pip`, `npm` (ambos frontends), `github-actions` y `cargo`. Labels creados en el repo: `severity:critical`, `severity:high`, `severity:medium`, `area:engines`, `area:backend`, `area:frontend`, `area:docs`, `area:ci`, `area:security`, `area:packaging`, `area:perf`, `debt`, `good first issue`, `help wanted`.

**Criterio de aceptación.**
```bash
for f in .github/ISSUE_TEMPLATE/bug_report.yml .github/ISSUE_TEMPLATE/feature_request.yml \
         .github/ISSUE_TEMPLATE/documentation.yml SECURITY.md .github/CODEOWNERS .github/dependabot.yml; do
  test -f "$f" && echo "OK   $f" || echo "MISS $f"; done          # → 6 × OK
python -c "import yaml,glob; [yaml.safe_load(open(f)) for f in
  glob.glob('.github/ISSUE_TEMPLATE/*.yml')+['.github/dependabot.yml']]; print('YAML OK')"
gh label list --limit 100 | grep -cE "severity:|area:|debt|good first issue|help wanted"   # → ≥ 14
grep -c "threat-model" SECURITY.md                                                          # → ≥ 1
```

---

### W0-T03 · Registro trazable de los 148 hallazgos

| | |
|---|---|
| **Hallazgos** | `D1-007` (registro como RESUELTO) · `D8-012` (registro como RESUELTO) · habilita el seguimiento de los 146 restantes |
| **Tamaño** | S |
| **Depende de** | `W0-T02` (labels) |

**Resultado esperado.** Un archivo `docs/AUDIT_FINDINGS_TRACKER.md` con las 148 filas del reporte (ID · severidad · título · ola · tarea · estado · issue), y un issue de GitHub por cada hallazgo 🔴 y 🟠 (62 issues) etiquetado con su `severity:` y `area:` y con el ID del hallazgo en el título. Los 17 hallazgos 🟢 aparecen en el tracker con estado `GUARDRAIL` y sin issue. Los items ya resueltos (`D1-007`, `D8-012`, y la parte de `D5-018` relativa a `test-zapier.txt`) se marcan `RESUELTO` con la evidencia del reporte.

**Criterio de aceptación.**
```bash
grep -cE "^\| D[1-9]-[0-9]{3} \|" docs/AUDIT_FINDINGS_TRACKER.md    # → 148
grep -c "RESUELTO" docs/AUDIT_FINDINGS_TRACKER.md                   # → ≥ 3
grep -c "GUARDRAIL" docs/AUDIT_FINDINGS_TRACKER.md                  # → 17
gh issue list --label "severity:critical" --state open --limit 100 --json number | python -c \
  "import json,sys; print(len(json.load(sys.stdin)))"               # → 17
gh issue list --label "severity:high" --state open --limit 100 --json number | python -c \
  "import json,sys; print(len(json.load(sys.stdin)))"               # → 45
```

---

## 4. WAVE 1 · DESBLOQUEO

Objetivo de la ola: que `pip install -r requirements.txt && pytest tests/` funcione en un clone limpio, que `ruff`/`black` salgan 0, y que los artefactos de runtime dejen de estar versionados. Al cerrar esta ola, el repo pasa de "no se puede verificar" a "se puede verificar y está rojo en puntos concretos".

**Gate de cierre de ola W1:**
```bash
python -c "import simulator"                                  # sin torch → exit 0
python -m pytest tests/ --collect-only -q 2>&1 | tail -1      # → "681 tests collected"
python -m pytest tests/ -q 2>&1 | tail -1                     # → "0 failed"
ruff check . ; echo $?                                        # → 0
black --check . ; echo $?                                     # → 0
mypy . --ignore-missing-imports 2>&1 | tail -1                # → NO "Duplicate module named"
docker build -f Dockerfile.optimized . 2>&1 | head -1         # → NO "unknown instruction"
git status --porcelain | grep -cE "\.pt$|\.db$|repomix-output" # → 0
```

---

### Track A — Runtime e imports

#### W1-T01 · Atributos de fallback del router CfC + import de `extended_models`

| | |
|---|---|
| **Hallazgos** | `D1-001` · `D1-003` · cierra `D4-010` · habilita `D1-004`, `D1-009` |
| **Tamaño** | XS |
| **Depende de** | `W0-T01` |

**Resultado esperado.** `CfCRouter` inicializa `_lambda_corrector` y `_landscape_corrector` a `None` en `__init__`, de modo que `status` es evaluable con o sin torch. `simulator.py` importa las tres reglas desde su ubicación canónica `massive.core.extended_models`, y su rama `except` registra un warning (paridad con las ramas TDA y LangChain). `EXTENDED_MODELS_AVAILABLE` es `True` en un entorno normal.

**Criterio de aceptación.**
```bash
PYTHONPATH=/tmp/notorch python -c "import simulator; print('OK')"      # → OK   (torch bloqueado)
PYTHONPATH=/tmp/notorch python -c "import cfc_router;
print(cfc_router.CfCRouter.get().status)"                              # → dict con 6 claves, todas False
python -c "import simulator; assert simulator.EXTENDED_MODELS_AVAILABLE is True; print('OK')"
python -c "from extended_models import regla_bayesiana" 2>&1 | head -1  # → sigue fallando, ES ESPERADO
                                                                        #   (el shim lo crea W5-T04)
python -m pytest tests/test_cfc_router.py tests/test_cfc_engine.py -q 2>&1 | tail -1   # → 0 failed
PYTHONPATH=/tmp/notorch python -m pytest tests/test_cfc_router.py -q 2>&1 | tail -1    # → 0 failed
```

#### W1-T02 · Decisión y cierre sobre el fallback NumPy de `cfc_engine`

| | |
|---|---|
| **Hallazgos** | `D1-002` · `D5-008` (decisión binaria) |
| **Tamaño** | S (opción A) · L (opción B) |
| **Depende de** | `W1-T01` · `G-5` (decisión registrada) |

**Resultado esperado.** **Decisión A** (torch como dependencia dura): `torch` pasa a `[project] dependencies` y a `requirements.txt`; se elimina el bloque `torch = None` / `nn` falso y el warning que promete un fallback inexistente; los docstrings de `cfc_router.py` y `cfc_engine.py` dejan de afirmar "fallback transparente NumPy"; `pytest.yml` instala torch en los 4 jobs; `massive_core/neural_physics/pinns.py` deja de ser el único módulo con `import torch` desnudo sin documentación. **Decisión B** (fallback real): `from __future__ import annotations` + anotaciones cualificadas + una implementación NumPy de `CfCCell`/`CfCLambdaCorrector`/`CfCLandscapeModulator` con test de paridad contra la rama torch. Cualquiera de las dos: el mensaje de warning describe con exactitud lo que el código hace.

**Criterio de aceptación.**
```bash
# Decisión A:
python -c "import tomllib;d=tomllib.load(open('pyproject.toml','rb'));
assert any('torch' in x for x in d['project']['dependencies']); print('torch es dependencia base')"
grep -c "implementación NumPy fallback" cfc_engine.py cfc_router.py       # → 0 0
grep -c "fallback transparente" cfc_router.py                             # → 0
PYTHONPATH=/tmp/notorch python -c "import simulator" 2>&1 | head -1       # → ImportError claro, NO AttributeError
python -c "
import importlib.util as u
assert all(u.find_spec(m) for m in ['torch']); print('OK')"
# Ambas decisiones:
python -m pytest tests/ -q 2>&1 | tail -1                                 # → 0 failed
make verify 2>&1 | grep -E "ruff|black"                                   # → sin regresión vs. baseline
```

#### W1-T03 · Dependencias faltantes de test y de benchmark

| | |
|---|---|
| **Hallazgos** | `D4-006` · `D5-005` · cierra `D1-004` |
| **Tamaño** | S |
| **Depende de** | `W1-T02` |

**Resultado esperado.** `httpx` y `psutil` declarados donde corresponde (un `requirements-dev.txt` o el extra `dev` de pyproject, y `psutil` además en `requirements.txt` por ser import duro de `benchmark_scalability.py`). Extras nuevos en `pyproject.toml` para las capacidades opcionales: `gpu = ["cupy"]`, `tda = ["ripser","persim"]`, `clustering = ["hdbscan"]`, `social = ["tweepy","praw"]`. Los 4 jobs de `pytest.yml` comparten un único paso de instalación (composite action o archivo de requisitos común) en lugar de cuatro listas divergentes.

**Criterio de aceptación.**
```bash
python -c "import benchmark_scalability; print('OK')"                     # → OK
python -m pytest tests/ --collect-only -q 2>&1 | tail -1                  # → 681 tests collected, 0 errors
python -m pytest tests/test_api_security.py tests/test_backend_observability.py \
  tests/test_llm_endpoint.py -q 2>&1 | tail -1                            # → recolecta y corre
python - <<'PY'
import tomllib; d=tomllib.load(open('pyproject.toml','rb'))['project']['optional-dependencies']
assert {'gpu','tda','clustering','social'} <= set(d), sorted(d); print('extras OK:', sorted(d))
PY
diff <(grep -oE "pip install .*" .github/workflows/pytest.yml | sort -u) /dev/null | head -1
python -c "import yaml;s=open('.github/workflows/pytest.yml').read();
assert s.count('numpy>=1.26')<=1; print('instalación de deps unificada')"
```

---

### Track B — Build, Docker e higiene del árbol

#### W1-T04 · Dockerfiles y compose: sintaxis y ruta canónica

| | |
|---|---|
| **Hallazgos** | `D7-004` · `D1-011` · avanza `D7-005` |
| **Tamaño** | S |
| **Depende de** | — |

**Resultado esperado.** No queda ningún archivo de build con una línea que no sea sintaxis válida. El bucle de referencias cruzadas (`docker-compose.yml` → `single.yml` → `Dockerfile.optimized` → `Dockerfile`) se rompe: una sola pareja compose+Dockerfile es canónica y la otra está eliminada o movida a `docs/examples/` con banner. `README.md` y `README_ES.md` nombran explícitamente el camino canónico.

**Criterio de aceptación.**
```bash
head -1 Dockerfile.optimized 2>/dev/null | grep -qE "^#" && echo "comentado OK" || \
  test ! -f Dockerfile.optimized && echo "eliminado OK"
docker compose -f docker-compose.yml config -q && echo "compose OK"
grep -cE "docker-compose|Dockerfile" README.md                            # → ≥ 1 (camino documentado)
grep -c "LEGACY" docker-compose.yml docker-compose.single.yml 2>/dev/null  # → 0 (o solo existe uno)
```

#### W1-T05 · Higiene de artefactos: ignore efectivo, binarios, `.dockerignore`

| | |
|---|---|
| **Hallazgos** | `D5-019` · `D5-020` · `D5-021` · `D5-022` · `D7-020` · `D8-012` |
| **Tamaño** | S |
| **Depende de** | — |

**Resultado esperado.** `.gitignore` corrige `repomack` → `repomix` y su comentario de sección. Las reglas de ignore y el contenido trackeado dejan de contradecirse: o los `.pt` y los `reports/*.json` se declaran evidencia versionada (y se retiran las reglas que los prohíben) o se des-trackean y se mueven a LFS/artifacts. `data/ui_ng/runs.db` deja de estar trackeado. `.gitattributes` declara binarios `.pt .pth .npz .png .jpg .db .sqlite`. `.dockerignore` incluye los pesos CfC necesarios en la imagen, excluye `docs/ .github/ experiments/ reports/ site/ *.md massive-ui-ng/frontend/node_modules/`, y corrige el glob final `*.env.*\.backup`.

**Criterio de aceptación.**
```bash
grep -n "repomix-output" .gitignore                                       # → presente
grep -n "repomack" .gitignore                                             # → ausente
git ls-files | grep -cE "\.db$|\.sqlite$"                                 # → 0
git check-ignore -v repomix-output.xml                                    # → coincide con la regla
grep -cE "^\*\.(pt|pth|npz|png|jpg|db|sqlite) binary" .gitattributes      # → ≥ 1
python -c "
lines=open('.dockerignore').read().split('\n')
assert not any(l.strip().startswith('models/') for l in lines), 'models/ sigue excluido'
assert any('massive-ui-ng/frontend/node_modules' in l for l in lines)
assert not any(l.strip().endswith('\\\\.backup') for l in lines)
print('.dockerignore OK')"
docker build -f Dockerfile -t massive-audit . && \
  docker run --rm massive-audit python -c "
from pathlib import Path; assert (Path('models/cfc_calibrated/cfc_residual.pt')).exists(), 'sin pesos'
print('pesos CfC presentes en la imagen')"
```

---

### Track C — Lint y tipos

#### W1-T06 · Ruff y black a cero

| | |
|---|---|
| **Hallazgos** | `D2-001` · `D2-002` · `D2-017` (parcial: habilitar `FAST`, `RUF013`) |
| **Tamaño** | S |
| **Depende de** | — |

**Resultado esperado.** `ruff check .` y `black --check .` salen 0 sobre todo el repo, incluido `massive-ui-ng/`. Los `from __future__` vuelven a la primera línea en los 4 archivos afectados; los 6 `F841` de `energy_engine.py` quedan resueltos (por `W2-T07`, no con `noqa`); las dependencias FastAPI sin anotar (`FAST002`, 14) y los `Optional` implícitos (`RUF013`, 5) están corregidos. `black` y `ruff` quedan pinneados a versión exacta.

**Criterio de aceptación.**
```bash
ruff check . ; echo "ruff=$?"                                             # → 0
black --check . ; echo "black=$?"                                         # → 0
ruff check . --select F841 ; echo $?                                      # → 0 (sin noqa añadidos)
grep -c "noqa" energy_engine.py                                           # → 0 nuevos
ruff check . --select FAST002,RUF013 ; echo $?                            # → 0
python -c "
import re;s=open('pyproject.toml').read()+open('requirements-dev.txt').read() if __import__('os').path.exists('requirements-dev.txt') else open('pyproject.toml').read()
assert re.search(r'black[=><=~!]*=?\d+\.\d+\.\d+', s) or 'black==' in s; print('black pinneado')"
git diff --stat HEAD~1 -- '*.py' | tail -1                                # → sin cambios de comportamiento
make verify 2>&1 | grep -E "tests_passed"                                 # → sin regresión vs. baseline
```

#### W1-T07 · `mypy .` ejecutable + configuración única

| | |
|---|---|
| **Hallazgos** | `D2-004` · `D7-014` (parcial) |
| **Tamaño** | XS |
| **Depende de** | — |

**Resultado esperado.** `mypy .` ya no aborta por `Duplicate module named "backend"`: la configuración declara exclusiones para `massive-ui-ng/`, `frontend/`, `node_modules/`, `site/`, `dist/`, `build/`. La configuración de mypy vive en un solo archivo. El opt-out de `multilayer_engine_sparse` lleva asociado un número de issue.

**Criterio de aceptación.**
```bash
mypy . --ignore-missing-imports 2>&1 | grep -c "Duplicate module"          # → 0
mypy . --ignore-missing-imports 2>&1 | tail -1                             # → "Found N errors" (N medible)
test ! -f mypy.ini -o ! -f pyproject.toml || \
  python -c "import tomllib;print('tool.mypy' in tomllib.load(open('pyproject.toml','rb')).get('tool',{}))"
grep -cE "multilayer_engine_sparse" pyproject.toml mypy.ini 2>/dev/null
grep -nE "#.*issue|#.*[0-9]{2}" pyproject.toml mypy.ini 2>/dev/null | grep -i sparse   # → presente
```

---

### Track D — Documentación de bajo coste

#### W1-T08 · Correcciones documentales puntuales y metadata del repo

| | |
|---|---|
| **Hallazgos** | `D6-006` · `D6-013` · `D6-016` · `D6-017` · `D8-003` · `D8-004` |
| **Tamaño** | S |
| **Depende de** | — |

**Resultado esperado.** Las fechas imposibles de los tres reportes de root están corregidas o los reportes llevan banner `> ⚠️ HISTÓRICO — describe el commit {sha} del {fecha}`. El comando de MkDocs del README usa un puerto que no colisiona con la API. `.github/Agent_Copilot2` es `.github/agents/repo-surgeon.agent.md` con frontmatter YAML parseable. `.github/agents/my-agent.agent.md` está renombrado según su `name:` y sin el code fence envolvente. `LICENSE` es el texto canónico de Apache-2.0 con el aviso de copyright en el `APPENDIX`, y el año es coherente con la historia del proyecto. Los topics del repo no incluyen `streamlit` ni `scaleable`, e incluyen al menos 10 de los topics sugeridos en `D8-004`; la descripción expande el acrónimo.

**Criterio de aceptación.**
```bash
grep -cE "Fecha: 2025|Fecha:\*\* 2025|\*\*Fecha:\*\* 2025" REPORT_*.md     # → 0, o cada uno con banner HISTÓRICO
grep -c "HISTÓRICO" REPORT_BUGS.md REPORT_OPTIMIZATION.md REPORT_STRUCTURE.md
grep -nE "mkdocs serve" README.md README_ES.md | grep -vc ":8000"          # → ≥ 1 (puerto distinto)
python -c "
import yaml,glob
for f in glob.glob('.github/agents/*.agent.md'):
    t=open(f).read().lstrip()
    assert t.startswith('---'), f
    fm=t.split('---')[1]; yaml.safe_load(fm); print('frontmatter OK:', f)
assert len(glob.glob('.github/agents/*.agent.md'))>=2"
test ! -f .github/Agent_Copilot2 && echo "renombrado OK"
gh repo view --json licenseInfo --jq '.licenseInfo.key'                    # → apache-2.0
gh repo view --json repositoryTopics --jq '[.repositoryTopics[].name] |
  (index(.,"streamlit")==null and index(.,"scaleable")==null)'              # → true
gh repo view --json repositoryTopics --jq '.repositoryTopics | length'      # → ≥ 13
```

---

### Track E — Tests

#### W1-T09 · Los 12 tests fallantes: pesos CfC

| | |
|---|---|
| **Hallazgos** | `D4-001` |
| **Tamaño** | M |
| **Depende de** | `W0-T01` · `G-5` (decisión registrada) · `W1-T05` (si se opta por LFS) |

**Resultado esperado.** `pytest tests/` sale con 0 fallos en un clone limpio. Una de las tres rutas, decidida y registrada: **(a)** los tres pesos (`cfc_lambda_corrector.pt`, `cfc_landscape.pt`, `cfc_temperature.pt`) se publican vía Git LFS con `.gitattributes` configurado y `models/cfc_calibrated/` completo; **(b)** los 12 tests se convierten en `skipif(not _path.exists())` con un fixture de descarga documentado y un contador de skips visible en el resumen; **(c)** los pesos se regeneran en CI a partir de `train_cfc_*.py` sobre `datasets/`. La afirmación del README sobre la reducción de error del ~50 % en Brexit queda respaldada por la ruta elegida o se retira.

**Criterio de aceptación.**
```bash
rm -rf .venv-clean && python -m venv .venv-clean && . .venv-clean/bin/activate
pip install -q -r requirements.txt && python -m pytest tests/ -q 2>&1 | tail -1   # → "0 failed"
# ruta (a):
git lfs ls-files | grep -c "models/cfc_calibrated"                       # → ≥ 3
python -m pytest tests/test_cfc_lambda_integration.py tests/test_cfc_landscape_integration.py \
  tests/test_brexit_calibration.py -q 2>&1 | tail -1                     # → 12 passed
# ruta (b):
python -m pytest tests/ -q -rs 2>&1 | grep -c SKIPPED                    # → ≥ 12, y el resumen los lista
grep -c "50 %" README.md README_ES.md                                    # → 0, o respaldado por un reporte commiteado
```

#### W1-T10 · Unificación de la suite y fixtures reales

| | |
|---|---|
| **Hallazgos** | `D4-007` · `D4-008` · `D4-009` · `D4-014` (parcial) |
| **Tamaño** | S |
| **Depende de** | `W1-T09` |

**Resultado esperado.** Existe `tests/conftest.py` con: `sys.path` explícito, fixture autouse que resetea `CfCRouter._instance` entre tests, fixture que aísla `MASSIVE_ENV`, y fixture que redirige los archivos creados por efectos colaterales de import a `tmp_path`. Los 2 archivos de `massive-ui-ng/tests/` están dentro de `testpaths` o movidos a `tests/`. `tests/test_cfc_engine.py::test_import_no_crash_without_torch` ejercita de verdad el camino sin torch (subprocess con `torch` bloqueado) y pasa en ambas configuraciones. `addopts` ya no desactiva un plugin inexistente.

**Criterio de aceptación.**
```bash
test -f tests/conftest.py && grep -cE "@pytest.fixture" tests/conftest.py     # → ≥ 3
python -c "import tomllib;p=tomllib.load(open('pyproject.toml','rb'));
o=p['tool']['pytest']['ini_options'];
assert 'libtmux' not in o.get('addopts',''); print('addopts OK:', o['addopts'])"
python -m pytest tests/ -q -p no:randomly 2>&1 | tail -1                      # → 0 failed
python -m pytest tests/ -q 2>&1 | tail -1                                     # → mismo resultado (sin orden-dependencia)
python -m pytest tests/test_cfc_engine.py::TestCfCEngineImport -q 2>&1 | tail -1
PYTHONPATH=/tmp/notorch python -m pytest tests/test_cfc_engine.py::TestCfCEngineImport -q 2>&1 | tail -1
                                                                                # → ambos pasan
ls -A | grep -cE "massive_run.log|landscapes_cache.db"                          # → 0 tras correr la suite
```

---

## 5. WAVE 2 · CAMINO CANÓNICO SEGURO Y VERIFICABLE

Objetivo de la ola: que la superficie HTTP canónica valide lo que declara, que los fallos sean observables en lugar de silenciosos, y que los gates de CI dejen de tener válvulas de escape. Al cierre, `D5-001` (el hallazgo de seguridad más grave) está cerrado y `typecheck.yml` puede fallar.

**Gate de cierre de ola W2:**
```bash
curl -s -o /dev/null -w "%{http_code}" -X POST localhost:8000/v1/simulate \
  -H "X-API-Key: $K" -H "Content-Type: application/json" -d '{"pasos": 99999999}'   # → 422
curl -s -o /dev/null -w "%{http_code}" localhost:8000/metrics                        # → 401 (o 200 solo desde CIDR interno)
MASSIVE_ENV=production uvicorn backend.app.main:app & sleep 3
curl -s -o /dev/null -w "%{http_code}" -X POST localhost:8000/v1/simulate \
  -H "X-API-Key: dev-secret-key" -d '{}'                                             # → 401/503
python scripts/typecheck_slice.py ; echo $?                                          # → 0
grep -c "|| true" .github/workflows/lint.yml                                         # → 0
grep -c "continue-on-error" .github/workflows/typecheck.yml                          # → 0
grep -rn "except Exception" --include="*.py" backend services massive_core | \
  grep -c "pass$"                                                                    # → 0
```

---

### Track A — Contrato de la API

#### W2-T01 · DTOs Pydantic como cuerpos de request + cotas anti-DoS

| | |
|---|---|
| **Hallazgos** | `D3-004` · `D5-001` · avanza `D4-004`, `D2-003` |
| **Tamaño** | M |
| **Depende de** | `W1-T06` (para no mezclar diffs de formato) |

**Resultado esperado.** Los 6 routers canónicos tipan su cuerpo de request con modelos Pydantic (`extra="forbid"` + `Field(ge=…, le=…)`) en lugar de `dict[str, Any]`. Las cotas son explícitas y están en un solo sitio: `pasos ≤ 10 000`, `n_agents ≤ 200 000`, `max_intentos ≤ 10`, y las que correspondan a `forecast`, `benchmark`, `energy`, `architect`. `/openapi.json` publica esquemas reales por endpoint. El README describe cotas que existen en el camino que recomienda. Existen tests de contrato por router: payload válido → 200 con esquema; campo fuera de rango → 422; campo desconocido → 422; sin `X-API-Key` → 401.

**Criterio de aceptación.**
```bash
grep -rc "payload: dict\[str, Any\]" backend/app/routers/*.py | grep -v ":0"   # → vacío
python - <<'PY'
import json, urllib.request
spec = json.load(urllib.request.urlopen("http://127.0.0.1:8000/openapi.json"))
bodies = [p[m].get("requestBody", {}) for p in spec["paths"].values() for m in p if m in ("post","put")]
withschema = [b for b in bodies if b.get("content", {}).get("application/json", {}).get("schema", {}).get("$ref")]
assert len(withschema) >= 6, f"solo {len(withschema)} endpoints con esquema"
print(f"{len(withschema)} endpoints con DTO cableado")
PY
for body in '{"pasos":99999999}' '{"n_agents":99999999}' '{"max_intentos":999}' '{"campo_inventado":1}'; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -X POST localhost:8000/v1/simulate \
    -H "X-API-Key: $K" -H "Content-Type: application/json" -d "$body"); echo "$body → $code"; done
                                                                                 # → 422 en los 4
python -m pytest tests/test_api_contract.py -q 2>&1 | tail -1                    # → 0 failed
python scripts/typecheck_slice.py 2>&1 | grep -c "call-arg"                      # → reducción vs. baseline
```

#### W2-T02 · Endurecimiento de la superficie HTTP

| | |
|---|---|
| **Hallazgos** | `D5-009` · `D5-010` · `D5-013` · `D5-023` |
| **Tamaño** | M |
| **Depende de** | `W2-T01` |

**Resultado esperado.** `/metrics` requiere autenticación o está restringido por red. `MASSIVE_ENV` sin definir resuelve a un valor fail-closed (no a `development`); el fallback `dev-secret-key` exige una segunda variable explícita. `.env.example` deja de proponer `MASSIVE_ALLOWED_HOSTS=*` y el middleware valida el header `Host`. `/docs`, `/redoc` y `/openapi.json` se deshabilitan cuando el entorno es producción. `gitleaks.toml` sustituye `stopwords` genéricos por `regexes` anclados y `paths` acotados.

**Criterio de aceptación.**
```bash
curl -s -o /dev/null -w "%{http_code}" localhost:8000/metrics                    # → 401 (o 200 solo desde CIDR interno)
env -u MASSIVE_ENV -u MASSIVE_API_KEY uvicorn backend.app.main:app & sleep 3
curl -s -o /dev/null -w "%{http_code}" -X POST localhost:8000/v1/simulate \
  -H "X-API-Key: dev-secret-key" -d '{"pasos":5}'                                # → 401/503, NO 200
grep -n "MASSIVE_ALLOWED_HOSTS" .env.example | grep -vc "\*"                     # → ≥ 1
python -c "
from massive_core.config.api_auth import is_dev_env
assert is_dev_env(None) is False, 'unset sigue siendo development'
print('fail-closed OK')"
python - <<'PY'
import tomllib, sys
try: cfg = tomllib.load(open("gitleaks.toml","rb"))
except Exception: cfg = None
txt = open("gitleaks.toml").read()
assert txt.count("stopwords") <= 1, txt.count("stopwords")
print("allowlist endurecida")
PY
python -m pytest tests/test_api_security.py -q 2>&1 | tail -1                    # → 0 failed
```

#### W2-T03 · nginx, headers y modelo de contenedor

| | |
|---|---|
| **Hallazgos** | `D5-014` · `D5-015` · `D7-016` |
| **Tamaño** | M |
| **Depende de** | `W2-T02` · `W1-T04` |

**Resultado esperado.** Los headers de seguridad se aplican también a las respuestas de assets estáticos (include compartido o repetición del bloque en cada `location`). La CSP no usa `'unsafe-inline'` en `script-src`; `connect-src` enumera los proveedores reales; se añade `server_tokens off` y `Permissions-Policy`; se retira `X-XSS-Protection`. El contenedor tiene un único modelo de procesos coherente: o dos contenedores (nginx + api) en el compose, o supervisord sin directivas `user=root` inefectivas y con el mecanismo de bind :80 documentado. Una sola definición de healthcheck (`/health`).

**Criterio de aceptación.**
```bash
docker compose up -d && sleep 10
for p in / /assets/app.js /health /metrics; do
  echo "== $p"; curl -sI "localhost$p" | grep -iE "content-security-policy|x-content-type|strict-transport" | wc -l
done                                                        # → ≥ 3 en TODAS las rutas, incluido /assets
curl -sI localhost/ | grep -ci "x-xss-protection"           # → 0
curl -sI localhost/ | grep -ci "server: nginx/"             # → 0 (server_tokens off)
grep -c "unsafe-inline" nginx.conf                          # → ≤ 1 (solo style-src, si aplica)
grep -c "user=root" supervisord.conf                        # → 0 (o dos contenedores en compose)
grep -c "healthcheck" Dockerfile docker-compose.yml | awk -F: '{s+=$2} END{print s}'   # → definición única
```

---

### Track B — Fiabilidad del runtime

#### W2-T04 · `cache_manager`: TTL, clave versionada, concurrencia y observabilidad

| | |
|---|---|
| **Hallazgos** | `D9-001` · `D9-002` · `D9-003` · `D2-008` (el `print` de `cache_manager.py:36`) |
| **Tamaño** | M |
| **Depende de** | `W1-T06` |

**Resultado esperado.** El cache tiene TTL configurable por env y lo aplica en la lectura (`created_at` deja de ser una columna muerta). La capa en memoria tiene límite de tamaño con política de desalojo. La clave usa un hash no-MD5 de ancho completo e incluye un `CACHE_SCHEMA_VERSION` más un fingerprint de los pesos CfC y de `MASSIVE_RUNTIME_PARAMS`. Las operaciones sobre memoria y SQLite están bajo lock. Los cuatro `except Exception` registran warning con `exc_info` e incrementan un contador expuesto en `/metrics`; `clear()` es transaccional. El docstring de la clase describe con exactitud las garantías reales.

**Criterio de aceptación.**
```bash
grep -c "created_at" cache_manager.py                                    # → ≥ 2 (definición + lectura)
grep -cE "md5" cache_manager.py                                          # → 0
grep -cE "Lock\(|lock\b" cache_manager.py                                # → ≥ 2
grep -cE "except Exception:\s*$" -A1 cache_manager.py | grep -c "pass"   # → 0
grep -cE "print\(" cache_manager.py                                      # → 0
python - <<'PY'
import time, os
os.environ["MASSIVE_CACHE_TTL_SECONDS"] = "1"
import cache_manager
c = cache_manager.LandscapeCache(db_path=":memory:")
c.set("objetivo de prueba", {"a": 1}); assert c.get("objetivo de prueba") == {"a": 1}
time.sleep(1.5); assert c.get("objetivo de prueba") is None, "el TTL no expira"
print("TTL OK")
k1 = c._key("mismo objetivo"); os.environ["MASSIVE_RUNTIME_PARAMS"] = "cambiado"
assert c._key("mismo objetivo") != k1 or "CACHE_SCHEMA_VERSION" in open("cache_manager.py").read()
print("clave versionada OK")
PY
python - <<'PY'
import threading, cache_manager
c = cache_manager.LandscapeCache(db_path=":memory:")
errs = []
def w(i):
    try:
        for j in range(200): c.set(f"goal-{i}-{j}", {"i": i, "j": j}); c.get(f"goal-{i}-{j}")
    except Exception as e: errs.append(e)
ts = [threading.Thread(target=w, args=(i,)) for i in range(8)]
[t.start() for t in ts]; [t.join() for t in ts]
assert not errs, errs[:3]; print("concurrencia sin errores:", len(errs))
PY
curl -s localhost:8000/metrics | grep -c "cache_"                        # → ≥ 1 (hits/misses/errors)
```

#### W2-T05 · Excepciones observables, logging centralizado y side-effects de import

| | |
|---|---|
| **Hallazgos** | `D2-005` · `D1-008` · `D2-009` · `D2-010` |
| **Tamaño** | M |
| **Depende de** | `W1-T06` |

**Resultado esperado.** Ningún handler `except Exception` del código de librería (`backend/`, `services/`, `massive/`, `massive_core/`, módulos root) termina en `pass`/`continue` sin registrar. Ningún módulo de librería llama a `logging.basicConfig`; los dos de `tests/` tampoco. Todos los loggers de librería usan `getLogger(__name__)` y la jerarquía se configura desde `massive_core/config/logging_setup.py`. Importar cualquier módulo no crea archivos en el CWD: `massive_run.log` y `landscapes_cache.db` pasan a rutas configurables con default fuera del CWD.

**Criterio de aceptación.**
```bash
python - <<'PY'
import ast, glob, sys
bad = []
for f in glob.glob("**/*.py", recursive=True):
    if any(x in f for x in (".venv","node_modules","site/","/tests/","experiments/","scripts/")): continue
    try: t = ast.parse(open(f).read(), f)
    except SyntaxError: continue
    for n in ast.walk(t):
        if isinstance(n, ast.ExceptHandler) and n.body and all(
              isinstance(s, ast.Pass) or (isinstance(s, ast.Continue)) for s in n.body):
            bad.append(f"{f}:{n.lineno}")
assert not bad, bad; print("0 excepciones silenciadas en librería")
PY
grep -rn "logging.basicConfig" --include="*.py" backend services massive massive_core *.py tests | \
  grep -vcE "logging_setup.py|cli/main.py|__main__|benchmarks/runner.py|benchmark_scalability.py|train_cfc|cfc_trainer.py"   # → 0
grep -rhn "getLogger(" --include="*.py" backend services massive massive_core *.py | \
  grep -vc "__name__"                                                          # → 0
python - <<'PY'
import os, glob, subprocess, tempfile, sys
before = set(glob.glob("*"))
subprocess.run([sys.executable, "-c", "import simulator"], check=True, cwd=os.getcwd())
new = set(glob.glob("*")) - before
assert not new, f"import creó: {new}"; print("import sin side-effects en CWD")
PY
python -m pytest tests/ -q 2>&1 | tail -1                                      # → 0 failed
```

---

### Track C — Tipos y rendimiento del motor

#### W2-T06 · Cero errores en el slice de mypy y retirada de las válvulas de escape

| | |
|---|---|
| **Hallazgos** | `D7-006` · `D2-003` (los 36 del slice) · avanza `D7-002` |
| **Tamaño** | M |
| **Depende de** | `W1-T07` · `W2-T01` |

**Resultado esperado.** `scripts/typecheck_slice.py` sale 0. `services/llm_orchestrator.py:479` ya no asigna un `ForecastResult` a una variable `dict[str, Any]` (el `hasattr(result, "model_dump")` defensivo deja de ser necesario). `lint.yml` pierde el `|| true` y `typecheck.yml` pierde el `continue-on-error: true`; ambos jobs pueden fallar y de hecho fallan si se introduce un error. El badge de MyPy del README refleja un check bloqueante.

**Criterio de aceptación.**
```bash
python scripts/typecheck_slice.py ; echo "slice=$?"                          # → 0
mypy --config-file pyproject.toml massive/ backend/ services/ massive_core/ 2>&1 | tail -1   # → Success
grep -c "|| true" .github/workflows/lint.yml                                 # → 0
grep -c "continue-on-error" .github/workflows/typecheck.yml                  # → 0
grep -n "hasattr(result" services/llm_orchestrator.py                        # → ausente
# prueba de que el gate muerde:
cp services/llm_orchestrator.py /tmp/bk && \
  printf '\ndef _probe(x: int) -> str:\n    return x\n' >> services/llm_orchestrator.py && \
  python scripts/typecheck_slice.py ; rc=$? ; cp /tmp/bk services/llm_orchestrator.py ; \
  echo "gate detecta error inyectado: rc=$rc"                                # → rc=1
```

#### W2-T07 · Las 6 variables descartadas de `energy_engine.py`

| | |
|---|---|
| **Hallazgos** | `D9-004` · `D2-006` |
| **Tamaño** | M |
| **Depende de** | `W1-T06` |

**Resultado esperado.** Cada una de las 6 variables (`sigma2`, `att_positions`, `att_strengths`, `rep_positions`, `rep_strengths`, `gini`) está cableada a la dinámica o eliminada, con la decisión documentada. Si `gini` alimenta el acoplamiento reactivo descrito en `MASSIVE_REACTIVE_COHERENCE_PLAN.md`, el test correspondiente pasa. El coste por paso del motor no aumenta.

**Criterio de aceptación.**
```bash
ruff check energy_engine.py --select F841 ; echo $?                          # → 0
grep -nE "gini" energy_engine.py | head -5                                   # → cableado o eliminado, no asignado-y-olvidado
python -m pytest tests/test_cfc_lambda_integration.py -q -k reactive 2>&1 | tail -1   # → passed (si aplica la hipótesis de coherencia)
python - <<'PY'
import time, numpy as np
from energy_engine import SocialEnergyEngine
e = SocialEnergyEngine(n_agents=2000, seed=42)
t = time.perf_counter(); e.step(50); dt = time.perf_counter() - t
print(f"2k agents × 50 steps: {dt:.2f}s")
assert dt < 30, dt
PY
```

#### W2-T08 · URLs centralizadas + interfaz CLI del generador de tipos

| | |
|---|---|
| **Hallazgos** | `D2-016` · `D3-019` · protege `D3-020` |
| **Tamaño** | S |
| **Depende de** | `W1-T06` |

**Resultado esperado.** Las URLs base de proveedores LLM viven en `massive_core/config/settings.py` y todos los consumidores (incluido `interpreter_layer.py:222`) leen de ahí o de su variable de entorno. `scripts/gen_ts_types.py` tiene `argparse` con `--dry-run` (compara sin escribir, exit 1 si hay diff), `--stdout`, `--out PATH` y `--check`. `validate_ts_types.yml` usa `--check`. El fork roto de `massive-ui-ng/infra/scripts/` queda eliminado o reparado (según lo que decida `W5-T01`).

**Criterio de aceptación.**
```bash
grep -n "localhost:11434" interpreter_layer.py | grep -vc getenv              # → 0
python - <<'PY'
import re
n = 0
for f in ["interpreter_layer.py","langchain_workflows.py","massive-ui-ng/backend/app/llm_chat.py"]:
    try: t = open(f).read()
    except FileNotFoundError: continue
    for m in re.finditer(r'"https?://[^"]+"', t):
        if "localhost" in m.group() or "127.0.0.1" in m.group(): n += 1
print("hardcodes localhost en .py de librería:", n); assert n == 0
PY
cp frontend/src/types/api.generated.ts /tmp/orig
python scripts/gen_ts_types.py --dry-run ; echo "dry-run=$?"                  # → 0 y el archivo intacto
diff -q /tmp/orig frontend/src/types/api.generated.ts && echo "no escribió"
python scripts/gen_ts_types.py --stdout | head -3 | grep -qE "^//|^import|^export" && echo "stdout OK"
python scripts/gen_ts_types.py --check ; echo "check=$?"                      # → 0
grep -n "gen_ts_types.py --check" .github/workflows/validate_ts_types.yml     # → presente
```

---

### Track D — Workflows y dependencias

#### W2-T09 · Corrección de los workflows

| | |
|---|---|
| **Hallazgos** | `D7-003` · `D7-010` · `D7-012` · `D7-013` |
| **Tamaño** | M |
| **Depende de** | `W1-T02` · `W1-T03` |

**Resultado esperado.** Los 4 jobs de `pytest.yml` instalan el mismo conjunto de dependencias y ninguno corre tests cuyas dependencias no instala. `pvu-validation.yml` se dispara también en push a `main` (o por schedule semanal). Los smoke tests de CI generan la clave de API en el step en lugar de usar un valor fijo. `secret_scan.yml` se divide en escaneo incremental (por push) y escaneo de historial completo (programado), con `paths-ignore`.

**Criterio de aceptación.**
```bash
python - <<'PY'
import yaml
w = yaml.safe_load(open(".github/workflows/pytest.yml"))
installs = [s.get("run","") for j in w["jobs"].values() for s in j["steps"] if "pip install" in s.get("run","")]
print(f"{len(installs)} pasos de instalación")
core = [i for i in installs if "test_simulator" in i or True]
w2 = yaml.safe_load(open(".github/workflows/pvu-validation.yml"))
assert "push" in (w2.get("on") or w2.get(True)), w2.get("on")
print("pvu-validation corre en push OK")
PY
grep -c "ci-test-key" .github/workflows/*.yml                                 # → 0
grep -cE "openssl rand|secrets\." .github/workflows/docker-e2e.yml            # → ≥ 1
grep -c "fetch-depth: 0" .github/workflows/secret_scan.yml                    # → solo en el job programado
grep -c "schedule" .github/workflows/secret_scan.yml                          # → ≥ 1
python - <<'PY'
import yaml, glob
for f in glob.glob(".github/workflows/*.yml"): yaml.safe_load(open(f))
print("13/13 YAML válidos")
PY
```

#### W2-T10 · Fuentes de verdad de dependencias

| | |
|---|---|
| **Hallazgos** | `D5-003` · `D5-004` · `D5-006` · `D5-007` · `D5-011` · `D5-012` |
| **Tamaño** | M |
| **Depende de** | `W1-T02` · `W1-T03` |

**Resultado esperado.** Una sola fuente de verdad: `pyproject.toml`. `requirements.txt` se genera a partir de él (o desaparece). Existe lockfile commiteado por extra/plataforma y `uv.lock` sale del `.gitignore`. `streamlit` y `torchdiffeq` eliminados si siguen sin imports. `pytest`, `mkdocs*` y el resto de herramientas de dev/docs fuera del requirements de runtime. Los especificadores de versión son idénticos en ambas declaraciones. `.env.example` sin claves duplicadas y con una única convención de nombrado documentada; `.env.local.example` eliminado o con precedencia explícita y los dos compose actualizados en consecuencia.

**Criterio de aceptación.**
```bash
python - <<'PY'
import re, tomllib, os
req = {l.split(">=")[0].split("==")[0].split("<")[0].strip().lower().replace("_","-")
       for l in open("requirements.txt") if l.strip() and not l.startswith("#")}
p = tomllib.load(open("pyproject.toml","rb"))["project"]
declared = {re.split(r"[><=~!\[]", d)[0].strip().lower().replace("_","-") for d in p["dependencies"]}
for extra in p.get("optional-dependencies", {}).values():
    declared |= {re.split(r"[><=~!\[]", d)[0].strip().lower().replace("_","-") for d in extra}
print("en requirements y no declarado:", sorted(req - declared))
print("streamlit presente:", "streamlit" in req | declared)
print("torchdiffeq presente:", "torchdiffeq" in req | declared)
print("pytest en runtime:", "pytest" in {re.split(r'[><=~!\\[]',d)[0] for d in p['dependencies']})
assert "streamlit" not in (req | declared)
PY
ls *.lock uv.lock requirements*.lock 2>/dev/null | head -3                     # → existe al menos uno
grep -c "^uv.lock$" .gitignore                                                 # → 0
git check-ignore -v uv.lock ; echo "no ignorado=$?"                            # → exit ≠ 0
grep -c "mkdocs" requirements.txt                                              # → 0 (o requirements-dev.txt)
grep -c "OLLAMA_HOST" .env.example                                             # → 1
grep -cE "^(LLM_MODEL|MASSIVE_LLM_MODEL)=" .env.example                        # → 1 (una convención)
pip-audit -r requirements.txt --no-deps                                        # → No known vulnerabilities
python -c "import simulator, backend.app.main; print('import OK tras cambio de deps')"
```

---

## 6. WAVE 3 · BUILD, EMPAQUETADO Y DESPLIEGUE

Objetivo de la ola: que el proyecto se pueda instalar, empaquetar, contenerizar y publicar. Al cierre, `pip install -e .` funciona, el wheel es importable, y `publish.yml` es alcanzable.

**Gate de cierre de ola W3:**
```bash
python -m venv /tmp/w3 && . /tmp/w3/bin/activate
pip install -e ".[full]"                                    # → exit 0
python -c "import massive, massive.cli.main, backend.app.main, metrics.unified_metrics; print('OK')"
massive-cli --help                                          # → exit 0
python -m build && pip install dist/*.whl && \
  python -c "from massive.core.empirical_calibration import *; from metrics.unified_metrics import *; print('wheel OK')"
docker compose build && docker compose up -d && sleep 10 && \
  curl -sf localhost/health && curl -sf localhost:8000/health
gh api repos/Adlgr87/MASSIVE/tags --jq 'length'             # → ≥ 1
```

---

#### W3-T01 · Backend de build y empaquetado real

| | |
|---|---|
| **Hallazgos** | `D5-002` · `D3-001` · `D8-002` (nombre de distribución) |
| **Tamaño** | L |
| **Depende de** | `W2-T10` · `PE-2` |

**Resultado esperado.** `pip install -e .` funciona sin toolchain Rust. El paquete Python y la extensión Rust están desacoplados (build-backend `setuptools` para `massive`, extensión publicada aparte o construida en un job dedicado). `packages.find` incluye todo lo que los módulos incluidos consumen: los 31 módulos root declarados vía `py-modules`, más `metrics*`, `adapters*` y `monitoring*` — o bien la migración a `massive/core/` está lo bastante avanzada como para que el `include` actual sea correcto. Un wheel construido e instalado en un venv limpio importa sin `ModuleNotFoundError`. `install.sh install` y `install.sh install-dev` completan. El nombre de distribución en PyPI está verificado como disponible.

**Criterio de aceptación.**
```bash
python -m venv /tmp/w3t01 && . /tmp/w3t01/bin/activate && pip install -q -U pip
pip install -e ".[dev]" ; echo "editable=$?"                                  # → 0
python -c "import tomllib;p=tomllib.load(open('pyproject.toml','rb'));
print(p['build-system']['build-backend'])"                                    # → setuptools (o maturin con Rust disponible en CI)
python -m build 2>&1 | tail -2                                                # → Successfully built …whl …tar.gz
pip install -q dist/*.whl && python - <<'PY'
import importlib
for m in ["massive","massive.cli.main","massive.core.empirical_calibration",
          "massive.core.extended_models","metrics.unified_metrics",
          "backend.app.main","services.simulation_service","forecast"]:
    importlib.import_module(m); print("OK", m)
PY
bash install.sh install ; echo "install.sh=$?"                                # → 0
grep -A5 "packages.find" pyproject.toml | grep -cE "metrics|adapters"          # → ≥ 1 (o py-modules con los 31)
pip index versions massive 2>&1 | head -1                                      # → decisión de nombre registrada
```

#### W3-T02 · Rust: un solo manifiesto, compilado y testeado en CI, con paridad verificada

| | |
|---|---|
| **Hallazgos** | `D3-017` · `D3-018` · `D7-009` · `D9-007` |
| **Tamaño** | M |
| **Depende de** | `W3-T01` |

**Resultado esperado.** Un único `Cargo.toml` (el huérfano de `rust_core/` eliminado, o convertido en workspace member real que resuelve). Un job `rust` en CI con toolchain estable que ejecuta `cargo fmt --check`, `cargo clippy -- -D warnings`, `cargo test`, `maturin develop` y un test de paridad Rust↔NumPy sobre los tres kernels. `massive_core/rust_core.py` tiene el `# pragma: no cover` en la rama correcta. Las constantes numéricas de los kernels están en un único sitio documentado. El badge de Rust del README enlaza al manifiesto real y afirma sólo lo verificado.

**Criterio de aceptación.**
```bash
test ! -f rust_core/Cargo.toml -o (cd rust_core && cargo metadata --no-deps -q) && echo "manifiesto resoluble"
find . -name Cargo.toml -not -path "./.git/*" | wc -l                          # → 1 (o 2 si es workspace válido)
cargo fmt --check ; echo "fmt=$?"                                             # → 0
cargo clippy -- -D warnings ; echo "clippy=$?"                                # → 0
cargo test ; echo "cargo-test=$?"                                             # → 0
grep -c "rust" .github/workflows/*.yml | grep -v ":0"                          # → ≥ 1 workflow
python - <<'PY'
import numpy as np
from massive_core.rust_core import RUST_CORE_AVAILABLE, multi_potential_gradient
if RUST_CORE_AVAILABLE:
    import massive_rust_core as r
    x = np.random.default_rng(0).uniform(-1,1,(64,5))
    np.testing.assert_allclose(multi_potential_gradient(x),
                               np.asarray(r.multi_potential_gradient(x)), rtol=1e-12)
    print("paridad Rust↔NumPy OK")
else:
    print("RUST_CORE_AVAILABLE=False — la paridad se verifica en el job rust de CI")
PY
grep -n "pragma: no cover" massive_core/rust_core.py                           # → en la rama que NO se ejecuta
```

#### W3-T03 · Un camino de despliegue documentado

| | |
|---|---|
| **Hallazgos** | `D7-015` · `D7-005` (cierre) · `D3-014` · `D7-011` |
| **Tamaño** | M |
| **Depende de** | `W1-T04` · `W2-T03` · `W3-T01` |

**Resultado esperado.** Una tabla en README y README_ES con **una** opción por caso de uso (dev local · producción · observabilidad) y los archivos restantes eliminados o movidos a `docs/examples/` con banner. `main_massive.yml` (Azure) eliminado o documentado como destino real con `python-version` fijada. `monitoring/` conectado a un `docker-compose.observability.yml` opcional con prometheus y grafana montándolo, o marcado explícitamente como reference-only. `docs/DOCKER.md` está en el nav de MkDocs. El Makefile tiene targets `docker`, `docker-observability` y `docs`.

**Criterio de aceptación.**
```bash
grep -cE "docker|Docker" README.md                                             # → ≥ 3
find . -maxdepth 1 -name "docker-compose*.yml" -o -maxdepth 1 -name "Dockerfile*" | wc -l   # → ≤ 2
docker compose config -q && echo "canónico OK"
test ! -f .github/workflows/main_massive.yml -o \
  grep -cE "python-version: '3.x'" .github/workflows/main_massive.yml          # → 0
(test -f docker-compose.observability.yml && docker compose -f docker-compose.observability.yml config -q \
  && echo "observabilidad cableada") || grep -c "reference-only" README.md     # → una de las dos
python -c "import yaml;n=yaml.safe_load(open('mkdocs.yml'))['nav'];
import json;assert 'DOCKER.md' in json.dumps(n); print('DOCKER.md en nav')"
make help | grep -cE "^docker|^docs"                                           # → ≥ 2
```

#### W3-T04 · Versionado único, primer release y pipeline de publicación alcanzable

| | |
|---|---|
| **Hallazgos** | `D6-012` · `D8-002` · `D7-008` · `D5-016` |
| **Tamaño** | M |
| **Depende de** | `W3-T01` · `W2-T06` |

**Resultado esperado.** Una única versión en todo el repo, leída desde un único punto (`massive/__init__.py:__version__`) y consumida por `pyproject.toml`, `FastAPI(version=…)`, ambos `package.json`, el manifiesto del adapter y `GET /version`. `CHANGELOG.md` con una sola sección `[Unreleased]` y versiones SemVer ordenadas. Tag `vX.Y.Z` y release de GitHub creados, con notas generadas desde el CHANGELOG. `deploy_hf_spaces.yml` no embebe el token en la URL del remoto ni hardcodea el usuario. Trusted Publishing de PyPI configurado para el environment `pypi-publish`.

**Criterio de aceptación.**
```bash
python -c "import massive; print(massive.__version__)"
python - <<'PY'
import json, re, tomllib, massive
v = massive.__version__
assert tomllib.load(open("pyproject.toml","rb"))["project"]["version"] == v
assert re.search(rf'version="{re.escape(v)}"', open("backend/app/main.py").read())
assert json.load(open("frontend/package.json"))["version"] == v
print("versión única:", v)
PY
curl -s localhost:8000/version | python -c "import json,sys;print(json.load(sys.stdin)['version'])"
grep -c "^## \[Unreleased\]" CHANGELOG.md                                      # → 1
grep -cE "^## \[v?[0-9]+\.[0-9]+" CHANGELOG.md                                 # → ≥ 1
gh api repos/Adlgr87/MASSIVE/tags --jq '.[0].name'                             # → vX.Y.Z
gh api repos/Adlgr87/MASSIVE/releases --jq '.[0].tag_name'                     # → igual
grep -cE "https://[^ ]*:\\\$HF_TOKEN@" .github/workflows/deploy_hf_spaces.yml   # → 0
gh secret list --env pypi-publish 2>/dev/null | head -2                        # → OIDC configurado
```

#### W3-T05 · Job `clean-clone` y matriz de dependencias mínimas

| | |
|---|---|
| **Hallazgos** | `D7-002` (cierre agregado) · `D1-004` · `D1-009` · Patrón 6 del reporte |
| **Tamaño** | M |
| **Depende de** | `W1-*` · `W2-*` · `W3-T01` · `W3-T03` |

**Resultado esperado.** Un workflow `clean-clone.yml` que, desde un checkout sin caché: crea un venv, instala **sólo** `requirements.txt`, verifica que importan `simulator`, `backend.app.main`, `massive.cli.main` y `metrics.unified_metrics`, ejecuta `pytest tests/ -q`, construye la imagen Docker y verifica dentro del contenedor que los pesos CfC están presentes y que `CfCRouter.get().status` reporta lo esperado. Un segundo job con la matriz de dependencias mínimas (sin `torch`, sin `cupy`, sin extras) que verifica que el sistema arranca en modo degradado y lo declara. `tests/test_import_smoke.py` parametrizado sobre los 146 módulos, ejecutado en ambas matrices.

**Criterio de aceptación.**
```bash
test -f .github/workflows/clean-clone.yml && python -c "import yaml;yaml.safe_load(open('.github/workflows/clean-clone.yml'));print('OK')"
test -f tests/test_import_smoke.py && python -m pytest tests/test_import_smoke.py -q 2>&1 | tail -1   # → 146 passed
PYTHONPATH=/tmp/notorch python -m pytest tests/test_import_smoke.py -q -rs 2>&1 | tail -2              # → pasado con skips documentados
rm -rf /tmp/cc && python -m venv /tmp/cc && . /tmp/cc/bin/activate && \
  pip install -q -r requirements.txt && \
  python -c "import simulator, backend.app.main, massive.cli.main, metrics.unified_metrics; print('clean-clone OK')" && \
  python -m pytest tests/ -q 2>&1 | tail -1                                                            # → 0 failed
docker compose build && docker run --rm massive-audit python -c "
from cfc_router import CfCRouter; s=CfCRouter.get().status; print(s)
from pathlib import Path; assert Path('models/cfc_calibrated/cfc_residual.pt').exists()"
```

---

## 7. WAVE 4 · VERDAD DOCUMENTAL Y PRIMERA IMPRESIÓN

Objetivo de la ola: que todo lo que el repo afirma de sí mismo sea cierto y verificable automáticamente, y que la raíz deje de ser una pared de archivos. Esta ola puede ejecutarse en paralelo con la 3 (no comparten archivos), salvo `W4-T01` que necesita las cifras reales de `W3-T05`.

**Gate de cierre de ola W4:**
```bash
ls -A | wc -l                                             # → ≤ 45 (desde 106)
ls *.md | wc -l                                           # → ≤ 8 (desde 21)
python scripts/check_docs_refs.py 2>&1 | tail -1          # → 0 rutas inexistentes (o todas en docs/archive/)
grep -rc "/home/" --include="*.md" . | grep -v ":0" | wc -l   # → 0
python -m mkdocs build --strict && echo OK                # → 0 warnings
python -c "import yaml,json;n=json.dumps(yaml.safe_load(open('mkdocs.yml'))['nav']);
import glob;orph=[f for f in glob.glob('docs/**/*.md',recursive=True) if f.split('docs/',1)[1] not in n];
print('huérfanos:',len(orph))"                            # → ≤ 5
```

---

#### W4-T01 · README generado desde CI

| | |
|---|---|
| **Hallazgos** | `D6-001` · `D6-002` · `D6-014` · `D8-005` · `D8-010` |
| **Tamaño** | M |
| **Depende de** | `W3-T05` (para las cifras reales) |

**Resultado esperado.** Las cifras del README (nº de tests, passed/failed, cobertura, estado de ruff/black/mypy, recuento de endpoints, árbol de layout) se generan desde un artifact de CI entre marcadores `<!-- QUALITY:START -->`/`<!-- QUALITY:END -->`, y un job exige diff vacío. Toda mención a herramientas que no están en CI (`semgrep`) está retirada o la herramienta está añadida. Los badges reflejan checks bloqueantes reales; se añade coverage, docs, code-style y release. La tabla frontier y el árbol de layout reconocen explícitamente los módulos legacy en migración. `README.md` y `README_ES.md` comparten las cifras generadas y un check compara sus encabezados de sección. La discrepancia `Python 3.11+` ↔ `requires-python` está resuelta.

**Criterio de aceptación.**
```bash
python - <<'PY'
import re, json, subprocess
r = open("README.md").read(); e = open("README_ES.md").read()
m = re.search(r"<!-- QUALITY:START -->(.*?)<!-- QUALITY:END -->", r, re.S)
assert m, "sin marcadores de calidad generada"
q = json.load(open("reports/audit_baseline.json"))
out = subprocess.run(["python","-m","pytest","tests/","-q","--co"],capture_output=True,text=True).stdout
n = int(re.search(r"(\d+) tests? collected", out).group(1))
assert str(n) in m.group(1), f"el README no dice {n}"
print("README sincronizado con la medición:", n, "tests")
heads_en = re.findall(r"^##\s+(.+)$", r, re.M); heads_es = re.findall(r"^##\s+(.+)$", e, re.M)
assert len(heads_en) == len(heads_es), (len(heads_en), len(heads_es))
print("estructura EN/ES paralela:", len(heads_en), "secciones")
PY
grep -ci "semgrep" README.md README_ES.md                                   # → 0 (o semgrep en CI)
grep -cE "679 tests|530 tests|68 %" README.md README_ES.md                  # → 0
python -c "import tomllib,re;p=tomllib.load(open('pyproject.toml','rb'));
rp=p['project']['requires-python'];b=open('README.md').read();
assert re.search(r'Python-'+rp.replace('>=','').replace('.','') , b) or rp.replace('>=','') in b, rp
print('requires-python', rp, 'coherente con el badge')"
python scripts/gen_readme_quality.py --check ; echo $?                      # → 0
curl -s localhost:8000/openapi.json | python -c "
import json,sys;s=json.load(sys.stdin)['paths'];print(len([p for p in s if p.startswith('/v1/')]),'endpoints /v1')"
grep -oE "[0-9]+ v1 endpoints" README.md                                    # → coincide
```

#### W4-T02 · Vaciado de la raíz: Markdown

| | |
|---|---|
| **Hallazgos** | `D6-003` · `D8-001` (parcial) |
| **Tamaño** | S |
| **Depende de** | `W0-T03` |

**Resultado esperado.** La raíz conserva sólo `README.md`, `README_ES.md`, `CHANGELOG.md`, `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, un único archivo de instrucciones para agentes y `repomix-instruction.md` (que `repomix.config.json` necesita en root). Los 5 `REPORT_*.md` van a `docs/archive/reports/`; los 4 de arquitectura/planes a `docs/architecture/` o `docs/plans/`; los 2 de operaciones a `docs/operations/`; `calibration_log.md` y `progress.md` a `docs/research/`. Cada documento movido a `docs/archive/` lleva el banner `> ⚠️ HISTÓRICO`. `CONTRIBUTING.md` establece la regla "ningún `.md` de planning en root". Las referencias internas a las rutas movidas están actualizadas.

**Criterio de aceptación.**
```bash
ls *.md | sort                                                                  # → ≤ 8 archivos
ls *.md | wc -l
test -d docs/archive/reports && ls docs/archive/reports | wc -l                 # → 5
grep -rc "REPORT_OPTIMIZATION.md\|MASSIVE_SYSTEM_MAP.md" --include="*.md" . | grep -v ":0" | \
  xargs -r grep -l "docs/archive\|docs/architecture" >/dev/null && echo "refs actualizadas"
grep -l "HISTÓRICO" docs/archive/reports/*.md | wc -l                           # → 5
grep -c "planning en root\|no .*\.md.* en root\|ningún.*root" CONTRIBUTING.md    # → ≥ 1
python -m mkdocs build --strict && echo "strict OK"
python scripts/check_docs_refs.py 2>&1 | tail -1                                # → 0 nuevas roturas
```

#### W4-T03 · Reconciliación documento ↔ árbol

| | |
|---|---|
| **Hallazgos** | `D6-004` · `D6-005` · `D6-007` · `D6-008` · `D6-010` · `D6-011` · `D6-018` (linkcheck) |
| **Tamaño** | L |
| **Depende de** | `W4-T02` |

**Resultado esperado.** Un script `scripts/check_docs_refs.py` que extrae referencias a rutas de todos los `.md` y falla si alguna no existe (excluyendo `docs/archive/`). Las 186 rutas inexistentes están corregidas, o su documento está en `docs/archive/` con banner. Cero ocurrencias de `/home/`, `/Users/` o `C:\` en archivos trackeados, con check de CI. `MASSIVE_SYSTEM_MAP.md` regenerado desde el árbol real (o reducido a componentes + directorios estables). `REPORT_OPTIMIZATION.md` archivado con banner y su premisa Numba marcada como obsoleta. `docs/README_ES.md` deja de ser un stub de 5 líneas (o el nav apunta a la traducción real). Los 11 módulos de librería sin docstring lo tienen. MkDocs incorpora un link-checker.

**Criterio de aceptación.**
```bash
python scripts/check_docs_refs.py ; echo "refs=$?"                              # → 0
python scripts/check_docs_refs.py 2>&1 | tail -1                                # → "0 rutas inexistentes"
grep -rn "/home/\|/Users/" --include="*.md" . | grep -vc "docs/archive/"        # → 0
grep -c "check_docs_refs" .github/workflows/*.yml | grep -v ":0"                # → ≥ 1
python - <<'PY'
import ast, glob
missing = []
for f in glob.glob("**/*.py", recursive=True):
    if any(x in f for x in (".venv","node_modules","site/","tests/","/test_")): continue
    try: t = ast.parse(open(f).read(), f)
    except SyntaxError: continue
    if ast.get_docstring(t) is None: missing.append(f)
assert not missing, missing; print("0 módulos de librería sin docstring")
PY
wc -l docs/README_ES.md                                                          # → > 50, o nav corregido
grep -c "Numba\|numba" REPORT_OPTIMIZATION.md docs/archive/reports/REPORT_OPTIMIZATION.md 2>/dev/null
                                                                                    # → 0, o con banner HISTÓRICO
grep -c "streamlit\|8501\|test_mamba_engine\|micro_ui" MASSIVE_SYSTEM_MAP.md docs/**/MASSIVE_SYSTEM_MAP.md 2>/dev/null  # → 0
python -m mkdocs build --strict 2>&1 | grep -ciE "warning|error"                 # → 0
grep -cE "linkcheck|htmlproofer" mkdocs.yml                                       # → ≥ 1
```

#### W4-T04 · Navegabilidad de la documentación + instrucciones para agentes unificadas

| | |
|---|---|
| **Hallazgos** | `D6-009` · `D6-015` |
| **Tamaño** | S |
| **Depende de** | `W4-T02` |

**Resultado esperado.** Los 35 documentos huérfanos están en el nav de MkDocs bajo secciones coherentes (`Operations`, `Architecture → Domain maps`, `Reference`, `Validation`, `Archive`), o explícitamente excluidos con justificación. Un único archivo de instrucciones para agentes, con secciones internas; los demás archivos apuntan a él. Las definiciones de agentes están en `.github/agents/*.agent.md` correctamente formateadas y con nombres que coinciden con su `name:`.

**Criterio de aceptación.**
```bash
python - <<'PY'
import yaml, json, glob
nav = json.dumps(yaml.safe_load(open("mkdocs.yml"))["nav"])
orph = [f for f in glob.glob("docs/**/*.md", recursive=True) if f.split("docs/",1)[1] not in nav]
print(f"huérfanos: {len(orph)}"); assert len(orph) <= 5, orph
PY
python -m mkdocs build --strict && ls site/architecture/ | wc -l                # → ≥ 19
find . -maxdepth 1 -name "AGENTS.md" -o -maxdepth 1 -name "CLAUDE.md" | wc -l   # → 1
python - <<'PY'
import yaml, glob
fs = sorted(glob.glob(".github/agents/*.agent.md"))
assert len(fs) >= 2, fs
for f in fs:
    t = open(f).read().lstrip(); assert t.startswith("---"), f
    name = yaml.safe_load(t.split("---")[1])["name"]
    print(f"{f} → {name}")
PY
grep -c "AGENTS.md" CLAUDE.md repomix-instruction.md 2>/dev/null | head -3      # → referencian el único archivo
```

#### W4-T05 · Nomenclatura de producto y superficie HTTP versionada

| | |
|---|---|
| **Hallazgos** | `D8-011` · `D3-011` |
| **Tamaño** | S |
| **Depende de** | `W4-T01` |

**Resultado esperado.** El nombre de servicio expuesto (`/health`, título de OpenAPI, `container_name`) es coherente con el nombre del producto. Los archivos con nombre de generación anterior están renombrados con shim, o la decisión de conservarlos está registrada en `docs/architecture/CANONICAL_SOURCES.md`. Los alias `/api/v1/*` emiten header `Deprecation` y/o `Sunset` con fecha, y `docs/architecture/backward_compatibility_aliases.md` está en el nav y documenta la retirada.

**Criterio de aceptación.**
```bash
curl -s localhost:8000/health | python -c "import json,sys;print(json.load(sys.stdin)['service'])"   # → "MASSIVE …", sin "UIL"
curl -s localhost:8000/openapi.json | python -c "import json,sys;print(json.load(sys.stdin)['info']['title'])"
grep -c "massive-uil" docker-compose.yml                                        # → 0
find . -name "*UIL*" -not -path "./.git/*" -not -path "*/node_modules/*" | wc -l # → 0, o registrado en CANONICAL_SOURCES
curl -sI -X POST localhost:8000/api/v1/simulate -H "X-API-Key: $K" | grep -icE "deprecation|sunset"  # → ≥ 1
python -c "import yaml,json;n=json.dumps(yaml.safe_load(open('mkdocs.yml'))['nav']);
assert 'backward_compatibility_aliases.md' in n; print('en nav')"
test -f docs/architecture/CANONICAL_SOURCES.md && grep -c "UIL\|api.py" docs/architecture/CANONICAL_SOURCES.md   # → ≥ 2
```

---

## 8. WAVE 5 · CONSOLIDACIÓN ARQUITECTÓNICA

Objetivo de la ola: cerrar el Patrón 1 y el Patrón 4 — una sola instancia por categoría, con autoridad declarada. Es la ola de mayor tamaño y la única con tareas XL. **No debe empezar antes de que W1–W3 estén verdes**, porque mover módulos sin CI verde garantiza regresiones no detectadas.

**Gate de cierre de ola W5:**
```bash
ls *.py | wc -l                                            # → ≤ 8 (desde 31)
ls -A | wc -l                                              # → ≤ 20 (desde 106)
find . -maxdepth 2 -type d -name backend | wc -l           # → 1
find . -maxdepth 2 -type d -name frontend -not -path "*/node_modules/*" | wc -l   # → 1
find . -type d -name utils -not -path "*/node_modules/*" | wc -l                  # → 1
wc -l $(find . -name "*.py" -not -path "./.venv/*" -not -path "*/node_modules/*") | \
  sort -rn | head -6                                       # → ningún archivo > 800 líneas
mypy . 2>&1 | tail -1                                      # → no aborta
make verify                                                # → verde
python -m pytest tests/ -q 2>&1 | tail -1                  # → 0 failed
```

---

#### W5-T01 · Decisión y ejecución sobre los backends y frontends duplicados

| | |
|---|---|
| **Hallazgos** | `D3-002` · `D3-003` · `D3-005` · `D7-007` |
| **Tamaño** | XL |
| **Depende de** | `W2-T01` · `W2-T02` · `W3-T05` · `G-5` |

**Resultado esperado.** `docs/architecture/CANONICAL_SOURCES.md` existe y declara, por categoría, la instancia canónica, el estado de las demás y su fecha de retirada. Tras la decisión: **un** paquete `backend` en el árbol (sin colisión de namespace, `mypy .` no aborta), **un** frontend (con lint, typecheck y build en CI), `api.py` congelado con shim o eliminado con sus consumidores migrados, y `massive-ui-ng/` promovido o archivado — con su workflow activado y correcto si se promueve. Los 825 líneas duplicadas del `.jsx` existen una sola vez. Los 39 errores mypy del subproyecto excluido quedan dentro del scope analizado o el subproyecto deja de existir.

**Criterio de aceptación.**
```bash
test -f docs/architecture/CANONICAL_SOURCES.md && \
  grep -cE "^\| *(backend|frontend|Dockerfile|compose|Cargo|gen_ts_types|env example|utils|metrics|agentes|docs perf|despliegue|tests)" \
  docs/architecture/CANONICAL_SOURCES.md                                      # → ≥ 12 categorías
python -c "import yaml,json;n=json.dumps(yaml.safe_load(open('mkdocs.yml'))['nav']);
assert 'CANONICAL_SOURCES.md' in n; print('en nav')"
grep -c "CANONICAL_SOURCES" CONTRIBUTING.md AGENTS.md                          # → ≥ 1 en cada uno
find . -type d -name backend -not -path "*/node_modules/*" -not -path "./.git/*" | wc -l    # → 1
mypy . --ignore-missing-imports 2>&1 | grep -c "Duplicate module"              # → 0
find . -name "MASSIVE_UIL_demo.jsx" -o -name "*UIL*.jsx" | wc -l               # → ≤ 1
ls -d massive-ui-ng 2>/dev/null && \
  (test -f .github/workflows/ui-ng.yml && grep -c "massive-ui-ng" .github/workflows/ui-ng.yml)   # → ≥ 3 si se conserva
find . -maxdepth 2 -type d -name frontend -not -path "*/node_modules/*" | wc -l # → 1
npm --prefix frontend run lint && npm --prefix frontend run build              # → exit 0
```

#### W5-T02 · Reorganización modular: root → paquetes, y split de los engines

| | |
|---|---|
| **Hallazgos** | `D3-006` · `D3-007` · `D3-008` · `D3-010` · `D3-012` · `D3-016` |
| **Tamaño** | XL |
| **Depende de** | `W5-T01` · `W3-T01` |

**Resultado esperado.** Los 31 módulos root están dentro de paquetes (`massive/core/engines/`, `massive/cfc/`, `services/`, `massive_core/`), con shims de re-export en root durante el periodo de transición declarado en `CANONICAL_SOURCES.md`. `simulator.py` está dividido por responsabilidad y ninguna versión del archivo supera ~800 líneas. Un único paquete `utils/`. `massive_core/config/` (configuración de aplicación) separado de la capa científica. `micro_schemas.py` dentro de `micro_massive/`. Las dos implementaciones de métricas micro/unificadas fusionadas. `forecast/__init__.py` perezoso y `DEFAULT_CONFIG` en un módulo sin dependencias, de modo que `adapters.mutalambda` ya no arrastra el motor de simulación. El árbol de layout del README coincide con el real.

**Criterio de aceptación.**
```bash
ls *.py | sort                                                                  # → sólo shims + entrypoints declarados
ls *.py | wc -l                                                                 # → ≤ 8
wc -l simulator.py massive/core/engines/*.py 2>/dev/null | sort -rn | head -3   # → ninguno > 800
find . -type d -name utils -not -path "*/node_modules/*" -not -path "./.git/*" | wc -l   # → 1
python - <<'PY'
import sys, subprocess
# adapters ya no debe arrastrar simulator
out = subprocess.run([sys.executable,"-c",
  "import sys; import adapters.mutalambda.massive_target as m; "
  "print('simulator' in sys.modules, 'cfc_router' in sys.modules)"],
  capture_output=True, text=True)
print(out.stdout.strip(), out.stderr[-200:])
assert out.stdout.strip() == "False False", "la cadena frágil persiste"
PY
python -c "from massive.core.engines import simular, resumen_historial; print('nueva ruta OK')"
python -c "from simulator import simular; print('shim OK')"
python -m pytest tests/ -q 2>&1 | tail -1                                       # → 0 failed
python -m build && pip install dist/*.whl && python -c "import massive; print('wheel OK')"
grep -cE "massive/core/engines|massive/cfc" README.md                           # → ≥ 1 (layout actualizado)
```

#### W5-T03 · Código duplicado y código muerto

| | |
|---|---|
| **Hallazgos** | `D2-012` · `D2-013` · `D4-003` (parcial) |
| **Tamaño** | L |
| **Depende de** | `W5-T02` |

**Resultado esperado.** Un único entrenador CfC parametrizado en lugar de tres clones (`cfc_trainer.py` es el superviviente y tiene tests). Cada hallazgo de vulture al 80 % resuelto. Los módulos sin consumidores (`social_connectors.py`, `simulator.simular_multiples_dask`, `programmatic_architect.design_intervention`, los métodos muertos de `massive_core/physics/`) están cableados a un consumidor real, o eliminados junto con sus dependencias declaradas (`tweepy`, `praw`) y su documentación. El bloque duplicado de configuración CORS entre `api.py` y `backend/app/main.py` está factorizado.

**Criterio de aceptación.**
```bash
pylint . --disable=all --enable=R0801 2>&1 | grep -c "duplicate-code"           # → 0 (o solo bloques justificados)
ls train_cfc_*.py 2>/dev/null | wc -l                                          # → 0, o shims declarados
python -m pytest tests/test_cfc_trainer.py -q 2>&1 | tail -1                    # → 0 failed
vulture . --min-confidence 80 | wc -l                                          # → 0
python - <<'PY'
import subprocess
out = subprocess.run(["vulture",".","--min-confidence","60"],capture_output=True,text=True).stdout
n = len([l for l in out.splitlines() if l.strip()])
print("vulture@60:", n, "(baseline 311)"); assert n < 150
PY
test -f social_connectors.py -o ! grep -rq "tweepy\|praw" requirements.txt pyproject.toml && echo "coherente"
grep -rc "TwitterConnector\|RedditConnector" --include="*.py" . | grep -v ":0" | wc -l   # → 0, o con consumidor real
python -m pytest tests/ -q 2>&1 | tail -1                                       # → 0 failed
```

#### W5-T04 · Shims uniformes, nomenclatura de identificadores y complejidad alta

| | |
|---|---|
| **Hallazgos** | `D3-009` · `D2-014` · `D2-011` |
| **Tamaño** | L |
| **Depende de** | `W5-T02` |

**Resultado esperado.** Un único patrón de shim deprecado aplicado a todos (docstring `.. deprecated::` + re-export + warning filtrable + fecha de retirada en `CANONICAL_SOURCES.md`); el shim de `extended_models` existe o su importador está corregido; el docstring contradictorio de `schemas.py` dice una sola cosa. Un alias canónico por concepto en la frontera de entrada del router CfC, con la tabla de mapeo español↔inglés en `docs/NAMING_CONVENTIONS.md`; `_STATE_KEYS` ya no contiene dos sinónimos. `_dispatch` (F-50) convertido en tabla de dispatch y `build_narrative` (F-57) dividido por sección narrativa; ningún bloque por encima de E.

**Criterio de aceptación.**
```bash
python -c "from extended_models import regla_bayesiana, regla_nash, regla_sir; print('shim OK')"
python - <<'PY'
import glob, re
pats = {}
for f in ["empirical_config.py","empirical_calibration.py","llm_credentials.py","state_compression.py","schemas.py","extended_models.py"]:
    try: t = open(f).read()
    except FileNotFoundError: continue
    pats[f] = ("deprecated::" in t, "warnings.warn" in t, "re-export" in t.lower())
assert len(set(pats.values())) == 1, pats
print("patrón de shim uniforme:", pats)
PY
python -W error::DeprecationWarning -c "import schemas" 2>&1 | head -1           # → warning controlado, no explosión
python -c "
from cfc_router import CfCRouter
k = CfCRouter._STATE_KEYS
assert not ('confianza' in k and 'trust' in k), k
print('_STATE_KEYS sin sinónimos:', k)"
grep -cE "^\| *(confianza|polarizacion|ruido|homofilia|pertenencia)" docs/NAMING_CONVENTIONS.md   # → ≥ 5
radon cc . -s -n E | grep -cE "^massive|^backend|^services"                      # → 0 bloques E o F
radon cc services/llm_orchestrator.py -s -n C | grep -c "_dispatch"              # → 0 (o ≤ C)
python -m pytest tests/ -q 2>&1 | tail -1                                        # → 0 failed
```

#### W5-T05 · Cobertura y calidad de la suite

| | |
|---|---|
| **Hallazgos** | `D4-002` · `D4-004` (cierre) · `D4-005` |
| **Tamaño** | L |
| **Depende de** | `W5-T02` · `W2-T01` |

**Resultado esperado.** Los 5 routers canónicos por encima del 80 % de cobertura con tests de contrato. Los 140 tests sin aserción asertan una propiedad nombrada. `fail_under` subido a la cobertura real menos 2 puntos, con política de ratchet documentada (+2 por release hasta 75 %). El scope de cobertura definido en un único sitio y consumido por CI sin enumeración manual de targets. La cifra del README generada desde CI (ya en `W4-T01`) coincide.

**Criterio de aceptación.**
```bash
python -m pytest tests/ -q --cov --cov-report=json:cov.json 2>&1 | tail -2
python - <<'PY'
import json
c = json.load(open("cov.json"))
routers = {k: v["summary"]["percent_covered"] for k, v in c["files"].items() if "backend/app/routers" in k}
print({k.split("/")[-1]: round(v,1) for k,v in routers.items()})
assert all(v >= 80 for v in routers.values()), routers
PY
python - <<'PY'
import ast, glob
noassert = []
for f in glob.glob("tests/**/*.py", recursive=True):
    t = ast.parse(open(f).read(), f)
    for n in t.body:
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith("test_"):
            has = any(isinstance(x,ast.Assert) or
                      (isinstance(x,ast.Expr) and isinstance(x.value,ast.Call) and
                       isinstance(x.value.func,ast.Attribute) and
                       x.value.func.attr in ("assertEqual","assertTrue","assertFalse","assertRaises",
                                             "assertIsNotNone","assertAlmostEqual","assertIn","raises","fails"))
                      for x in ast.walk(n))
            if not has: noassert.append(f"{f}:{n.lineno}:{n.name}")
print(f"tests sin aserción: {len(noassert)} (baseline 140)")
assert len(noassert) == 0, noassert[:10]
PY
python -c "import tomllib;p=tomllib.load(open('pyproject.toml','rb'))['tool']['coverage']['report'];
assert p['fail_under'] >= 57, p['fail_under']; print('fail_under =', p['fail_under'])"
grep -cE "ratchet" CONTRIBUTING.md docs/testing/*.md 2>/dev/null | grep -v ":0"  # → política documentada
grep -c "\-\-cov=" .github/workflows/pytest.yml                                 # → 0 (scope único en pyproject)
```

#### W5-T06 · Cabos sueltos de superficie pública

| | |
|---|---|
| **Hallazgos** | `D1-005` · `D1-006` · `D3-013` · `D7-019` |
| **Tamaño** | M |
| **Depende de** | `W5-T02` |

**Resultado esperado.** Decisión registrada sobre Mamba/SSM: restaurado como baseline con tests, o eliminado de toda la documentación y del material de producto. `streamlit` fuera de `requirements.txt`, topic retirado, y las 22 referencias a `app.py` corregidas o archivadas; `PLAN_INTEGRACION_UI_NG.md` archivado con banner. `massive-cli` con tests (help, corrida mínima, salida JSON, códigos de error) y cobertura ≥ 80 %; el target `cli-verify` del Makefile implementado y funcionando. `addopts` sin referencias a plugins inexistentes.

**Criterio de aceptación.**
```bash
grep -rci "mamba" --include="*.md" . | grep -v ":0" | wc -l                    # → 0, o el baseline existe
test -f tests/test_mamba_engine.py -o ! grep -rq "test_mamba_engine" --include="*.md" .
grep -c "streamlit" requirements.txt pyproject.toml                             # → 0 0
gh repo view --json repositoryTopics --jq '[.repositoryTopics[].name]|index(.)' 2>/dev/null
gh repo view --json repositoryTopics --jq '[.repositoryTopics[].name] | index("streamlit")'   # → null
grep -rl "app\.py" --include="*.md" . | grep -vc "docs/archive/"                # → 0
python -m pytest tests/test_cli.py -q 2>&1 | tail -1                            # → 0 failed
python -c "import json;c=json.load(open('cov.json'));
v=[x['summary']['percent_covered'] for k,x in c['files'].items() if 'massive/cli/main' in k][0];
assert v>=80, v; print('cli coverage', round(v,1))"
make cli-verify ; echo "cli-verify=$?"                                          # → 0
```

---

## 9. WAVE 6 · RENDIMIENTO, EVIDENCIA CIENTÍFICA Y CIERRE

Objetivo de la ola: que las afirmaciones de rendimiento y de validación científica sean reproducibles desde el repo, y cerrar la deuda de tipos y de complejidad restante. Al cierre, el proyecto puede sostener públicamente lo que declara.

**Gate de cierre de ola W6 (gate final del plan):**
```bash
make verify                                                     # → verde en todas las etapas
ls -A | wc -l                                                   # → ≤ 20
ls *.py | wc -l                                                 # → ≤ 8
python -m pytest tests/ -q 2>&1 | tail -1                       # → 0 failed
python -m pytest --cov -q 2>&1 | grep "Total coverage"          # → ≥ 70 %
mypy . 2>&1 | tail -1                                           # → Success (o < 20 errores documentados)
ruff check . && black --check .                                 # → 0 0
test -f reports/scalability/metrics.json && echo OK
python -m benchmarks.runner --cases datasets/real_cases --offline --out /tmp/pvu --seed 42 ; echo $?   # → 0
gh api repos/Adlgr87/MASSIVE/actions/runs?per_page=1 --jq '.workflow_runs[0].conclusion'             # → success
```

---

#### W6-T01 · Evidencia de escalabilidad reproducible

| | |
|---|---|
| **Hallazgos** | `D9-005` · `D9-009` · `D9-006` |
| **Tamaño** | L |
| **Depende de** | `W1-T03` · `W5-T02` |

**Resultado esperado.** `reports/scalability/{metrics.json, report.md}` commiteado, con metadata completa (`fecha`, `commit_sha`, `cpu_model`, `ram_gb`, `python_version`, `numpy_version`, `comando exacto`) y las cifras que respaldan la tabla del README. Dos tiers: tier CI (1K y 10K agentes) con baseline commiteado y tolerancia de ±20 %, ejecutado por un workflow; tier manual (`workflow_dispatch`) para 1M y 100M. `scripts/profile_hotspot.py` accesible vía `make profile`, escribiendo en `reports/profiling/` (gitignored). La documentación de rendimiento consolidada en `docs/performance/baseline.md` (en el nav); los documentos contradictorios archivados con banner. Las afirmaciones del README sobre memoria y cuantización describen exactamente lo que la evidencia soporta, incluido el comportamiento escalonado.

**Criterio de aceptación.**
```bash
test -f reports/scalability/metrics.json && python - <<'PY'
import json
d = json.load(open("reports/scalability/metrics.json"))
req = {"generated_at","commit_sha","cpu_model","ram_gb","python_version","numpy_version","command","results"}
assert req <= set(d), sorted(req - set(d))
print("metadata completa:", sorted(d))
PY
python benchmark_scalability.py --agents 1000 --steps 100 --json 2>&1 | tail -3   # → ejecuta y produce JSON
grep -c "reports/scalability" README.md                                            # → ≥ 1 (citado)
grep -cE "near-constant|uint8-quantized" README.md README_ES.md                    # → reformulado o respaldado
test -f .github/workflows/scale-regression.yml -o \
  grep -rc "benchmark_scalability" .github/workflows/*.yml | grep -v ":0"          # → ≥ 1
make profile && ls reports/profiling/ | wc -l                                      # → ≥ 1
git check-ignore -v reports/profiling/                                             # → ignorado
python -c "import yaml,json;n=json.dumps(yaml.safe_load(open('mkdocs.yml'))['nav']);
assert 'performance/baseline.md' in n; print('baseline en nav')"
grep -c "HISTÓRICO" REPORT_OPTIMIZATION.md docs/archive/reports/REPORT_OPTIMIZATION.md 2>/dev/null  # → ≥ 1
```

#### W6-T02 · Validación PVU sobre los casos reales y con baselines convergentes

| | |
|---|---|
| **Hallazgos** | `D4-011` · `D4-012` |
| **Tamaño** | M |
| **Depende de** | `W0-T01` (puede empezar en paralelo con cualquier ola) |

**Resultado esperado.** El comando por defecto de benchmark (README, Makefile, `pvu-validation.yml`, `publish.yml`) apunta a los 12 casos reales de `datasets/real_cases/`, o ejecuta ambos conjuntos y publica los dos resultados. `metrics.json` incluye por baseline un campo `converged` derivado de `mle_retvals`, y el runner distingue con código de salida distinto de 0 el caso "un baseline no convergió". El resultado de los 12 casos reales está commiteado en `reports/pvu_real_validation/` y citado desde el README. Si MASSIVE no supera al mejor baseline en el conjunto real, la tabla del README lo dice.

**Criterio de aceptación.**
```bash
PYTHONHASHSEED=42 python -m benchmarks.runner --cases datasets/real_cases --offline \
  --out /tmp/pvu_real --seed 42 ; echo "exit=$?"                                 # → 0, y 12 casos evaluados
python - <<'PY'
import json, glob
fs = glob.glob("/tmp/pvu_real/**/metrics.json", recursive=True)
assert len(fs) >= 10, len(fs)
d = json.load(open(fs[0]))
def walk(o):
    if isinstance(o, dict):
        if "converged" in o: yield o
        for v in o.values(): yield from walk(v)
    elif isinstance(o, list):
        for v in o: yield from walk(v)
conv = list(walk(d)); assert conv, "sin campo converged"
print(f"{len(fs)} casos · campo converged presente en {len(conv)} baselines")
PY
grep -cE "datasets/real_cases" Makefile .github/workflows/pvu-validation.yml \
  .github/workflows/publish.yml README.md | grep -v ":0" | wc -l                 # → ≥ 3
test -d reports/pvu_real_validation && ls reports/pvu_real_validation | wc -l     # → ≥ 2
grep -c "reports/pvu_real_validation" README.md                                  # → ≥ 1
grep -cE "N ≥ 10|N >= 10|12 casos|12 real" README.md                             # → ≥ 1
# el runner debe poder fallar:
python - <<'PY'
import subprocess, sys
r = subprocess.run([sys.executable,"-m","benchmarks.runner","--cases","datasets/pvu_cases",
                    "--offline","--out","/tmp/pvu_neg","--seed","42","--strict-convergence"],
                   capture_output=True, text=True)
print("exit con --strict-convergence:", r.returncode)
PY
```

#### W6-T03 · Paridad de implementaciones y deuda de rendimiento restante

| | |
|---|---|
| **Hallazgos** | `D9-008` · `D9-010` · `D9-011` |
| **Tamaño** | L |
| **Depende de** | `W5-T02` · `W3-T02` |

**Resultado esperado.** Test de paridad denso↔disperso sobre el mismo seed y la misma entrada, con tolerancia documentada; cobertura de `multilayer_engine_sparse.py` al nivel de la variante densa; el opt-out de mypy eliminado o con issue y fecha. Decisión registrada sobre el historial en memoria: o `PERF-01` lo resuelve y está documentado en `docs/performance/baseline.md`, o `state_compression.compress_agent_states` está cableado en el bucle de historial con flag de configuración y test de round-trip. El atributo muerto `_layers_csr` eliminado o usado. `radon cc --average` incorporado a `make verify` como check informativo con umbral de no-regresión sobre el baseline. El loop O(N²) de `network_inference/reconstruct.py` resuelto o explícitamente acotado por configuración con documentación del límite.

**Criterio de aceptación.**
```bash
python -m pytest tests/test_sparse_parity.py -q 2>&1 | tail -1                   # → 0 failed
python -c "import json;c=json.load(open('cov.json'));
v=[x['summary']['percent_covered'] for k,x in c['files'].items() if 'multilayer_engine_sparse' in k][0];
d=[x['summary']['percent_covered'] for k,x in c['files'].items() if k.endswith('multilayer_engine.py')][0];
print(f'sparse {v:.1f} vs densa {d:.1f}'); assert v >= d - 10, (v,d)"
grep -c "multilayer_engine_sparse" pyproject.toml mypy.ini 2>/dev/null            # → 0, o con issue+fecha
grep -rc "compress_agent_states" --include="*.py" . | grep -v "state_compression" | grep -v ":0" | wc -l   # → ≥ 1
python - <<'PY'
import numpy as np, tempfile, os
from massive.core.state_compression import compress_agent_states, decompress_agent_states
x = np.random.default_rng(0).uniform(-1,1,(500,6))
c = compress_agent_states(x, max_bond_dim=32)
r = decompress_agent_states(c)
print("round-trip shape", r.shape, "explained_variance ok")
assert r.shape[1] == x.shape[1]
PY
grep -c "_layers_csr" massive_engine.py                                          # → 0, o con consumidor
make verify 2>&1 | grep -i "radon"                                               # → presente
python -c "import subprocess;o=subprocess.run(['radon','cc','.','-s','-n','B','--average'],
  capture_output=True,text=True).stdout; print(o.strip().splitlines()[-1])"      # → ≤ B (9.6)
python -m pytest tests/ -q 2>&1 | tail -1                                        # → 0 failed
```

#### W6-T04 · Cierre de deuda de tipos, adopción de reglas y señal social

| | |
|---|---|
| **Hallazgos** | `D2-003` (repo-wide) · `D7-014` (cierre) · `D8-007` · `D4-013` (preservar) · `D2-017` (cierre) |
| **Tamaño** | L |
| **Depende de** | `W5-T01` · `W5-T02` · `W5-T05` |

**Resultado esperado.** mypy repo-wide por debajo de 20 errores, con los restantes listados y con issue asignado. `check_untyped_defs = True` global, sin opt-outs sin fecha. `strict = True` en los paquetes del slice científico. Reglas `PT`, `RUF` y `FAST` habilitadas en el `select` de ruff, con los 230 `PT009` y los 16 `PT018` migrados a asserts de pytest. `CITATION.cff` y una sección "Citing MASSIVE" en el README. Al menos un release publicado con notas (ya en `W3-T04`). Los 148 hallazgos del reporte cerrados o con issue abierto y etiquetado `debt`.

**Criterio de aceptación.**
```bash
mypy . --ignore-missing-imports 2>&1 | tail -1                                  # → < 20 errores
mypy . --ignore-missing-imports 2>&1 | grep -oE "\[[a-z-]+\]$" | sort | uniq -c | sort -rn | head -5
python -c "import tomllib;m=tomllib.load(open('pyproject.toml','rb'))['tool']['mypy'];
assert m.get('check_untyped_defs') is True; assert m.get('strict') is True or 'overrides' in m; print(m)"
ruff check . --select PT,RUF,FAST ; echo $?                                     # → 0
ruff check . --select PT009 | wc -l                                             # → 0
test -f CITATION.cff && python -c "import yaml;d=yaml.safe_load(open('CITATION.cff'));
assert {'title','authors','version'} <= set(d); print('CITATION.cff OK', d['version'])"
grep -c "Citing MASSIVE\|CITATION.cff" README.md                                # → ≥ 1
python - <<'PY'
import re
rows = re.findall(r"^\| (D\d-\d{3}) \|.*\| (\S+) \|$", open("docs/AUDIT_FINDINGS_TRACKER.md","rb").read().decode(), re.M)
open_ids = [i for i,s in rows if s.upper() not in ("CERRADO","RESUELTO","GUARDRAIL","WONTFIX")]
print(f"{len(rows)} filas · {len(open_ids)} abiertas")
assert len(rows) == 148, len(rows)
PY
gh issue list --label debt --state open --limit 200 --json number | \
  python -c "import json,sys;print(len(json.load(sys.stdin)),'issues de deuda abiertos y etiquetados')"
python -m pytest tests/ -q 2>&1 | tail -1                                       # → 0 failed (D4-013 preservado)
make verify                                                                     # → verde
```

---

## 10. MATRIZ DE COBERTURA HALLAZGO → TAREA

Los 148 hallazgos del reporte, asignados. `✓` = la tarea lo cierra; `→` = la tarea lo avanza y otra lo cierra; `G` = guardarraíl (no requiere acción; se verifica en `W0-T01`).

| ID | Tarea | | ID | Tarea | | ID | Tarea |
|---|---|---|---|---|---|---|---|
| D1-001 | W1-T01 ✓ | D4-001 | W1-T09 ✓ | D7-001 | W0-T01 → PE-1 ✓ |
| D1-002 | W1-T02 ✓ | D4-002 | W5-T05 ✓ | D7-002 | W3-T05 ✓ |
| D1-003 | W1-T01 ✓ | D4-003 | W5-T03 → W5-T06 ✓ | D7-003 | W2-T09 ✓ |
| D1-004 | W1-T03 ✓ · W3-T05 → | D4-004 | W2-T01 → W5-T05 ✓ | D7-004 | W1-T04 ✓ |
| D1-005 | W5-T06 ✓ | D4-005 | W5-T05 ✓ | D7-005 | W1-T04 → W3-T03 ✓ |
| D1-006 | W5-T06 ✓ | D4-006 | W1-T03 ✓ | D7-006 | W2-T06 ✓ |
| D1-007 | W0-T03 G | D4-007 | W1-T10 ✓ | D7-007 | W5-T01 ✓ |
| D1-008 | W2-T05 ✓ | D4-008 | W1-T10 ✓ | D7-008 | W3-T04 ✓ |
| D1-009 | W3-T05 ✓ | D4-009 | W1-T10 ✓ | D7-009 | W3-T02 ✓ |
| D1-010 | W0-T01 G | D4-010 | W1-T01 ✓ | D7-010 | W2-T09 ✓ |
| D1-011 | W1-T04 ✓ | D4-011 | W6-T02 ✓ | D7-011 | W3-T03 ✓ |
| D2-001 | W1-T06 ✓ | D4-012 | W6-T02 ✓ | D7-012 | W2-T09 ✓ |
| D2-002 | W1-T06 ✓ | D4-013 | W0-T01 G | D7-013 | W2-T09 ✓ |
| D2-003 | W2-T06 → W6-T04 ✓ | D4-014 | W1-T10 ✓ | D7-014 | W1-T07 → W6-T04 ✓ |
| D2-004 | W1-T07 ✓ | D5-001 | W2-T01 ✓ | D7-015 | W3-T03 ✓ |
| D2-005 | W2-T05 ✓ | D5-002 | W3-T01 ✓ | D7-016 | W2-T03 ✓ |
| D2-006 | W2-T07 ✓ | D5-003 | W2-T10 ✓ | D7-017 | W0-T01 G |
| D2-007 | W0-T01 G | D5-004 | W2-T10 ✓ | D7-018 | W0-T01 ✓ |
| D2-008 | W2-T04 ✓ · W2-T05 → | D5-005 | W1-T03 ✓ | D7-019 | W5-T06 ✓ |
| D2-009 | W2-T05 ✓ | D5-006 | W2-T10 ✓ | D7-020 | W1-T05 ✓ |
| D2-010 | W2-T05 ✓ | D5-007 | W2-T10 ✓ | D8-001 | W4-T02 → W5-T02 ✓ |
| D2-011 | W5-T04 ✓ | D5-008 | W1-T02 ✓ | D8-002 | W3-T01 → W3-T04 ✓ |
| D2-012 | W5-T03 ✓ | D5-009 | W2-T02 ✓ | D8-003 | W1-T08 ✓ |
| D2-013 | W5-T03 ✓ | D5-010 | W2-T02 ✓ | D8-004 | W1-T08 ✓ |
| D2-014 | W5-T04 ✓ | D5-011 | W2-T10 ✓ | D8-005 | W4-T01 ✓ |
| D2-015 | W0-T01 G | D5-012 | W2-T10 ✓ | D8-006 | W0-T02 ✓ |
| D2-016 | W2-T08 ✓ | D5-013 | W2-T02 ✓ | D8-007 | W6-T04 ✓ |
| D2-017 | W1-T06 → W6-T04 ✓ | D5-014 | W2-T03 ✓ | D8-008 | W0-T01 G |
| D3-001 | W3-T01 ✓ | D5-015 | W2-T03 ✓ | D8-009 | W0-T01 G |
| D3-002 | W5-T01 ✓ | D5-016 | W3-T04 ✓ | D8-010 | W4-T01 ✓ |
| D3-003 | W5-T01 ✓ | D5-017 | W0-T01 G | D8-011 | W4-T05 ✓ |
| D3-004 | W2-T01 ✓ | D5-018 | W0-T01 G · W0-T03 | D8-012 | W1-T05 ✓ · W0-T03 |
| D3-005 | W5-T01 ✓ | D5-019 | W1-T05 ✓ | D9-001 | W2-T04 ✓ |
| D3-006 | W5-T02 ✓ | D5-020 | W1-T05 ✓ | D9-002 | W2-T04 ✓ |
| D3-007 | W5-T02 ✓ | D5-021 | W1-T05 ✓ | D9-003 | W2-T04 ✓ |
| D3-008 | W5-T02 ✓ | D5-022 | W1-T05 ✓ | D9-004 | W2-T07 ✓ |
| D3-009 | W5-T04 ✓ | D5-023 | W2-T02 ✓ | D9-005 | W6-T01 ✓ |
| D3-010 | W5-T02 ✓ | D5-024 | W0-T02 ✓ | D9-006 | W6-T01 ✓ |
| D3-011 | W4-T05 ✓ | D6-001 | W4-T01 ✓ | D9-007 | W3-T02 ✓ |
| D3-012 | W5-T02 ✓ | D6-002 | W4-T01 ✓ | D9-008 | W6-T03 ✓ |
| D3-013 | W5-T06 ✓ | D6-003 | W4-T02 ✓ | D9-009 | W6-T01 ✓ |
| D3-014 | W3-T03 ✓ | D6-004 | W4-T03 ✓ | D9-010 | W6-T03 ✓ |
| D3-015 | W0-T01 G | D6-005 | W4-T03 ✓ | D9-011 | W6-T03 ✓ |
| D3-016 | W5-T02 ✓ | D6-006 | W1-T08 ✓ |  |  |
| D3-017 | W3-T02 ✓ | D6-007 | W4-T03 ✓ · W6-T01 → |  |  |
| D3-018 | W3-T02 ✓ | D6-008 | W4-T03 ✓ |  |  |
| D3-019 | W2-T08 ✓ | D6-009 | W4-T04 ✓ |  |  |
| D3-020 | W0-T01 G · W2-T08 | D6-010 | W4-T03 ✓ |  |  |
|  |  | D6-011 | W4-T03 ✓ |  |  |
|  |  | D6-012 | W3-T04 ✓ |  |  |
|  |  | D6-013 | W1-T08 ✓ |  |  |
|  |  | D6-014 | W4-T01 ✓ |  |  |
|  |  | D6-015 | W4-T04 ✓ |  |  |
|  |  | D6-016 | W1-T08 ✓ |  |  |
|  |  | D6-017 | W1-T08 ✓ |  |  |
|  |  | D6-018 | W0-T01 G · W4-T03 → |  |  |
|  |  | D6-019 | W0-T01 G |  |  |

**Verificación de cobertura:** 148 IDs del reporte · 0 sin asignar · 43 tareas declaradas y 43 citadas. De los 17 hallazgos 🟢, 14 son guardarraíles puros (ninguna acción, sólo verificación en `W0-T01`) y 3 tienen acción residual asociada (`D7-018` → targets nuevos de Makefile, `D8-012` → corrección del typo de `.gitignore`, `D9-011` → check informativo de `radon`). Los 131 restantes tienen tarea de cierre.

---

## 11. PATRONES SISTÉMICOS → TAREA QUE LOS ATACA

Cada patrón de la sección 5 del reporte tiene una tarea cuyo resultado esperado lo desactiva estructuralmente, no sólo en sus síntomas:

| Patrón | Tarea estructural | Mecanismo |
|---|---|---|
| 1 · Migraciones a mitad | `W5-T01` + `W5-T02` + `W4-T05` | `CANONICAL_SOURCES.md` con fecha de retirada por shim; "hecho" incluye eliminar el estado anterior |
| 2 · Docs no reconciliadas | `W4-T01` + `W4-T03` | Documentación derivada generada por script con gate de diff vacío; link-checker; tiers viva/histórica |
| 3 · Señal incapacitada | `W0-T01` + `W2-T06` + `W5-T05` + `W6-T04` | `make verify` único; retirada de `\|\| true` y `continue-on-error`; ratchet de cobertura y de mypy |
| 4 · Puntos de entrada múltiples | `W5-T01` | Un canónico por categoría, declarado y enlazado desde `CONTRIBUTING.md` y `AGENTS.md` |
| 5 · Contratos no aplicados | `W2-T01` + `W2-T04` + `W4-T01` | DTOs como cuerpos de request; docstring→test; cifras del README generadas |
| 6 · Camino feliz vs. degradación | `W3-T05` | Job `clean-clone` + matriz de dependencias mínimas + smoke del smoke en el contenedor |
| 7 · Artefactos de runtime | `W1-T05` + `W2-T05` | `.gitignore`/`.gitattributes` efectivos; cero side-effects de import; check anti-rutas personales |
| 8 · Escala afirmada, no medida | `W6-T01` + `W6-T02` | Baselines commiteados con metadata; tier CI + tier manual; casos reales por defecto |
| 9 · Complejidad > verificación | `W5-T06` + `G-3` + `W6-T04` | Regla de no añadir superficie sin verificación; tracker de los 148 con presupuesto de deuda |

---

## 12. RESUMEN DE EJECUCIÓN

| Ola | Tareas | Ancho paralelo | Bloqueante para | Cierre requiere |
|---|---|---|---|---|
| **W0** Harness y gobernanza | 3 | 3 pistas | todas las olas | `make verify` existe y mide |
| **W1** Desbloqueo | 10 | 5 pistas | W2, W3 | clone limpio: import + pytest 0 failed + ruff/black 0 |
| **W2** Camino canónico | 10 | 4 pistas | W3, W5 | DTOs con cotas, `/metrics` protegido, typecheck puede fallar |
| **W3** Build y despliegue | 5 | 4 pistas | W5 | `pip install -e .` OK, wheel importable, imagen verificada, tag creado |
| **W4** Verdad documental | 5 | 3 pistas | — (paralela a W3) | 0 refs rotas, README generado, ≤ 8 `.md` en root |
| **W5** Consolidación | 6 | 2 pistas | W6 | 1 backend, 1 frontend, ≤ 8 `.py` en root, ≤ 20 entradas root |
| **W6** Rendimiento y cierre | 4 | 3 pistas | — | evidencia reproducible commiteada, mypy < 20, gate final verde |
| **Total** | **43 tareas** | máx. 5 pistas | | **148 hallazgos cubiertos** |

**Puntos de no retorno** (decisiones que condicionan todo lo posterior y deben tomarse al inicio de su ola, registradas en `CANONICAL_SOURCES.md` según `G-5`):

1. `W1-T02` — torch duro (A) o fallback NumPy real (B). Afecta a `pytest.yml`, al wheel, al Dockerfile y a 25 módulos.
2. `W1-T09` — pesos CfC vía LFS (a), skips con descarga (b) o regeneración en CI (c). Afecta a la afirmación del README sobre Brexit.
3. `W3-T01` — backend de build y nombre de distribución en PyPI. Afecta a toda la cadena de publicación.
4. `W5-T01` — qué backend y qué frontend sobreviven. Afecta a `W5-T02`, `W5-T04` y a todo el trabajo posterior de módulos.

**Condición de éxito del plan completo:** el gate final de la sección 9 verde en `main`, en un run real de GitHub Actions, sobre un clone limpio, con los 148 hallazgos en estado `CERRADO`, `RESUELTO`, `GUARDRAIL` o `WONTFIX` justificado en `docs/AUDIT_FINDINGS_TRACKER.md`.

---

*Fin del workflow. 43 tareas · 7 olas · 148 hallazgos asignados · 0 huérfanos.*
