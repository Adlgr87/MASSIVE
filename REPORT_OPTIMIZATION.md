# Reporte de Optimización — MASSIVE

**Fecha:** 2025-07-24  
**Analista:** Performance Engineer (Agnes)  
**Alcance:** Código Python core (engines, services, routers)  
**Método:** Análisis estático + revisión de benchmarks existentes

---

## Executive Summary

El proyecto MASSIVE tiene **tres problemas de rendimiento críticos** que limitan su escalabilidad en producción:

1. **Engine Python fallback sin Numba** — 10× más lento que la ruta JIT compilada
2. **Network inference con loops O(N²)** — inusable para N > 100 agentes
3. **Historial de estado completo en memoria** — O(steps × N × K) bytes acumulados

Adicionalmente hay **issues de async** y **lotes de llamadas síncronas** que bloquean el event loop en producción.

---

## 1. Performance Bottlenecks

### CRÍTICO — EnergyEngine: Python fallback path (10× slowdown)

| Ubicación | Problema | Impacto | Recomendación |
|-----------|----------|---------|---------------|
| `energy_engine.py:498-507` | Bucle Python sin JIT cuando `NUMBA_AVAILABLE=False` | **10× más lento** que ruta JIT; bloquea event loop en requests concurrentes | Instalar numba como dependencia obligatoria en `[full]`; agregar warning en docs de deploy |
| `energy_engine.py:443-455` | Creación de arrays temporales `[a["position"] for a in attractors]` en cada paso | CPU wasted en allocation por paso; N attractors×steps allocs | Extraer arrays una vez en `__init__` o cache them si son estables |
| `energy_engine.py:459-467` | Drift function con loop Python `for i in range(n)` | Usado por scientific stepper; same 10× penalty que fallback | Migrate `_landscape_gradient` a versión vectorizada numpy o JIT |

**Fix propuesto (drift vectorizado):**
```python
# Replace the Python loop in drift() with:
att_positions = np.array([a["position"] for a in attractors], dtype=np.float64)
att_strengths = np.array([a["strength"] for a in attractors], dtype=np.float64)
rep_positions = np.array([r["position"] for r in repellers], dtype=np.float64)
rep_strengths = np.array([r["strength"] for r in repellers], dtype=np.float64)
sigma2 = _SIGMA ** 2

# Vectorized gradient computation (no Python loop)
diff_att = current[:, None] - att_positions[None, :]  # (n, n_att)
grad_att = att_strengths[None, :] * diff_att / sigma2 * np.exp(-diff_att**2 / (2 * sigma2))
grad = grad_att.sum(axis=1)

diff_rep = current[:, None] - rep_positions[None, :]
grad_rep = rep_strengths[None, :] * diff_rep / sigma2 * np.exp(-diff_rep**2 / (2 * sigma2))
grad -= grad_rep.sum(axis=1)
```

### ALTO — Network Inference: O(N²) nested loops

| Ubicación | Problema | Impacto | Recomendación |
|-----------|----------|---------|---------------|
| `massive_core/network_inference/reconstruct.py:169-174` | `reconstruct_transfer_entropy`: nested loop O(N²) | **O(N²×T)** where T=entropy calc time; N=100 → 10K calls; N=1000 → 1M calls | Parallelize con `joblib.Parallel`; pre-compute discretized arrays; limit to top-k candidates |
| `massive_core/network_inference/reconstruct.py:200-205` | `reconstruct_granger_causality`: nested loop O(N²) | Same scaling issue; each call runs OLS regression | Vectorize lag matrices; use `np.linalg.lstsq` on batched design matrices |
| `massive_core/network_inference/reconstruct.py:227-234` | `_conditional_mutual_information`: Python `list.count` in loop | O(T³) where T=unique triples; very slow for high-entropy data | Pre-compute joint histograms with `np.histogramdd`; replace count with array lookup |

### ALTO — MultilayerEngine dense kernel

