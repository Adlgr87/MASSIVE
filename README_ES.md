# MASSIVE

**Mathematical Architecture for Scalable Social Interaction & Virtual Engine**

MASSIVE es una plataforma híbrida de dinámica social para simular formación de opinión,
polarización, estrategias de intervención, riesgo temporal y diagnósticos científicos
sobre sistemas sociales complejos. Combina un simulador legacy estable con capas
científicas opcionales para numérica adaptativa, análisis de estabilidad, asimilación
de datos, observables inspirados en física, ruteo neuronal CfC, aceleración opcional
en Rust y flujos de validación.

El principio rector es **compatibilidad hacia atrás**: las APIs clásicas
(`simular`, `simular_multiples`, `run_with_schedule`) se mantienen estables, mientras
las capacidades avanzadas viven detrás de flags de configuración explícitos y nuevos
módulos `massive_core`.

> Documento principal en inglés: [`README.md`](./README.md).
> Esta versión es un resumen para usuarios hispanohablantes.

---

## Características clave

- **Razonamiento de régimen híbrido:** rutas heurísticas, LLM-compatibles y CfC
  neuronal coexisten con fallbacks seguros.
- **Capa científica opt-in:** steppers adaptativos, diagnósticos de estabilidad,
  asimilación EnKF, herramientas de bifurcación, mecánica estadística, reconstrucción
  de red y reportes científicos, sin alterar el comportamiento por defecto.
- **Arquitectura multi-motor:** simulación escalar legacy, dinámica Langevin de
  energía social, dinámica multicapa sociodemográfica y simulación masiva con
  super-agentes.
- **Aceleración opcional en Rust:** algunos kernels numéricos usan `massive_rust_core`
  vía `massive_core.rust_core`, manteniendo fallbacks en Python.
- **Diseño validation-first:** validación offline PVU-MASSIVE, benchmarks científicos
  canónicos y una suite pytest amplia para reproducibilidad.
- **Contrato tipado backend/frontend:** los DTOs de Pydantic generan interfaces
  TypeScript vía `scripts/gen_ts_types.py`.

---

## 🌍 Integración con CIA World Factbook

MASSIVE soporta simulaciones realistas con datos del CIA World Factbook: inicialización
de agentes con datos demográficos reales, presión social con diversidad étnica y
religiosa, y restricciones económicas basadas en PIB e índice de Gini.

**5 puntos de integración:**

1. **Inicialización de agentes** — escala de población real
2. **Presión social** — diversidad étnica/religiosa/lingüística
3. **Motor de energía** — Gini modula atractores/repulsores
4. **Optimizador de intervención** — PIB y presupuesto real
5. **Validación** — comparación con métricas del Factbook

```python
from massive.core.factbook import FactbookContext

context = FactbookContext()
context.load_country("US")
params = context.get_massive_params("US")
print(f"Agentes: {params['n_agents']}, Gini: {params['gini_coefficient']:.3f}")
```

