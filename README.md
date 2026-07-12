# MASSIVE

**Mathematical Architecture for Scalable Social Interaction & Virtual Engine**

MASSIVE is a hybrid social-dynamics platform for simulating opinion formation, polarization, intervention strategies, temporal risk and scientific diagnostics over complex social systems. It combines a stable legacy simulator with newer opt-in scientific layers for adaptive numerics, stability analysis, data assimilation, physics-inspired observables, CfC neural routing, optional Rust acceleration and validation workflows.

The guiding principle is backward compatibility: the classic APIs (`simular`, `simular_multiples`, `run_with_schedule`) remain stable, while advanced capabilities live behind explicit configuration flags and new `massive_core` modules.

---

## Why MASSIVE is different

- **Hybrid regime reasoning:** heuristic, LLM-compatible and optional CfC neural regime selection paths coexist with safe fallbacks.
- **Scientific opt-in layer:** adaptive steppers, stability diagnostics, EnKF assimilation, bifurcation tools, statistical mechanics, network reconstruction and scientific reports are available without changing default simulation behavior.
- **Multi-engine architecture:** legacy scalar simulation, social-energy Langevin dynamics, multilayer sociodemographic dynamics and large-scale super-agent simulation are all present.
- **Optional Rust acceleration:** selected numerical kernels can use the `massive_rust_core` extension through `massive_core.rust_core`, while keeping Python fallbacks.
- **Validation-first design:** PVU-MASSIVE offline validation, canonical scientific benchmarks and a broad pytest suite support reproducibility.
- **Typed backend/frontend contract:** Pydantic DTOs generate TypeScript interfaces through `scripts/gen_ts_types.py`.

---

## 🌍 CIA World Factbook Integration

MASSIVE now supports realistic country-specific simulations using data from the CIA World Factbook. This integration enables agents to be initialized with real demographic data, social pressure to be calculated using actual ethnic and religious diversity, and economic constraints to be based on real GDP and Gini index values.

**5 Integration Points:**
1. **Agent Initialization** - Scale agent counts and demographics from real population data
2. **Social Pressure** - Use ethnic/religious/linguistic diversity for realistic group dynamics  
3. **Energy Engine** - Gini index modulates attractor/repeller strengths in social landscapes
4. **Intervention Optimizer** - Economic constraints based on real GDP and budget data
5. **Validation Framework** - Compare simulation results against Factbook metrics

**Quick Start:**
```python
from massive.core.factbook import FactbookContext

# Load country data
context = FactbookContext()
context.load_country("US")

# Get MASSIVE parameters
params = context.get_massive_params("US")
print(f"Agents: {params['n_agents']}, Gini: {params['gini_coefficient']:.3f}")
```