| Ubicación | Problema | Impacto | Recomendación |
|-----------|----------|---------|---------------|
| `multilayer_engine.py:362-368` | Triple nested loop in `_multilayer_langevin_step_core`: `for ell → for i → for j` | O(L×N²) per step; Numba cannot optimize due to Python list access | Replace inner `for j` with matrix multiply: `layers_flat[ell] @ x_vec[:, COL_OPINION]` (already available in sparse path) |
| `multilayer_engine.py:392-425` | Sparse path exists but is NOT used by default | Dense kernel runs even for sparse graphs (Watts-Strogatz, Barabási-Albert) | Auto-detect sparsity: if `nnz / (N*N) < 0.1`, dispatch to sparse core automatically |

**Fix propuesto (auto-sparse dispatch):**
```python
def multilayer_langevin_step(..., layers_flat, ...):
    # ... existing setup ...
    
    # Auto-detect if sparse path is beneficial
    if isinstance(layers_flat, np.ndarray) and layers_flat.ndim == 3:
        density = np.count_nonzero(layers_flat) / layers_flat.size
        if density < 0.1:  # Sparse graph — use CSR path
            layers_sparse = [sparse.csr_matrix(layers_flat[i]) for i in range(layers_flat.shape[0])]
            return _multilayer_langevin_step_core_sparse(...)
    
    # Existing dense path...
```

### MEDIO — MassiveEngine: Event-driven overhead

| Ubicación | Problema | Impacto | Recomendación |
|-----------|----------|---------|---------------|
| `massive_engine.py:917-920` | `combine_layers_csr()` + per-layer CSR conversion at init | O(M³) memory for dense + O(M³) for CSR; doubles adjacency memory | Keep only CSR; drop dense `_layers_flat` when `event_driven=True` |
| `massive_engine.py:1012` | `x_prev = self._x.copy()` every step | O(M×K) allocation per step | Use double-buffering: swap pointers instead of copying |
| `massive_engine.py:1059-1062` | Quantize → dequantize round-trip every step when `quantize=True` | Unnecessary float64↔uint8 conversion; adds ~20% overhead | Only quantize for history storage, not for computation |

### MEDIO — Simulation history memory

| Ubicación | Problema | Impacto | Recomendación |
|-----------|----------|---------|---------------|
| `multilayer_engine.py:793` | `self._history.append(self.x.copy())` every step | O(steps × N × K × 8) bytes; N=10K, steps=365 → **~1.8 GB** | Default `store_history=False`; add `max_history_points` param with downsampling |
| `multilayer_engine.py:901-907` | `trajectories_by_attribute` iterates full history | Memory + CPU double penalty | Compute on-the-fly during `run()` when attribute grouping requested |

---

## 2. Async Issues

| Código | Problema | Fix |
|--------|----------|-----|
| `multilayer_engine.py:577` | `requests.post(...)` in `_create_drift_function` path — sync HTTP in potentially async context | Wrap with `asyncio.to_thread()` or use `httpx.AsyncClient` |
| `simulator.py:1292,1316` | `requests.post(...)` for LLM calls inside simulation loop | Move LLM calls outside hot path; batch or cache responses |
| `programmatic_architect.py:204,222` | `requests.post(...)` in architect search loop | Same — batch LLM calls; add timeout + retry with exponential backoff |
| `backend/app/routers/sim.py:42` | `run_scalar_simulation()` called directly in async handler — blocks event loop | Wrap with `await asyncio.to_thread(run_scalar_simulation, ...)` |
| `backend/app/routers/engine.py:26-58` | Same issue — energy/architect routes call sync functions directly | Already uses `asyncio.to_thread` in some places; verify all paths |
| `backend/app/routers/llm.py:115` | `run_llm_simulation()` called directly in async handler | Wrap with `await asyncio.to_thread(run_llm_simulation, ...)` |

**Patrón general detectado:** Los routers async llaman a funciones síncronas sin thread-pool offloading. Esto bloquea el event loop de FastAPI, haciendo que requests concurrentes se serialicen efectivamente.

**Fix recomendado (aplicar a todos los routers):**
```python
# In backend/app/routers/sim.py
import asyncio

@router.post("", dependencies=[...])
async def v1_simulate(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    # ... validation ...
    result = await asyncio.to_thread(
        run_scalar_simulation,
        estado_inicial=payload.get("estado_inicial"),
        escenario=payload.get("escenario", "campana"),
        pasos=int(payload.get("pasos", 50)),
        config=payload.get("config"),
        verbose=bool(payload.get("verbose", False)),
    )
    return result
```