El repositorio incluye datos de muestra para los códigos CIA `US`, `CH` (China)
y `GM` (Alemania) en `data/factbook/factbook_sample.json`. Dataset completo (260+ países) en
[wmccaffrey/cia_world_factbook](https://github.com/wmccaffrey/cia_world_factbook).

---

## Instalación

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Variables de entorno opcionales en `.env.example`. Para Ollama local, configura
`OLLAMA_HOST` si difiere de `http://localhost:11434`.

---

## Inicio rápido

### App Streamlit

```bash
streamlit run app.py
```

### Simulador legacy

```python
from simulator import simular, resumen_historial

estado = {
    "opinion": 0.5, "propaganda": 0.7, "confianza": 0.4,
    "opinion_grupo_a": 0.72, "opinion_grupo_b": 0.28,
    "pertenencia_grupo": 0.65,
}

historial = simular(estado, pasos=30, cada_n_pasos=5, verbose=False)
print(resumen_historial(historial))
```

### Simulación con reporte científico

```python
from massive_core import run_scientific_simulation

result = run_scientific_simulation(
    estado, pasos=30,
    scientific_config={"enable_scientific_report": True},
    verbose=False,
)
print(result.scientific_report.to_dict())
```

### Asimilar observaciones con EnKF

```python
result = run_scientific_simulation(
    estado, pasos=30,
    scientific_config={"enable_data_assimilation": True},
    observations={30: 0.82}, verbose=False,
)
print(result.assimilation_result.to_dict())
```

---

## Validación

- **Suite pytest** (`tests/`) — actualmente validada en este repositorio con
  `351 passed, 2 skipped`
- **PVU-MASSIVE** (`docs/validation/`) — protocolo de validación reproducible
- **Benchmarks canónicos** (`massive_core/benchmarks/`) — fixed-point, tipping, network
- **Benchmark con motor real** (`experiments/06_real_benchmark_v0/REPORT.md`) —
  evaluación de 12 casos sociales documentados contra baseline naive
- **Reporte empírico histórico** (`experiments/real_validation/EMPIRICAL_VALIDATION_REPORT.md`) —
  benchmark previo basado en el proxy offline

```bash
# Suite principal
python -m pytest tests/

# Validación offline PVU-MASSIVE
python -m benchmarks.runner --cases datasets/pvu_cases --offline \
    --out reports/validation/local --seed 42
```

---

## Mamba SSM — baseline de pronóstico (complementario a CfC)

MASSIVE incluye un modelo SSM selectivo (inspirado en Mamba) implementado en PyTorch puro como **baseline complementario** a la capa CfC:

- `MambaCell` — celda SSM selectiva con paso de discretización Δ dependiente de la entrada.
- `MambaSSM` — red SSM multicapa sobre secuencias de longitud arbitraria.
- `MambaBaseline` — baseline plug-in para PVU-BS con la misma interfaz `predict(train, horizon)` que `AR1Baseline`, `ETSBaseline`, etc.

**Rol diferenciado vs CfC:** Mamba no participa en la selección de régimen ni en las propuestas del Arquitecto Social — esas funciones las cubre CfC. Mamba opera exclusivamente como baseline de pronóstico de series temporales en la capa de benchmarks.

```python
from mamba_engine import MambaBaseline
import numpy as np

baseline = MambaBaseline(d_model=8, d_state=16, lags=4, epochs=50)
forecast = baseline.predict(train_series, horizon=10)
```

> **Nota:** En series cortas univariadas (típicas de los casos PVU), la ventaja de SSM sobre AR(1)/ETS puede ser marginal. El test Holm-Bonferroni lo reflejará objetivamente.

---

## Mapa del repositorio

| Área | Archivos | Propósito |
| --- | --- | --- |
| Simulador legacy | `simulator.py` | API pública estable, reglas, selector LLM, schedule. |
| Adaptador científico | `massive_core/` | Imports estables + módulos opt-in. |
| Integración numérica | `massive_core/numerics/` | Stepper, Euler-Maruyama, adaptativo. |
| Diagnósticos | `massive_core/diagnostics/`, `massive_core/benchmarks/` | Reportes y benchmarks. |
| Asimilación de datos | `massive_core/data_assimilation/` | EnKF, observaciones dispersas. |
| Módulos físicos | `massive_core/physics/`, `massive_core/dynamical_systems/` | Mecánica estadística, perturbación, bifurcación. |
| CfC / meta-learning | `cfc_engine.py`, `cfc_router.py`, `cfc_trainer.py` | Modelos neuronales de tiempo continuo. |
| Mamba SSM | `mamba_engine.py` | Baseline SSM selectivo puro PyTorch para benchmarks. |
| Aceleración Rust | `rust_core/`, `massive_core/rust_core.py` | Kernels compilados opcionales con fallback compatible en Python. |
| Motor de energía | `energy_engine.py`, `energy_runner.py` | Paisajes de energía social. |
| Motor multicapa | `multilayer_engine.py`, `massive_engine.py` | Dinámica sociodemográfica y masiva. |
| Forecasting | `forecast/` | Pronósticos analíticos y Monte Carlo. |
| Diseño de estrategias | `social_architect.py`, `intervention_optimizer.py` | Diseño inverso de intervención. |
| **Factbook** | `massive/core/factbook/`, `data/factbook/` | Datos CIA por país. |
| UI/API | `app.py`, `backend/`, `frontend/` | Streamlit, DTOs, TypeScript. |

---

## Documentación

- Versión completa en inglés: [`README.md`](./README.md)
- Plan de extensión científica: `docs/math_physics_extension_plan_ES.md`
- Protocolo PVU-MASSIVE: `docs/validation/`
- Reporte de benchmark: `experiments/MASSIVE_BENCHMARK_REPORT.md`
- Benchmark con motor real: `experiments/06_real_benchmark_v0/REPORT.md`
- Validación empírica histórica: `experiments/real_validation/EMPIRICAL_VALIDATION_REPORT.md`

---

## Licencia

Apache License 2.0. Ver [`LICENSE`](./LICENSE).
