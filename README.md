# MASSIVE

**Mathematical Architecture for Scalable Social Interaction & Virtual Engine**

MASSIVE is a hybrid social-dynamics platform for simulating opinion formation, polarization, intervention strategies, temporal risk and scientific diagnostics over complex social systems. It combines a stable legacy simulator with newer opt-in scientific layers for adaptive numerics, stability analysis, data assimilation, physics-inspired observables, CfC neural routing and validation workflows.

The guiding principle is backward compatibility: the classic APIs (`simular`, `simular_multiples`, `run_with_schedule`) remain stable, while advanced capabilities live behind explicit configuration flags and new `massive_core` modules.

---

## Why MASSIVE is different

- **Hybrid regime reasoning:** heuristic, LLM-compatible and optional CfC neural regime selection paths coexist with safe fallbacks.
- **Scientific opt-in layer:** adaptive steppers, stability diagnostics, EnKF assimilation, bifurcation tools, statistical mechanics, network reconstruction and scientific reports are available without changing default simulation behavior.
- **Multi-engine architecture:** legacy scalar simulation, social-energy Langevin dynamics, multilayer sociodemographic dynamics and large-scale super-agent simulation are all present.
- **Validation-first design:** PVU-BeyondSight offline validation, canonical scientific benchmarks and a broad pytest suite support reproducibility.
- **Typed backend/frontend contract:** Pydantic DTOs generate TypeScript interfaces through `scripts/gen_ts_types.py`.

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
| Energy engine | `energy_engine.py`, `energy_runner.py`, `energy_schemas.py` | Social-energy landscape dynamics and programmatic landscape generation. |
| Multilayer engine | `multilayer_engine.py`, `massive_engine.py` | Sociodemographic multilayer simulation and scalable super-agent execution. |
| Forecasting | `forecast/` | Analytical and Monte Carlo temporal forecasts and scenario comparison. |
| Strategy design | `social_architect.py`, `intervention_optimizer.py`, `programmatic_architect.py` | Inverse intervention design and optimization. |
| Validation | `benchmarks/`, `datasets/pvu_cases/`, `docs/validation/` | PVU-BeyondSight cases, metrics and validation reports. |
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

### Run canonical scientific benchmarks

```python
from massive_core import run_canonical_benchmarks

print(run_canonical_benchmarks())
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

## Validation and checks

```bash
# Unit/integration suite
python -m pytest tests/

# PVU-BeyondSight offline validation
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
- PVU-BeyondSight validation protocol: `docs/validation/`
- Spanish overview: `README_ES.md`

---

## Deployment notes

- CI deploy no longer uses force-push to Hugging Face Spaces.
- Configure `HF_TOKEN` in repository secrets for Hugging Face sync.
- Optional analytics in the Streamlit app can be injected with `MASSIVE_ANALYTICS_SNIPPET`; no placeholder script is emitted by default.

---

## License

Apache License 2.0. See `LICENSE`.