The repository ships sample data for the CIA country codes `US`, `CH` (China) and `GM` (Germany) in `data/factbook/factbook_sample.json`. A full dataset (260+ countries) can be loaded from [wmccaffrey/cia_world_factbook](https://github.com/wmccaffrey/cia_world_factbook). See `FACTBOOK_INTEGRATION_COMPLETE.md` for full documentation.

---

## Repository map

| Area | Files | Purpose |
| --- | --- | --- |
| Legacy simulator | `simulator.py` | Stable public API, regime rules, LLM/heuristic selection, schedule execution. |
| Scientific adapter | `massive_core/` | Stable import surface and opt-in scientific modules. |
| Numerical integration | `massive_core/numerics/` | `DynamicsStepper`, Euler-Maruyama baseline, adaptive solver, stability tools. |
| Diagnostics | `massive_core/diagnostics/`, `massive_core/benchmarks/` | `ScientificReport`, canonical fixed-point/tipping/network benchmarks. |
| Data assimilation | `massive_core/data_assimilation/` | Ensemble Kalman Filter and sparse observation assimilation workflows. |
| Physics modules | `massive_core/physics/`, `massive_core/dynamical_systems/` | Statistical mechanics, perturbation, hydrodynamics, bifurcation analysis. |
| Meta-learning/CfC | `cfc_engine.py`, `cfc_router.py`, `cfc_trainer.py`, `massive_core/metalearning/` | Closed-form continuous-time neural models and training-data adapters. |
| Rust acceleration | `rust_core/`, `massive_core/rust_core.py` | Optional compiled kernels with Python-compatible fallbacks for selected numerical routines. |
| Energy engine | `energy_engine.py`, `energy_runner.py`, `energy_schemas.py` | Social-energy landscape dynamics and programmatic landscape generation. |
| Multilayer engine | `multilayer_engine.py`, `massive_engine.py`, `massive_core/numerics/multilayer_engine_sparse.py` | Sociodemographic multilayer simulation, sparse-engine optimisation and scalable super-agent execution. |
| Forecasting | `forecast/` | Analytical and Monte Carlo temporal forecasts and scenario comparison. |
| Strategy design | `social_architect.py`, `intervention_optimizer.py`, `programmatic_architect.py` | Inverse intervention design and optimization. |
| Validation | `benchmarks/`, `datasets/pvu_cases/`, `docs/validation/` | PVU-MASSIVE cases, metrics and validation reports. |
| **CIA World Factbook** | `massive/core/factbook/`, `data/factbook/` | Country-specific demographic, economic, social data integration for realistic simulations. |
| UI/API contract | `app.py`, `backend/app/models/`, `frontend/src/types/` | Streamlit app, DTOs and generated TypeScript types. |

---

## AI-ready repository bundle with Repomix

MASSIVE includes a Repomix configuration so any AI assistant can inspect the repository as a single, structured XML file without committing generated bundles.

```bash
npx --yes repomix@latest --config repomix.config.json
```

The command writes `repomix-output.xml` using `.gitignore`, `.repomixignore`, and `repomix-instruction.md` to keep local secrets, caches, build artifacts, binary assets and generated outputs out of the AI bundle. For a smaller structural snapshot, run:

```bash
npx --yes repomix@latest --config repomix.config.json --compress -o repomix-output-compressed.xml
```

## Installation

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Optional environment variables are documented in `.env.example`. For local Ollama runs, set `OLLAMA_HOST` if different from `http://localhost:11434`.

---

## Quick start

### Run the Streamlit app

```bash
streamlit run app.py
```

### Run the legacy simulator

```python
from simulator import simular, resumen_historial

estado = {
    "opinion": 0.5,
    "propaganda": 0.7,
    "confianza": 0.4,
    "opinion_grupo_a": 0.72,
    "opinion_grupo_b": 0.28,
    "pertenencia_grupo": 0.65,
}

historial = simular(estado, pasos=30, cada_n_pasos=5, verbose=False)
print(resumen_historial(historial))
```

### Run with scientific reporting

```python
from massive_core import run_scientific_simulation

result = run_scientific_simulation(
    estado,
    pasos=30,
    scientific_config={"enable_scientific_report": True},
    verbose=False,
)

print(result.scientific_report.to_dict())
```

### Assimilate observations with EnKF

```python
result = run_scientific_simulation(
    estado,
    pasos=30,
    scientific_config={"enable_data_assimilation": True},
    observations={30: 0.82},
    verbose=False,
)

print(result.assimilation_result.to_dict())
```

### Use opt-in steppers in engines

```python
from energy_engine import SocialEnergyEngine

engine = SocialEnergyEngine(
    range_type="bipolar",
    temperature=0.0,
    scientific_config={"solver": "euler_maruyama"},
)
```

The default is `solver="legacy"`, so existing behavior is preserved unless a scientific solver is explicitly selected.

### Run with CIA World Factbook data

```python
from massive.core.factbook import FactbookContext
from massive_engine import MassiveEngine
from energy_engine import SocialEnergyEngine

# Initialize with country-specific data
context = FactbookContext()
context.load_country("US")
params = context.get_massive_params("US")

# Create engine with real demographic data
engine = MassiveEngine(config={"n_agents": params["n_agents"]})

# Use Gini index in energy landscape
energy_engine = SocialEnergyEngine(
    gini_coefficient=params["gini_coefficient"],
    inequality_factor=params["inequality_factor"],
)
```

### Run canonical scientific benchmarks

```python
from massive_core import run_canonical_benchmarks

print(run_canonical_benchmarks())
```

### Sparse multilayer engine

A fully sparse implementation of the multilayer graph engine based on
``scipy.sparse`` structures for reduced memory and faster iteration on
large systems:

```python
import numpy as np

from massive_core.numerics import SparseMultilayerEngine, LayerState
from scipy import sparse

layer = LayerState(
    node_features=np.random.randn(100, 8),
    graph_adjacency=sparse.random(100, 100, density=0.05, format="csr"),
    layer_id="social",
)
engine = SparseMultilayerEngine(layers=[layer])
result = engine.run_simulation()
```

### Stability and perturbation analysis

``StabilityAnalyzer`` computes the Jacobian at equilibrium and classifies
local stability via eigenvalue analysis; ``PerturbationTheorySolver``
provides state perturbations and parameter-sensitivity diagnostics:

```python
from massive_core.numerics import StabilityAnalyzer
from massive_core.physics import PerturbationTheorySolver

analyzer = StabilityAnalyzer(system_fn, equilibrium)
report = analyzer.analyze()
print(report.is_stable)
```

### Sparse ensemble Kalman filter

``SparseEnsembleKalmanFilter`` runs EnKF analysis on a subset of observable
variables, ideal for high-dimensional social systems where only a fraction
of the state is measured:

```python
import numpy as np

from massive_core.data_assimilation import SparseEnsembleKalmanFilter

ekf = SparseEnsembleKalmanFilter(
    n_ensemble=50,
    n_state_dim=200,
    n_obs_dim=20,
    observable_indices=list(range(20)),
    observation_covariance=np.eye(20) * 0.1,
)
state_estimate, ensemble = ekf.assimilate_step(model_fn, observations)
```

---

## CfC neural reasoning support

MASSIVE includes Closed-form Continuous-time (CfC) components:

- `CfCRegimeSelector` for fast regime selection.
- `CfCTauMatrix` for sociodemographic noise modulation.
- `CfCArchitectPolicy` for intervention proposals.
- `massive_core.metalearning.cfc_training_data` to transform MASSIVE histories into tensors compatible with the CfC trainer.

Training remains optional and model files are loaded from `models/` by `CfCRouter` when available.

```python
from massive_core import build_cfc_regime_dataset_from_history

dataset = build_cfc_regime_dataset_from_history(historial, window_size=6)
```

---

## Mamba SSM benchmark support

MASSIVE includes a selective State Space Model (Mamba/SSM) implemented in pure PyTorch as a **complementary baseline** to the existing CfC layer:

- `MambaCell` — one-step selective SSM cell with input-dependent discretisation step Δ.
- `MambaSSM` — multi-layer recurrent SSM over arbitrary-length sequences.
- `MambaBaseline` — drop-in PVU-BS baseline following the same `predict(train, horizon)` interface as `AR1Baseline`, `ETSBaseline`, etc.

The Mamba baseline is evaluated automatically under the Diebold-Mariano + Holm-Bonferroni protocol when `enable_mamba=True` in `ScientificRuntimeConfig` or when `torch` is available and `get_all_baselines()` is called.

> **Note on series length:** The architectural advantage of SSM (selective context compression) is most visible on long multivariate sequences. On the short univariate social series typical of PVU cases, Mamba may not outperform AR(1)/ETS with statistical significance — the Holm-Bonferroni test will reflect this honestly. For a fairer comparison, consider cross-episode pretraining across all PVU cases.

```python
from mamba_engine import MambaBaseline
import numpy as np

baseline = MambaBaseline(d_model=8, d_state=16, lags=4, epochs=50)
forecast = baseline.predict(train_series, horizon=10)
```

**Key difference from CfC:** Mamba does not participate in regime selection or social architect proposals — those remain CfC's responsibility. Mamba operates exclusively as a time-series forecasting baseline in the benchmark layer.

---

## Validation and checks

```bash
# Unit/integration suite
python -m pytest tests/

# PVU-MASSIVE offline validation
python -m benchmarks.runner --cases datasets/pvu_cases --offline --out reports/validation/local --seed 42

# Regenerate frontend TypeScript contracts
python scripts/gen_ts_types.py

# Build documentation
python -m mkdocs build --strict
```

---

## Documentation

- MkDocs site: `docs/`
- API reference: `docs/api.md`
- Scientific roadmap in Spanish: `docs/math_physics_extension_plan_ES.md`
- PVU-MASSIVE validation protocol: `docs/validation/`
- Spanish overview: `README_ES.md`
- Benchmark card: docs/cards/BENCHMARK.md
- Reproducibility card: docs/cards/REPRODUCIBILITY.md
- Real-engine benchmark report: `experiments/06_real_benchmark_v0/REPORT.md`
- Historical empirical validation report: `experiments/real_validation/EMPIRICAL_VALIDATION_REPORT.md`

---

## Project history

MASSIVE was previously developed under the name `BeyondSight` (visible in older git
history). The codebase was renamed to `MASSIVE` in 2026-06-29 to better reflect
the multi-engine architecture (`Multilayer + Architecture for Scalable Social
Interaction & Virtual Engine`). All current source uses the `massive*` namespace;
the rename is preserved in git history for traceability.

---

## Deployment notes

- CI deploy no longer uses force-push to Hugging Face Spaces.
- Configure `HF_TOKEN` in repository secrets for Hugging Face sync.
- Optional analytics in the Streamlit app can be injected with `MASSIVE_ANALYTICS_SNIPPET`; no placeholder script is emitted by default.

---

## License

Apache License 2.0. See `LICENSE`.
