# MASSIVE

MASSIVE es un simulador híbrido de dinámica social que combina motor matemático, selección de régimen por LLM/CfC y herramientas de arquitectura social para diseñar intervenciones.

## Estado funcional actual

### 1) Núcleo clásico (`simulator.py`)
- API estable y retrocompatible: `simular`, `simular_multiples`, `run_with_schedule`.
- Reglas de dinámica social (lineal, umbral, memoria, backlash, polarización, HK, contagio competitivo, umbral heterogéneo, homofilia, replicador, etc.).
- Selección de reglas por heurística, LLM o **Router CfC** cuando hay modelos entrenados.
- Integración de calibración empírica, métricas EWS y detección topológica.

### 2) Nuevo núcleo adaptativo (`IntegratedSimulator`)
Integrado dentro del flujo principal, con activación por configuración:
- **Saltos de Lévy** (`enable_levy_jumps`): perturbaciones endógenas de cola pesada.
- **Topología dinámica** (`enable_dynamic_topology`): recableado contextual de capas sociales.
- **Diagnóstico mariposa/Lyapunov** (`butterfly_interval`, `butterfly_threshold`): monitoreo continuo de divergencia y alertas.
- **Comunicación contextual** vía hooks opcionales:
  - `router_feedback_hook`
  - `social_architect_hook`

### 3) Shock exógeno manual (Cisne Negro)
- Se mantiene **manual** por diseño en `MassiveEngine.apply_shock(...)`.
- No corre automáticamente en el loop principal.
- Soporta distribuciones `uniform`, `normal`, `pareto` y fracción de agentes afectados.

### 4) Motor multicapa (`multilayer_engine.py`)
- `MultilayerEngine` para redes social/digital/económica con dinámica de Langevin multicapa.
- Nuevo `dynamic_rewiring(layer_name, mode, intensity)` para evolución topológica en runtime.
- Alias de compatibilidad: `MultiLayerEngine`.

### 5) Motor masivo (`massive_engine.py`)
- `MassiveSimEngine` para simulación eficiente con:
  - super-agentes (LOD),
  - cuantización uint8,
  - modo event-driven,
  - aceleración GPU opcional.
- `MassiveEngine` para estado completo de agentes + shock manual exógeno.

## Configuración relevante (nuevo simulador integrado)

Parámetros en `DEFAULT_CONFIG` / config runtime:
- `n_agents`, `n_ticks`, `dt`, `diffusion_sigma`
- `enable_levy_jumps`, `levy_lambda`, `alpha_stable`, `jump_magnitude_scale`
- `enable_dynamic_topology`, `topology_update_freq`, `topology_intensity`
- `butterfly_interval`, `butterfly_threshold`

## Uso rápido

### Instalar
```bash
pip install -r requirements.txt
```

### Ejecutar app
```bash
streamlit run app.py
```

### Ejecutar tests
```bash
pytest tests/
```

## Ejemplo mínimo: simulador integrado

```python
from simulator import IntegratedSimulator

sim = IntegratedSimulator({
    "n_agents": 500,
    "n_ticks": 200,
    "enable_levy_jumps": True,
    "enable_dynamic_topology": True,
    "topology_update_freq": 10,
    "butterfly_interval": 25,
})

history = sim.run()
```

## Ejemplo mínimo: Cisne Negro manual

```python
from massive_engine import MassiveEngine

engine = MassiveEngine({"n_agents": 1000, "seed": 42})
engine.apply_shock(
    magnitude=0.3,
    distribution="pareto",
    target_layer=0,
    affected_fraction=0.1,
)
```
