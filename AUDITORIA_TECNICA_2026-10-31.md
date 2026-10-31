# Auditoría Técnica — `Adlgr87/MASSIVE` (estado actual de GitHub)

**Fecha:** 2026-10-31 (verificación fresca contra `origin/main`)
**Rol:** Ingeniero de Software Senior / Arquitecto de Sistemas
**Método:** hechos comprobados ejecutando el código y leyendo diffs reales; las hipótesis de rendimiento están marcadas como tales.

---

## 0. Hecho que condiciona todo el análisis

`origin/main` sigue en **`b59c2ba`** ("Prod readiness (#159)"). Los PRs de remediación
**#160** y **#161** siguen **ABIERTOS, sin mergear** (`mergedAt: null`).

> **Consecuencia:** "el repositorio actual de GitHub" (lo que un `git clone` recibe por
> defecto) es **todavía el estado roto**. Las modificaciones recientes existen como PRs
> verdes pero no han llegado a `main`. Este es el riesgo número uno y el más fácil de
> resolver: **mergear #160 → main y #161 → prod-readiness**.

---

# FASE 1 — Detección de Desperfectos y Riesgos

## 1.1 Defectos CRÍTICOS en `main` (verificados por ejecución, no por inspección)

| # | Defecto | Evidencia comprobada | Impacto |
|---|---|---|---|
| **D1** | `pyproject.toml:82` declara el py-module `social_connectors`, que fue eliminado | `git show origin/main:pyproject.toml \| grep social_connectors` → presente; el archivo no existe | Rueda con declaración inválida (setuptools sólo avisa); `grep -rn social_connectors --include=*.py` en código → fallback roto en `compare_arms.py` |
| **D2** | El gate de tipos de CI está roto | `.github/workflows/lint.yml:54` ejecuta `mypy --config-file mypy.ini`; `mypy.ini` fue borrado. mypy sale con **exit 2** | El badge "Type-check: MyPy (blocking)" no valida nada; el job falla en cada run |
| **D3** | **La imagen Docker no se puede construir** | `Dockerfile:61-62` hace `COPY nginx.conf` y `COPY supervisord.conf`; **ninguno existe** → `failed to compute cache key: "/supervisord.conf": not found` | `compose-build-health` en rojo permanente; el README anuncia Docker que no funciona |
| **D4** | gitleaks escanea 0 bytes | `secret_scan.yml` con `actions/checkout@v4` (fetch-depth 1); gitleaks resuelve `BASE^..HEAD` → `ambiguous argument` | El escaneo de secretos es un no-op en PRs |
| **D5** | black/ruff sin pin en CI | `lint.yml:27` → `pip install ruff black mypy` (última versión) vs. `black==24.10.0` fijado en `pyproject.toml` | black nuevo exige reformatear `cache_manager.py`/`compare_arms.py` que están bien formateados según el pin del proyecto → `Python Lint` en rojo |

## 1.2 Impacto verificado de las modificaciones recientes (PRs #160 y #161)

Los dos PRs están **verdes en CI real** (GitHub Actions) y corrigen exactamente los 5 defectos
anteriores más un conjunto de defectos funcionales profundos:

| Área | Cambio verificado | Estado CI |
|---|---|---|
| Docker | `nginx.conf` (160 líneas, no-root) + `supervisord.conf` (uvicorn `0.0.0.0:8000` + nginx `:80`) creados | `compose-build-health` ✅ 3m53s |
| Type gate | `lint.yml` delega en `scripts/typecheck_slice.py`; slice 25→32 archivos | `Type Check (MyPy)` ✅ |
| Lint | black/ruff leídos de `[dev]` de `pyproject.toml` (sin deriva) | `Python Lint` ✅ |
| Secretos | `fetch-depth: 0` en el job incremental | `incremental` ✅ |
| Disparadores CI | `pull_request` sin filtro de ramas (antes sólo `main/master`) | PRs a `prod-readiness` ya reciben checks ✅ |
| **Acoplamiento** | Matriz declarada `DEFAULT_COUPLING_GAINS`: 2→6 vínculos (30% densidad), ciclo cerrado, signo configurable | 989 tests ✅ |
| **Sellos** | `seal_splits()`/`pre_register()` inmutables; `pytest` ya no reescribe 6 artefactos versionados | árbol limpio ✅ |
| **`dynamic_rewiring`** | bug: la censura modificaba la vista densa pero `step()` lee la sparse → intervenciones inertes; corregido | `multilayer_engine.py` tipado ✅ |
| API | `POST /v1/engine/multilayer` expone `coupling`/`dt`/`coupling_gains` (antes inalcanzables) | 10 tests de contrato ✅ |