---

## 3. Memory Improvements

| Código | Problema | Fix |
|--------|----------|-----|
| `energy_engine.py:443-455` | Re-create `att_positions`, `att_strengths` arrays every `step()` call | Compute once in `__init__` or when attractors/repellers change |
| `massive_engine.py:1140` | `history_bytes = len(_opinion_history) * 8 + ...` — unbounded list growth | Cap history to last N points; use `collections.deque(maxlen=N)` |
| `multilayer_engine.py:716` | `self._history: list[np.ndarray]` — stores full (N,K) copies | Store only opinion column summaries; keep full state in MPS-compressed form |
| `forecast/engine.py:179` | `noise = rng.normal(..., size=(n_runs, steps_horizon))` — allocates (200, 365) float64 | Use `float32` for noise (sufficient precision); reduces from 584KB to 292KB |
| `massive_core/network_inference/reconstruct.py:221-224` | `list(zip(...))` creates Python tuples for entropy calc | Use `np.unique` with `return_counts=True` on flattened integer arrays |

---

## 4. Code Quality

| Módulo | Problema | Suggested |
|--------|----------|-----------|
| `simulator.py` (2457 líneas) | Función más larga del proyecto; mezcla lógica de negocio, LLM, redes, visualización | Split into: `simulator/core.py`, `simulator/llm.py`, `simulator/network.py` |
| `services/llm_orchestrator.py` (868 líneas) | `_dispatch()` tiene 10+ if/elif branches; hard to extend | Replace with strategy pattern + registry dict; add `@register_motor("energy_engine")` decorator |
| `massive_core/network_inference/reconstruct.py` | `_conditional_mutual_information` usa `list.count()` — O(n²) por triple | Replace with `np.histogramdd` + array indexing |
| `energy_engine.py` | `_ews_fallback_multiplier` recomputes flags check on every call | Cache computed multiplier; invalidate only when flags change |
| `benchmark_scalability.py` | Hardcoded population sizes; no config file support | Add YAML/TOML config for benchmark parameters |
| `cfc_engine.py`, `cfc_router.py`, `cfc_trainer.py` | Three separate files for related functionality | Consider consolidating into `cfc/` package with `__init__.py` exports |

---

## 5. Benchmark Insights (based on `docs/performance_report.md`)

### Hallazgos del benchmark existente:

| Engine | Max Tested | Throughput | Bottleneck |
|--------|-----------|------------|------------|
| EnergyEngine | 10K (incomplete) | 60K ag/s | **Numba no instalado** — fallback Python ~10× más lento |
| MultilayerEngine | 10K | 55K ag/s | O(N²) memory — OOM above 10K |
| MassiveEngine (LOD) | 100M | 68.7M ag/s | ✅ Optimizado; único engine escalable |

### Proyecciones de escala (del reporte):

| Escenario | Engine | Time | RAM | Viabilidad |
|-----------|--------|------|-----|------------|
| 8B agents (Earth) | MassiveEngine LOD | ~1.5h | 0.65 TB | ✅ Factible |
| 8B agents | EnergyEngine | ~48h | 1.3 TB | ⚠️ Requiere distributed |
| 8B agents | MultilayerEngine | ~367 días | 5,450 TB | ❌ Infeasible |

### Recomendaciones de benchmark:

1. **Instalar Numba** — El benchmark parcial muestra que EnergyEngine sería competitive con JIT
2. **Agregar benchmark de network inference** — `reconstruct_transfer_entropy` para N=100, 500, 1000
3. **Benchmark de async concurrency** — Medir throughput de API con 10, 50, 100 concurrent requests
4. **Memory profiling** — `tracemalloc` durante `run(steps=365)` con N=10K para cuantificar historial overhead

---

## 6. Prioridades de Mejora

### 🔴 Critical (Product blocker)

1. **Instalar Numba** (`pip install numba`)
   - Impacto: 10× speedup en EnergyEngine y MultilayerEngine
   - Costo: 5 minutos de install; 0 código change needed (JIT kernels already written)
   - Add to `requirements.txt` or `[project.dependencies]` in `pyproject.toml`

