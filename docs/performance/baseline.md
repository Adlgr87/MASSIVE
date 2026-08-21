# Baseline de rendimiento — MASSIVE

> Método reproducible. Mediciones reales: **2026-08-20**, sandbox 2 vCPU / 3.8 GB RAM, Python 3.11.2, numpy.
> ⚠️ Cifras del sandbox NO comparables con las del README (31 GB RAM); sirven como referencia relativa para detectar regresiones en el mismo entorno.

## 1. Método

```bash
# Entorno
python3 -m venv .venv && source .venv/bin/activate   # o: make install
pip install -r requirements.txt

# 1) Duración y estabilidad de la suite completa
time python -m pytest tests/ -q          # (~35 s, 521 tests @ 2 vCPU)

# 2) Micro-benchmarks por motor (semilla fija, min de 3 ejecuciones)
python - <<'PY'
import time
def bench(name, fn, n=3):
    ts=[]
    for _ in range(n):
        t0=time.perf_counter(); fn(); ts.append(time.perf_counter()-t0)
    print(f"{name}: min={min(ts):.3f}s")

from services.simulation_service import run_scalar_simulation, run_multilayer_simulation, run_massive_sim
bench("scalar (50 pasos)",           lambda: run_scalar_simulation(pasos=50))
bench("multilayer (100ag, 50p)",     lambda: run_multilayer_simulation(n_agents=100, steps=50, seed=42))
bench("massive LOD (10k ag, 50p)",   lambda: run_massive_sim(n_agents=10_000, steps=50, seed=42))

from energy_runner import run_energy_simulation
bench("energy (50ag, 100p)",         lambda: run_energy_simulation(user_goal="reducir polarizacion", n_agents=50, steps=100, seed=42))

from services.llm_orchestrator import run_llm_simulation
bench("llm_orch offline (20p)",      lambda: run_llm_simulation("Simula la dinámica de opinión en una red", simulation_steps=20, seed=42))
PY

# 3) Benchmark oficial de validación PVU
PYTHONHASHSEED=42 python -m benchmarks.runner --cases datasets/pvu_cases --offline --out reports/validation/local --seed 42
```

## 2. Mediciones (2026-08-20, vía capa de servicios = camino productivo)

| Motor / flujo | Entrada | Min (3 runs) |
|---|---|---|
| `run_scalar_simulation` (legacy escalar) | 50 pasos | **0.029 s** |
| `run_multilayer_simulation` (MultilayerEngine) | 100 agentes, 50 pasos | **0.008 s** |
| `run_massive_sim` (MassiveSimEngine LOD) | 10 000 agentes, 50 pasos | **0.023 s** |
| `run_energy_simulation` (SocialEnergyEngine Langevin) | 50 agentes, 100 pasos | **0.012 s** |
| `run_llm_simulation` (pipeline completo offline, sin LLM) | 20 pasos | **0.010 s** |
| Suite completa pytest | 521 tests | **~35 s** |

Observaciones:
- El LOD de MassiveSim mantiene 10k agentes ≈ 0.023 s (compresión a super-agentes trabajando como se documenta).
- El pipeline del orquestador LLM añade ~2 ms sobre el motor subyacente cuando no hay LLM (fallback determinista).
- Import en frío de `backend.app.main`: ~4-5 s (torch/pgmpy) — solo afecta arranque, no requests.

## 3. Reglas

1. Ninguna optimización sin benchmark antes/después en el mismo entorno.
2. Cambios numéricos ⇒ comparación contra baseline con tolerancia definida (p. ej. `np.allclose(atol=1e-9)`) y seed fija.
3. Regresión >10% en suite o micro-benchmark bloquea el PR (cuando Hito 5 integre el job de CI).
4. Benchmarks oficiales de escala (1K→100M agentes) viven en README §Scalability y `benchmark_scalability.py` — requieren hardware con más RAM que este sandbox.