## 1.3 Desperfectos REMANENTES (no resueltos por los PRs — el trabajo pendiente real)

### Críticos

**R1 — La imagen Docker arrastra ~2.6 GB de stack CUDA para un simulador CPU.**
`requirements.txt:28` fija `torch>=2.2.0` sin índice CPU. `docker build` descargó: `torch 539 MB`,
`cudnn 519 MB`, `cublas 405 MB`, `triton 286 MB`, `cusolver 228 MB`… Medido: el build agotó 15 min
sólo descargando CUDA. **Hipótesis de impacto:** `pip install --index-url https://download.pytorch.org/whl/cpu`
lo reduciría a ~200 MB (~13× menos) y aceleraría el build de CI de minutos a segundos.

**R2 — `MultilayerEngine` sigue siendo O(N²) en memoria (no escala).**
`build_layers()` devuelve matrices **densas** (`nx.to_numpy_array`). Medido en esta sesión:
`N=4000 → self.layers denso = 384 MB, pico init = 529 MB`. Extrapolado: `N=10000 → 2.4 GB`,
`N=100000 → 240 GB`. El README promete "100M agentes en ~8 GB", pero eso **sólo** lo cumple
`MassiveSimEngine` (LOD); `MultilayerEngine` —el motor que expone `/v1/engine/multilayer`— muere
antes de `N=10000`. Es una asimetría no documentada entre el marketing y la API.

### Altos

**R3 — El type gate sólo cubre 32 de ~230 archivos.** El "blocking" mypy es un slice. El ámbito
completo (`massive/ backend/ services/ massive_core/`) todavía tiene **26 errores en 6 archivos**:
`physics_calibration.py` (8), `abcsbi.py` (8), `convergence_certifier.py` (4), `schemas.py` (3),
`cli/main.py` (2), `network_inference/reconstruct.py` (1).

**R4 — Módulos con cobertura crítica baja.** `ground_truth/_generate.py` **0%** (324 stmts) — el
generador de la *ground truth sellada* no tiene un solo test, pese a que de él dependen los sellos.
`massive_core/network_inference/reconstruct.py` 21%, `massive/core/extended_models.py` 26.5%
(Nash/Bayes/SIR que el README anuncia), `perturbation_theory.py` 33%.

**R5 — `api.py` legacy sigue presente.** Tras mi corrección, el frontend **no** lo consume
(`api.ts` usa `baseURL: "/v1"` y lo declara explícitamente), pero el módulo (506 líneas) sigue en el
árbol con su contrato `/api/*` divergente. Ya emite `DeprecationWarning`, pero no tiene fecha de
retirada y `install.sh`/`Makefile`/`massive serve --legacy` aún lo referencian.

### Medios

**R6 — Inconsistencia de contrato de forecast.** `massive.cli forecast` imprime
`{p_event, steps_to_event, days_to_event, confidence}`, mientras `POST /v1/forecast` devuelve
`{sim_id, horizon_ticks, points, feasibility}`. Dos formas del mismo motor, sin un solo contrato.

**R7 — Inconsistencia de tipos.** `TemporalConfig(event_type=...)` en el CLI: mypy reporta
`Missing named argument "time_horizon_days"` pero no crashea en runtime (hay un default implícito no
declarado en el type hint). Pydantic dice "requerido", el runtime dice "opcional".

### Bajos

**R8 — Higiene.** 16 ramas remotas (5 fusionadas/stale); 115 archivos `.md` con solapamiento
(marcado `docs/archive/` como no normativo, pero sin consolidar); ~120 referencias a módulos
eliminados que viven en docs de archivo (legítimas como historia, pero sin índice que las marque).

---

# FASE 2 — Plan de Acción y Estrategia de Mitigación

## P0 — Crítica (bloqueante, antes de cualquier feature)

| # | Intervención | Porqué técnico | Criterio de validación |
|---|---|---|---|
| P0.1 | **Mergear #160 → `main`** | `main` está roto en empaquetado y CI; todo trabajo futuro hereda el defecto. Es un sync mínimo (2 commits + fixes de CI/Docker) | `main` compila la rueda sin warning; los 5 jobs de CI pasan en `main` |
| P0.2 | **Mergear #161 → `prod-readiness`** | Es la remediación profunda (sellos, acoplamiento, API, rewiring) ya verde en CI | 989 tests; árbol limpio tras `pytest`; `/v1/engine/multilayer` responde |

## P1 — Alta