2. **Fix async→sync blocking en routers**
   - Impacto: Concurrent requests no más bloquean el event loop
   - Costo: ~30 minutos; wrap 5 funciones con `asyncio.to_thread`
   - Archivos: `sim.py`, `engine.py`, `llm.py`

### 🟠 High (Significant improvement)

3. **Vectorizar drift function en EnergyEngine**
   - Impacto: Elimina Python loop en scientific stepper path
   - Costo: ~2 horas de development + testing
   - Archivo: `energy_engine.py:459-467`

4. **Parallelize network inference**
   - Impacto: O(N²) → O(N²/p) donde p=workers; N=1000 pasa de minutos a segundos
   - Costo: ~4 horas; usar `joblib` o `concurrent.futures`
   - Archivos: `massive_core/network_inference/reconstruct.py`

5. **Auto-sparse dispatch en MultilayerEngine**
   - Impacto: Redes sparse (Watts-Strogatz, Barabási) corren en camino O(L·N·k) vs O(L·N²)
   - Costo: ~1 hora; detection + dispatch logic
   - Archivo: `multilayer_engine.py:428-497`

### 🟡 Medium (Quality + moderate performance)

6. **Cap simulation history memory**
   - Impacto: Reduce pico de memoria de O(steps×N×K) a O(cap×N×K)
   - Costo: ~1 hora; add `max_history` param
   - Archivos: `multilayer_engine.py`, `massive_engine.py`

7. **Optimize active set initialization**
   - Impacto: Reduce init time for large M; save 50% adjacency memory
   - Costo: ~2 horas; refactor `MassiveSimEngine.__init__`
   - Archivo: `massive_engine.py:904-920`

8. **Refactor llm_orchestrator dispatch**
   - Impacto: Más mantenible; fácil agregar nuevos motores
   - Costo: ~4 horas; strategy pattern + registry
   - Archivo: `services/llm_orchestrator.py:292-533`

### 🟢 Low (Nice to have)

9. **Float32 for forecast Monte Carlo noise**
   - Impacto: 50% memory reduction in noise buffer
   - Costo: 10 minutos
   - Archivo: `forecast/engine.py:179`

10. **Cache attractor/repeller arrays in EnergyEngine**
    - Impacto: Elimina allocations por paso
    - Costo: 30 minutos
    - Archivo: `energy_engine.py:443-455`

---

## 7. Trade-offs Considerados

| Decisión | Readability | Performance | Risk |
|----------|-------------|-------------|------|
| Numba obligatorio | ↔ | ↑↑↑ | Bajo — kernels ya escritos |
| Async→sync wrapping | ↓ (más boilerplate) | ↑↑↑ | Medio — necesita testing de concurrencia |
| Vectorizar drift | ↑ (código más limpio) | ↑↑ | Bajo — matemática identical |
| Parallel inference | ↓ (más complejidad) | ↑↑ | Medio — resultados pueden variar por orden |
| History capping | ↔ | ↑↑ | Bajo — info se pierde pero aggregates permanecen |
| Auto-sparse dispatch | ↔ | ↑↑ | Bajo — fallback a dense si detection falla |

---

## 8. Quick Wins ( < 1 hora cada uno)

| # | Cambio | Archivo | Líneas | Impacto estimado |
|---|--------|---------|--------|------------------|
| Q1 | `pip install numba` | `requirements.txt` | +1 | 10× EnergyEngine speedup |
| Q2 | Wrap `run_scalar_simulation` con `asyncio.to_thread` | `backend/app/routers/sim.py` | +3 | No more event loop blocking |
| Q3 | Float32 noise in forecast | `forecast/engine.py:179` | 1 | 50% memory reduction |
| Q4 | Cap `_opinion_history` con deque | `massive_engine.py:937` | +2 | Bounded memory growth |
| Q5 | Cache `sigma2 = _SIGMA**2` as module constant | `energy_engine.py` | 0 | Micro-optimization |

---

*Report generated by Performance Engineer agent. All line references are to the codebase as of 2025-07-24.*
