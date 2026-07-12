# MASSIVE

**Mathematical Architecture for Scalable Social Interaction & Virtual Engine**

MASSIVE es una plataforma híbrida de dinámica social para simular formación de opinión,
polarización, estrategias de intervención, riesgo temporal y diagnósticos científicos
sobre sistemas sociales complejos. Combina un simulador legacy estable con capas
científicas opcionales para numérica adaptativa, análisis de estabilidad, asimilación
de datos, observables inspirados en física, ruteo neuronal CfC y flujos de validación.

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

Datos de muestra: US, China, Alemania. Dataset completo (260+ países) en
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

- **PVU-MASSIVE** (`docs/validation/`) — protocolo de validación reproducible
- **Benchmarks canónicos** (`massive_core/benchmarks/`) — fixed-point, tipping, network
- **12 casos reales** (`experiments/real_validation/`) — Chile 2019, USA 2020, Brexit,
  Brasil 2022, Hong Kong 2019, France 2018, Colombia 2021, Egypt 2011, Iran 2022,
  South Korea 2016, Germany 2014, Myanmar 2021
- **Suite pytest** (`tests/`) — 334 tests pasando

```bash
# Validación offline
python3 -m benchmarks.runner --cases datasets/real_cases --offline \
    --out reports/real_validation --seed 42
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
- Validación con casos reales: `experiments/real_validation/EMPIRICAL_VALIDATION_REPORT.md`

---

## Licencia

Apache License 2.0. Ver [`LICENSE`](./LICENSE).