| # | Intervención | Porqué | Validación |
|---|---|---|---|
| P1.1 | **R1 — torch CPU en Docker** (build arg con default CPU) | Elimina 2.6 GB de artefactos inútiles; acelera CI y reduce la imagen | `docker build` < 5 min; tamaño de imagen < 1.5 GB; GPU opt-in vía `--build-arg` |
| P1.2 | **R2 — capas sparse en `MultilayerEngine`** | Rompe el cuello O(N²) del motor que expone la API | `N=20000` inicializa en < 1 GB; `pytest tests/test_multilayer*` verde; `dynamic_rewiring` sobre CSR |
| P1.3 | **R5 — plan de retirada de `api.py`** | Elimina una superficie con contrato divergente y sin consumidores | Fecha de sunset en docstring; `--legacy` marcado `deprecated`; CI sin referencias a `api:app` |

## P2 — Media

| # | Intervención | Porqué | Validación |
|---|---|---|---|
| P2.1 | **R3 — cerrar los 26 errores mypy** y ampliar el slice | El badge "blocking" hoy valida 32 archivos; el resto no está protegido | `mypy massive/ backend/ services/ massive_core/` → 0 errores; slice cubre ≥ 80% de módulos |
| P2.2 | **R4 — tests de `_generate.py`, `extended_models`, `network_inference`** | Código anunciado sin cobertura es código no verificado (y el generador sella datos) | `_generate.py` ≥ 60%; los tres módulos ≥ 60% |
| P2.3 | **R6/R7 — unificar contrato de forecast y tipar `TemporalConfig`** | Una sola forma de respuesta; el type hint debe reflejar el runtime | `cli forecast` y `/v1/forecast` emiten el mismo esquema; mypy sin error en `cli/main.py` |

## P3 — Baja

| # | Intervención | Porqué | Validación |
|---|---|---|---|
| P3.1 | **R8 — podar ramas y consolidar docs** | Menos ruido de navegación | 11 ramas; índice único con mapa canónico/histórico |

---

# FASE 3 — Propuesta de Modificaciones (código)

> Las propuestas D1–D5 **ya están implementadas** en los PRs #160/#161. Se muestran aquí como
> referencia de parche. R1 y R2 son **nuevas** y no están en ningún PR.

## P0 — D1: declaración inválida de `social_connectors` (ya en #160)

**Ubicación:** `pyproject.toml:82`
```diff
   "micro_engine", "micro_schemas", "multilayer_engine",
   "programmatic_architect", "simulator",
-  "social_architect", "social_connectors",
+  "social_architect",
   "uil_adapter", "visualizations",
```
**Justificación:** un py-module inexistente es una declaración muerta; eliminar evita el warning de
build y el fallback roto. Validación: `tests/test_packaging_contract.py::test_every_py_module_exists`.

## P0 — D3: los dos archivos que faltaban para Docker (ya en #160)

**Ubicación:** `nginx.conf` (nuevo) y `supervisord.conf` (nuevo). Contenido ya presentado en los
deliverables. Puntos de diseño no negociables que se codificaron:
- nginx **sin root**: `pid /tmp/nginx.pid`, todos los `*_temp_path` en `/tmp`, sin directiva `user`.
- uvicorn en `0.0.0.0:8000` (el `docker-compose` publica `8000:8000` y el smoke test pega desde el
  host; loopback dejaría el puerto muerto).
- supervisord **sin `user=`** (arranca ya como `appuser`; supervisord sólo puede *bajar* privilegios).

**Validación real:** `nginx -t` como UID 1000 ✅ · `ServerOptions.realize` ✅ · `compose-build-health` ✅.

## P1.1 — R1: torch CPU por defecto (NUEVO)

**Ubicación:** `Dockerfile`, etapa `builder-py` (la que ejecuta `pip wheel -r requirements.txt`).
```diff
+ARG TORCH_INDEX="https://download.pytorch.org/whl/cpu"
+
 # Install python deps from wheels built in Stage 1
-RUN pip wheel --no-cache-dir -w /wheels -r requirements.txt
+RUN pip wheel --no-cache-dir -w /wheels \
+      --extra-index-url "${TORCH_INDEX}" \
+      -r requirements.txt
```
**Justificación:** el simulador corre en CPU; `torch>=2.2.0` sin índice resuelve el build CUDA
(~2.6 GB). Con índice CPU, pip baja `torch` CPU (~200 MB) y **ningún** paquete `nvidia-*`. Para un
build GPU el operador pasa `--build-arg TORCH_INDEX="https://download.pytorch.org/whl/cu124"`.
**Impacto (hipótesis):** imagen ~13× más ligera; `compose-build-health` de ~4 min a <1 min.

## P1.2 — R2: capas sparse en `MultilayerEngine` (NUEVO)

