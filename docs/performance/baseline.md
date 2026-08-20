# Baseline de rendimiento — MASSIVE

> Método reproducible. Fecha: 2026-08-20. Entorno de referencia inicial: sandbox 2 vCPU / 3.8 GB RAM / Python 3.11.2.
> ⚠️ Las cifras del sandbox NO son comparables con las del README (31 GB RAM); sirven como referencia relativa para detectar regresiones en el mismo entorno.

## 1. Método

```bash
# Entorno
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# Baseline de suite (duración y estabilidad)
time python -m pytest tests/ -q

# Micro-benchmarks por motor (semilla fija)
PYTHONHASHSEED=42 python - <<'PY'
import time, numpy as np
from multilayer_engine import MultilayerEngine
from energy_engine import SocialEnergyEngine
from massive_engine import MassiveSimEngine

def bench(name, fn, n=3):
    ts = []
    for _ in range(n):
        t0 = time.perf_counter(); fn(); ts.append(time.perf_counter() - t0)
    print(f"{name}: min={min(ts):.3f}s mediana={sorted(ts)[len(ts)//2]:.3f}s")

bench("MultilayerEngine(100 agentes, 50 pasos)", lambda: MultilayerEngine(n_agents=100, n_steps=50).run())
PY
```

> Nota: los motores exponen constructores/APIs distintos; el snippet se adapta por motor.
> Los benchmarks oficiales del repo: `python -m benchmarks.runner --cases datasets/pvu_cases --offline --out reports/validation/local --seed 42`.

## 2. Mediciones de referencia (sandbox, 2026-08-20)

| Métrica | Valor | Comando |
|---|---|---|
| Suite completa de tests | ~38 s (483 tests, 2 vCPU) | `time pytest tests/ -q` |
| Import de `backend.app.main` (arranque en frío) | ~4-5 s (carga torch/pgmpy) | introspección |
| PVU offline validation | pendiente de medir en este entorno | `benchmarks.runner` |
| Benchmarks por motor | pendiente (Hito 5) | ver método |

## 3. Reglas

1. Ninguna optimización sin benchmark antes/después en el mismo entorno.
2. Cambios numéricos ⇒ comparación contra baseline con tolerancia definida (p. ej. `np.allclose(atol=1e-9)`) y seed fija.
3. Regresiones >10% en la suite o en un micro-benchmark bloquean el PR (una vez CI los ejecute).
