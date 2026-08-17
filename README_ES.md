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

## El océano no está en una sola molécula de agua

MASSIVE no simula individuos: modela el **comportamiento emergente de millones de personas en interacción**. Al igual que el océano no reside en una molécula de agua sino en el conjunto, los fenómenos que MASSIVE captura solo existen a escala masiva.

Criticar que "los humanos son impredecibles" es irrelevante: MASSIVE modela fenómenos *colectivos* —oleadas de opinión, polarización, cambios de fase— que carecen de significado a nivel individual. La meteorología no predice moléculas de aire; mapea campos de presión y temperatura. MASSIVE hace lo mismo con las sociedades: identifica **patrones y puntos de bifurcación** que solo emergen cuando millones de decisiones convergen.

La base teórica es la **ontología de niveles**: los fenómenos sociales son irreducibles a la suma de decisiones individuales. MASSIVE no es un oráculo ni modela conciencias. Es una herramienta para:

- **Explorar escenarios** antes de que se cristalicen en realidad.
- **Probar intervenciones** en un sandbox seguro y cuantitativo.
- **Detectar señales tempranas** de inestabilidad y puntos de quiebre.

Se sitúa en la intersección de la física de sistemas complejos y las ciencias sociales cuantitativas —la misma tradición intelectual que dio origen a la termodinámica, los modelos epidemiológicos y la mecánica estadística aplicada al comportamiento colectivo humano.

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

## Instalación

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Variables de entorno opcionales en `.env.example`. Para Ollama local, configura
`OLLAMA_HOST` si difiere de `http://localhost:11434`.

## Inicio rápido

### UI-NG frontend + API (servicio único)

```bash
# 1. Instalar dependencias backend
pip install -r requirements.txt

# 2. Compilar el frontend UI-NG (una vez) — genera frontend/dist
cd frontend && npm ci && npm run build && cd ..

# 3. Servir todo (API en :8000, frontend en /)
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Abre `http://localhost:8000` para la app UI-NG. La documentación OpenAPI está en `/docs`.

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
| Aceleración Rust | `rust_core/`, `massive_core/rust_core.py` | Kernels compilados opcionales con fallback compatible en Python. |
| Motor de energía | `energy_engine.py`, `energy_runner.py` | Paisajes de energía social. |
| Motor multicapa | `multilayer_engine.py`, `massive_engine.py` | Dinámica sociodemográfica y masiva. |
| Forecasting | `forecast/` | Pronósticos analíticos y Monte Carlo. |
| Diseño de estrategias | `social_architect.py`, `intervention_optimizer.py` | Diseño inverso de intervención. |
| **Factbook** | `massive/core/factbook/`, `data/factbook/` | Datos CIA por país. |
| UI/API | `backend/`, `frontend/` | FastAPI backend, DTOs Pydantic, interfaces TypeScript. |

---

## Documentación

- Versión completa en inglés: [`README.md`](./README.md)
- Plan de extensión científica: `docs/math_physics_extension_plan_ES.md`
- Protocolo PVU-MASSIVE: `docs/validation/`
- Reporte de benchmark: `experiments/MASSIVE_BENCHMARK_REPORT.md`
- Benchmark con motor real: `experiments/06_real_benchmark_v0/REPORT.md`
- Validación empírica histórica: `experiments/real_validation/EMPIRICAL_VALIDATION_REPORT.md`

## Licencia

Apache License 2.0. Ver [`LICENSE`](./LICENSE).