**Ubicación:** `multilayer_engine.py`, `build_layers()` (líneas 248–270 aprox.) y
`MultilayerEngine.__init__` (donde se materializa `self.layers`).

**Estado actual (denso, O(N²)):**
```python
def build_layers(N: int, config: dict | None = None) -> dict:
    # ...
    return {
        "social": generate_watts_strogatz(N, ...),   # np.ndarray (N,N) float64
        "digital": generate_scale_free(N, ...),
        "economic": generate_hierarchical(N, ...),
    }
```

**Estado optimizado (sparse, O(N·k)):**
```python
from scipy import sparse as sp

def _to_csr(adjacency: np.ndarray) -> sp.csr_matrix:
    return sp.csr_matrix(adjacency)

def build_layers(N: int, config: dict | None = None, *, sparse: bool = True) -> dict:
    layers = {
        "social": generate_watts_strogatz(N, ...),
        "digital": generate_scale_free(N, ...),
        "economic": generate_hierarchical(N, ...),
    }
    if sparse:
        return {name: _to_csr(a) for name, a in layers.items()}
    return layers
```
Y en `__init__`, reemplazar la doble representación por **una sola vista CSR**:
```python
self.layers = build_layers(N, layer_config, sparse=True)
self._layers_sparse = [self.layers[n] for n in LAYER_NAMES]
```
`dynamic_rewiring` debe operar sobre CSR (o convertir a COO, editar, re-normalizar filas) en vez de
indexación densa. **Justificación:** el `matmul` sparse es O(N·k), y la memoria pasa de O(N²) a O(N).
**Impacto medido (hipótesis):** `N=4000` de 529 MB → ~40 MB; habilita `N=100k` en el motor multicapa.
**Riesgo:** `dynamic_rewiring` y `tests/test_integrated_dynamics.py` (que hacen `.copy()` y
comparaciones `> 0` sobre la matriz) deben adaptarse; hay que preservar el API `self.layers` para no
romper consumidores.

## P2.1 — R3: cerrar el ámbito mypy (prioridad sobre los 8 de `physics_calibration`)

**Ubicación:** `massive/core/physics_calibration.py` (8 errores) — son los más numerosos y afectan
a la calibración, el camino científico central. El patrón típico es `dict[str, Any]` sin tipar
retornado como si fuera un modelo. **Modificación propuesta** (representativa):
```diff
- def load_calibrated_params(path: str) -> "PhysicsParams":
-     raw = yaml.safe_load(open(path))
-     return PhysicsParams(**raw)
+ def load_calibrated_params(path: str) -> "PhysicsParams":
+     raw: dict[str, Any] = yaml.safe_load(open(path))
+     return PhysicsParams(**raw)
```
**Justificación:** la causa raíz de los 26 errores no es lógica, es ausencia de anotaciones en el
límite YAML→modelo; tipar el dict intermedio elimina la cascada de `Any`. Validación:
`mypy --config-file pyproject.toml massive/ backend/ services/ massive_core/` → 0 errores, y añadir
esos módulos al slice bloqueante.

## P2.3 — R6/R7: contrato de forecast único + tipado correcto

**Ubicación:** `massive/cli/main.py:114` (construcción de `TemporalConfig`) y `forecast/engine.py`.
```diff
- tc = TemporalConfig(event_type=args.event_type)
+ tc = TemporalConfig(event_type=args.event_type, time_horizon_days=DEFAULT_HORIZON_DAYS)
```
Y que `_cmd_forecast` emita el **mismo** `ForecastResponse` que el router (con `points`/`feasibility`)
en lugar del dict crudo del motor. **Justificación:** dos superficies que producen esquemas distintos
para el mismo cálculo rompen la "única fuente de verdad" que el propio README reclama.

---

## Resumen ejecutivo

1. **Hecho:** `main` sigue roto; los PRs verdes #160/#161 están sin mergear. **Acción inmediata: merge.**
2. **Desperfectos de `main` (5 críticos)** ya corregidos y verificados en CI por los PRs.
3. **Pendiente real:** R1 (torch CUDA 2.6 GB), R2 (`MultilayerEngine` O(N²)), R3 (mypy 26 errores),
   R4 (cobertura 0–33% en módulos anunciados), R5 (`api.py` sin retirar), R6/R7 (contrato forecast),
   R8 (higiene).
4. **Separación hecho/hipótesis:** los defectos D1–D5, R2 (384 MB @ N=4000) y R3 (26 errores) están
   **medidos**. Los ahorros de R1 (~13×) y R2 (habilitar N=100k) son **estimaciones** a validar tras
   implementar.
