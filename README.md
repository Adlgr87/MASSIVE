---
title: MASSIVE
emoji: 🌊
colorFrom: blue
colorTo: indigo
sdk: streamlit
app_file: app.py
pinned: false
---

# MASSIVE
### Mathematical Architecture for Scalable Social Interaction & Virtual Engine

> *"Many behaving as One"*

<p align="center">
  <img src="https://github.com/user-attachments/assets/04c5860f-36d4-433c-a142-5761d0f16824" alt="MASSIVE Social Simulator" width="260"/>
</p>

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![tests](https://github.com/Adlgr87/MASSIVE/actions/workflows/pytest.yml/badge.svg)](https://github.com/Adlgr87/MASSIVE/actions/workflows/pytest.yml)
[![docs](https://github.com/Adlgr87/MASSIVE/actions/workflows/mkdocs.yml/badge.svg)](https://github.com/Adlgr87/MASSIVE/actions/workflows/mkdocs.yml)
[![PVU Validation](https://github.com/Adlgr87/MASSIVE/actions/workflows/pvu-validation.yml/badge.svg)](https://github.com/Adlgr87/MASSIVE/actions/workflows/pvu-validation.yml)

![MASSIVE UI Demo](docs/massive_ui_mockup.png)


MASSIVE is a hybrid social dynamics simulator that combines a rigorous mathematical core with the contextual reasoning of Large Language Models. It models how opinions, behaviors, and social structures form and evolve — from small groups to populations of millions.

Traditional simulators ask *"what will happen?"*. MASSIVE also answers: **"what sequence of interventions gets us where we want to go?"** — via the reverse-engineering Social Architect agent.

---

## Contents

- [What it does](#what-it-does)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Simulation Rules](#simulation-rules)
- [Installation](#installation)
- [Running the App](#running-the-app)
- [Programmatic API](#programmatic-api)
- [Configuration](#configuration)
- [Performance at Scale](#performance-at-scale)
- [Social Media Integration](#social-media-integration)
- [Validation Protocol (PVU-BS)](#validation-protocol-pvu-bs)
- [Design Decisions](#design-decisions)
- [Limitations](#limitations)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

---

## What it does

MASSIVE lets you:

1. **Run forward simulations** — pick one of 13 mathematical rules, configure opinion, propaganda, trust, and group composition, and watch a social network evolve step by step with live charts and early warning signals.
2. **Reverse-engineer outcomes** — describe a desired social state in plain language; the Social Architect uses an LLM in an iterative propose-simulate-score-refine loop to find the intervention sequence that gets you there.
3. **Model structural complexity** — each agent carries a 5-dimensional state vector `(opinion, cooperation, hierarchy, income, info_access)` across three superimposed network layers (social, digital, economic), modulated by demographic attributes.
4. **Scale to millions** — population-scale simulation on a laptop, combining super-agent clustering, uint8 quantization, event-driven updates, and optional GPU offloading.
5. **Seed from real data** — fetch live sentiment from Twitter/X or Reddit to initialize simulations from actual public opinion distributions.

---

## Key Features

### Simulation Core
- **13 simulation rules** rooted in peer-reviewed opinion dynamics literature (DeGroot, Friedkin-Johnsen, Hegselmann-Krause, Granovetter, Axelrod, Nash, Pearl, Kermack-McKendrick, and more).
- **LLM as regime selector** — instead of hard-coding which model runs when, the LLM reads the current network state and selects the most sociologically coherent rule at each step.
- **Two opinion ranges** — probabilistic `[0, 1]` (neutral = 0.5) and bipolar `[-1, 1]` (neutral = 0.0), selectable per run. All values are clipped to range after every update.
- **Three cross-cutting mechanisms** applied on top of every rule: Confirmation Bias, Dynamic Homophily, and a Game-Theoretic Strategic Force.

### Social Architect
- Iterative LLM agent that **reverse-engineers intervention sequences** to reach a user-defined social outcome.
- Closed feedback loop: LLM proposes a `StrategyMatrix` → Langevin simulation executes it → score computed (0–100) → LLM refines until score ≥ 90 or attempts exhausted.
- Two operational modes: **Macro** (public opinion, elections, social movements) and **Corporate** (organizational change, team alignment, informal leadership).
- Outputs a structured schedule with sociological rationale + a consultant-quality narrative in plain language.

### Multilayer Sociodemographic Engine
- Each agent is a **5D state vector** `(opinion, cooperation, hierarchy, income, info_access)` evolving simultaneously.
- **Three superimposed network layers**: Watts-Strogatz (social), Barabási-Albert (digital), hierarchical star+hubs (economic).
- **Demographic modulation (θ-matrix)**: religion, education, age, and gender adjust each agent's noise sensitivity per behavioral dimension, producing realistic heterogeneity without per-agent hand-tuning.
- **Multidimensional social potential** with independent but coupled gradients: double-well polarization (opinion), cooperation clustering, hierarchy bifurcation, income centering, and info-access decay.

### Energy Landscape Engine
- **Langevin stochastic dynamics** on a configurable landscape of Gaussian attractors and repellers.
- **Numba JIT-compiled** inner loop (`@njit`) — compiled once, runs at native speed for all subsequent calls.
- **8 pre-built social archetypes** (`polarizacion_extrema`, `consenso_moderado`, `radicalizacion_progresiva`, …) for instant scenario setup.
- **Resolution pipeline** for free-text goals: exact archetype match → RAM cache → SQLite cache (persists across restarts) → LLM one-shot → fallback.

### Massive Scale Engine
- **Sociological LOD (super-agents)**: N agents collapse to M clusters; matrix size drops from O(N²) to O(M²).
- **uint8 state quantization**: 87.5% RAM reduction per parameter with resolution ≈ 0.008 per opinion unit.
- **Event-driven active sets**: sleeping agents (in stable consensus) consume zero CPU until a neighbor change wakes them.
- **GPU offloading**: CuPy → PyTorch+CUDA → NumPy, selected automatically at startup — no configuration required.

### Analytics & Monitoring
- **Early Warning Signals (EWS)**: sliding-window variance, lag-1 autocorrelation, and skewness — flags ⚠️ proximity to social tipping points.
- **Topological Data Analysis (TDA)**: optional persistent homology via Takens delay-embedding + Vietoris-Rips filtration (`ripser` + `persim`), detecting structural regime changes that scalar metrics miss.
- **Network graph metrics**: degree/betweenness centrality, density, and cluster identification via NetworkX.

### Integration & Infrastructure
- **LangChain typed chains** (`strategy_chain`, `narrative_chain`, `landscape_chain`) with JSON output validation and transparent HTTP fallback.
- **Dask parallel multi-simulation** across all available CPU cores via `dask.delayed`.
- **Quantum module**: QAOA-inspired intervention optimizer (Qiskit or classical fallback) + MPS tensor-network compression for agent-state matrices.
- **43-parameter empirical calibration base**, cross-validated from 40+ peer-reviewed sources, with cultural variance per block and explicit `pending_empirical_data` flags.
- **PVU-BS formal validation protocol** with Diebold-Mariano significance tests and Holm-Bonferroni correction.
- **Bilingual Streamlit UI** (English / Spanish) with runtime language toggle.
- **Social media connectors**: Twitter/X (v2 Recent Search API) and Reddit (praw) for live sentiment seeding.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Streamlit UI  (app.py)                     │
│  Tab 1: Simulation │ Tab 2: Architect │ Tab 3: Multilayer │ Tab 4: Massive │
└─────┬───────────────────┬──────────────────┬────────────────-┘
      │                   │                  │
┌─────▼──────┐  ┌─────────▼────────┐  ┌──────▼──────────────┐
│ simulator  │  │ social_architect  │  │ multilayer_engine    │
│ (13 rules) │  │ (LLM loop +       │  │ (5D × 3 layers +    │
│ EWS / TDA  │  │  StrategyMatrix)  │  │  θ-matrix + Numba)  │
└─────┬──────┘  └─────────┬────────┘  └──────┬──────────────-┘
      │                   │                  │
      └──────────┬─────────┘                  │
                 ▼                            │
    ┌────────────────────────────────────────-┘
    │   energy_engine (Langevin / Numba JIT)
    │   massive_engine (LOD / uint8 / event-driven / GPU)
    └───────────────────────────────────────────────────
                 │
    ┌────────────▼────────────────────────────────────┐
    │  LLM providers (via llm_credentials.py):         │
    │  heuristic │ Ollama │ Groq │ OpenAI │ OpenRouter │
    │  (optional LangChain chains in langchain_workflows.py) │
    └──────────────────────────────────────────────────┘
```

### The Langevin equation at each step

```
x(t + Δt) = f(x(t), r(t)) · α  +  b(x(t)) · (1 − α)  +  G(x(t))  +  η(t)
```

| Term | Meaning |
|------|---------|
| `f(x(t), r(t))` | Output of the active dynamical rule `r` (HK, threshold, replicator, …) |
| `α` | Blend weight between LLM-selected model and base tendency (default 0.80) |
| `b(x(t))` | Base tendency: `0.92 · opinion + 0.08 · propaganda` |
| `G(x(t))` | Group polarization: weighted cluster A/B influence |
| `η(t) ~ 𝒩(0, σ²)` | Stochastic Wiener increment |

Noise adapts to institutional trust: `σ(t) = σ_base + σ_distrust · (1 − trust(t))`. As trust erodes, the diffusion coefficient grows — making the system harder to steer and producing wider opinion swings.

### Social Architect loop

```
User goal (free text) + initial network state
        │
        ▼
LLM proposes StrategyMatrix (JSON schedule of interventions)
        │
        ▼
run_with_schedule() → Langevin engine executes each phase
        │
        ▼
evaluar_resultado() → score 0–100 (polarization, opinion delta, variance)
        │
   Score ≥ 90? ──YES──► generar_narrativa_final() ──► Done
        │
       NO
        │
inject feedback into LLM context → repeat (up to max_attempts)
```

### Multilayer equation

```
dx_i/dt = −∇U(x_i) + Σ_ℓ w_ℓ · (A_ℓ · G(x))_i + θ(a_i) · η_i
```

Three differentiated network layers run simultaneously:

| Layer | Topology | Phenomenon captured |
|-------|----------|---------------------|
| Social | Watts-Strogatz (small-world) | Face-to-face contacts, local community |
| Digital | Barabási-Albert (scale-free) | Social media, echo chambers, viral content |
| Economic | Hierarchical (star + hubs) | Authority flow, wages, organizational power |

Demographic attributes modulate noise sensitivity per behavioral dimension (calibrated from social-psychology literature):

```python
theta[i, opinion]     *= 1 + 0.5 * religion_i    # Altemeyer (1988)
theta[i, cooperation] *= 1 + 0.3 * education_i   # Putnam (2000)
theta[i, hierarchy]   *= 1 + 0.4 * (age_i / 2)  # Alwin & Krosnick (1991)
theta[i, income]      *= 1 + 0.2 * youth_i       # labor-market volatility
theta[i, info_access] *= 1 + 0.4 * education_i   # van Dijk (2005)
```

---

## Simulation Rules

| # | Rule | Theoretical basis |
|---|------|-------------------|
| 0 | `lineal` | Proportional smooth change |
| 1 | `umbral` | Threshold jump at critical point |
| 2 | `memoria` | Past-state inertia |
| 3 | `backlash` | Propaganda reinforces opposing position |
| 4 | `polarizacion` | Echo-chamber attractor |
| 5 | `hk` | Hegselmann-Krause (2002) bounded confidence |
| 6 | `contagio_competitivo` | Two narratives competing simultaneously — Beutel et al. (2012) |
| 7 | `umbral_heterogeneo` | Granovetter (1978) threshold distribution — social cascades |
| 8 | `homofilia` | Co-evolutionary network weights — Axelrod (1997) |
| 9 | `replicador` | Replicator ODE integrated with RK45 — Taylor & Jonker (1978) |
| 10 | `nash` | Nash equilibrium coordination game (1950) — via `nashpy` |
| 11 | `bayesiano` | Bayesian opinion network — Pearl (1988), built with `pgmpy` |
| 12 | `sir` | SIR epidemiological contagion — Kermack & McKendrick (1927) |

**Cross-cutting mechanisms** (applied on top of every rule at every step):
- **Confirmation Bias** (Sunstein 2009, Nickerson 1998) — incoming counter-information is attenuated proportionally to the agent's current position.
- **Dynamic Homophily** (Axelrod 1997, Flache et al. 2017) — group influence weights update each step based on opinion similarity.
- **Strategic Game-Theory Force** (`utility_logic.py`) — payoff-based bias toward cooperation or defection based on neighbors' average position.

---

## Installation

**Requirements:** Python 3.9+

```bash
git clone https://github.com/Adlgr87/MASSIVE.git
cd MASSIVE
pip install -r requirements.txt
```

**Optional accelerators** (installed separately):

```bash
pip install numba             # JIT-compiled Langevin engine (~10–50× speedup on loops)
pip install cupy-cuda12x      # GPU offloading via CUDA (auto-detected; falls back to CPU)
pip install dask              # Parallel multi-simulation runs
pip install ripser persim     # Topological Data Analysis (persistent homology)
pip install qiskit qiskit-aer # Quantum-inspired optimizer (falls back to classical)
```

---

## Running the App

### Local (Streamlit)

```bash
streamlit run app.py
```

### Docker

```bash
docker build -t massive:latest .
docker run --rm -p 8501:8501 --env-file .env massive:latest
```

Then open: `http://localhost:8501`

The interface has four tabs:

| Tab | What it does |
|-----|-------------|
| **Simulation** | Configure and run forward simulations with any of the 13 rules; view opinion trajectories, EWS alerts, TDA, and network graph |
| **Social Architect** | Describe a target outcome in plain language; the LLM agent reverse-engineers the intervention schedule |
| **Multilayer** | Run the 5D sociodemographic engine across three network layers with demographic breakdowns |
| **Massive** | Simulate millions of agents using the LOD/uint8/event-driven/GPU engine |

Language toggle (English ↔ Spanish) is available at the top of the sidebar.

### Hugging Face Spaces

This repository is ready to deploy as a Streamlit Space. Connect the repo and set your API keys as Secrets.

---

## Programmatic API

```python
# Forward simulation — 13 rules, LLM selector, EWS
from simulator import simular

result = simular(
    opinion_inicial=0.5,
    regla="hk",                  # Hegselmann-Krause bounded confidence
    pasos=100,
    propaganda=0.3,
    provider="groq",             # heuristic | ollama | groq | openai | openrouter
)

# Multilayer engine — 5D vectors, three network layers
from multilayer_engine import MultilayerEngine

engine = MultilayerEngine(
    N=200,
    layer_weights=(0.4, 0.3, 0.3),   # social, digital, economic
    coupling=0.3,
    attr_config={"religion_prob": 0.35, "age_dist": (0.25, 0.45, 0.30)},
)
history  = engine.run(steps=500)
traj_df  = engine.trajectories_by_attribute("age_group")
corr     = engine.behavior_correlation_matrix()
landscape = engine.get_landscape()

# Massive-scale engine — millions of agents, all optimizations
from massive_engine import MassiveSimEngine

engine = MassiveSimEngine(
    N=1_000_000,
    quantize=True,
    event_driven=True,
    layer_weights=(0.4, 0.3, 0.3),
    seed=42,
)
result = engine.run(steps=300)
print(f"Memory savings: {result['memory_savings_pct']:.1f}%")  # ≈ 99.99%
print(f"Steps/second:   {result['steps_per_second']:.0f}")

# Apply a news shock to 20% of the network
engine.apply_shock(shock_value=0.4, fraction=0.2)
result2 = engine.run(steps=100)

# Memory breakdown
print(engine.memory_report)
# {'n_agents': 1000000, 'n_clusters': 1000, 'float64_MB': 40.0,
#  'lod_MB': 0.04, 'final_MB': 0.005, 'savings_pct': 99.99,
#  'strategies': ['LOD', 'uint8', 'Event-Driven'], 'gpu_backend': 'numpy'}
```

---

## Configuration

### Environment variables

Copy `.env.example` to `.env`:

```env
# LLM providers (at least one required for non-heuristic mode)
GROQ_API_KEY=your_key
OPENAI_API_KEY=your_key
OPENROUTER_API_KEY=your_key

# Social media connectors (optional)
TWITTER_BEARER_TOKEN=your_token
REDDIT_CLIENT_ID=your_id
REDDIT_CLIENT_SECRET=your_secret
```

All five LLM providers resolve credentials through `llm_credentials.py`. In Hugging Face Spaces, set these as Secrets instead of a `.env` file.

### Multilayer configuration

Layer weights, network parameters, and demographic attribute distributions can be changed without touching code via `configs/multilayer.yaml`.

### Empirical calibration

The 43-parameter empirical base (`empirical_calibration.py`) loads automatically. Cultural profiles (Latin, Anglo-Saxon, …) can be applied at runtime via `apply_empirical_profile(cfg)` to adjust base values for region-specific simulations. Parameters with missing data are flagged with `pending_empirical_data` and surfaced as warnings in the UI.

---

## Performance at Scale

`massive_engine.py` combines four strategies to make population-scale simulation tractable on standard hardware:

### 1 — Sociological LOD (super-agents)

Inspired by Level-of-Detail rendering: N agents collapse to M statistical clusters. Only M << N cluster representatives are evolved; the rest are reconstructed at query time.

| N agents | M clusters (auto) | Matrix size | RAM (float64) |
|----------|-------------------|-------------|---------------|
| 10 000 | 100 | 100 × 100 | ~0.08 MB |
| 100 000 | 316 | 316 × 316 | ~0.8 MB |
| 1 000 000 | 1 000 | 1 000 × 1 000 | ~8 MB |

### 2 — uint8 state quantization

Agent parameters stored as unsigned 8-bit integers instead of float64: **87.5% RAM reduction** per parameter with resolution ≈ 0.008 per opinion unit.

```python
opinion_float64 = 0.857432   # 8 bytes
opinion_uint8   = 219         # 1 byte  → dequantize → 0.856...
```

### 3 — Event-driven active sets

Only super-agents whose state changed by more than `sleep_threshold` are updated. Agents in stable consensus are frozen — zero CPU cost until a neighbor wakes them.

### 4 — GPU offloading

Matrix operations auto-delegate to GPU when CuPy or PyTorch+CUDA are detected. Falls back to NumPy automatically — no configuration required.

**Combined effect at N = 1 M agents:** >99.99% RAM reduction vs. a naive float64 implementation.

---

## Social Media Integration

Seed simulations with live opinion data from real platforms:

### Twitter / X

Requires a Bearer Token from the [Twitter Developer Portal](https://developer.twitter.com). The connector queries the v2 Recent Search API, applies keyword-based sentiment scoring, and returns a weighted opinion distribution.

### Reddit

Requires a script-type app at [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) (Client ID + Secret). Uses `praw` to score post titles and bodies by sentiment, weighted by Reddit vote score.

Both connectors support bipolar `[-1, 1]` and unipolar `[0, 1]` ranges and can be configured via the sidebar under **🌐 Social Media Data** or via environment variables.

---

## Validation Protocol (PVU-BS)

MASSIVE ships with a formal **Protocol of Validated Use (PVU-BS)** that defines the minimum evidence standard for claiming validated predictive performance on real-world data.

| Concept | Description |
|---------|-------------|
| **Independent case** | A `{network, time_series, interventions, metadata}` tuple — cases sharing confounds get a `cluster_id` |
| **Target variable** | Compound: Polarization Index P(t) + Turning-Point Skill (F1 on regime transitions) |
| **Anti-leakage** | Test metrics must never be seen before model config is frozen |
| **Statistics** | Diebold-Mariano test + Holm-Bonferroni correction; effect sizes (ΔMAE, ΔRMSE, TPS F1) required alongside p-values |

```bash
# Offline (no API key required — default in CI):
PYTHONHASHSEED=42 python -m benchmarks.runner \
    --cases datasets/pvu_cases --offline \
    --out reports/validation/ci --seed 42

# LLM mode (requires OPENROUTER_API_KEY or OPENAI_API_KEY):
PYTHONHASHSEED=42 python -m benchmarks.runner \
    --cases datasets/pvu_cases --llm \
    --out reports/validation/llm_run --seed 42
```

Full protocol docs: [English](docs/validation/PVU_BeyondSight_EN.md) · [Español](docs/validation/PVU_BeyondSight_ES.md)

> **Note:** `datasets/pvu_cases/` currently contains synthetic cases for pipeline testing only. Real PVU-BS validation requires N ≥ 10 independent real-world cases.

---

## Design Decisions

A few architectural choices that shape how MASSIVE works:

**Opinion as a physical system.** Langevin dynamics brings tools from statistical physics — energy wells, stochastic diffusion, tipping-point theory — into social modeling, while remaining anchored to sociological literature rather than physics metaphors.

**LLM as regime selector, not oracle.** The LLM does not predict outcomes. It selects which mathematical model is most appropriate for the current social context at each step. This keeps outputs interpretable: every prediction traces back to a defined mathematical rule and its peer-reviewed basis.

**Inverse before forward.** The Social Architect was designed alongside the simulator, not bolted on afterward. The propose-simulate-score-refine feedback loop is a first-class architectural feature, not a wrapper.

**Empirical accountability by default.** Every calibration parameter has a source citation and a cultural variance estimate. Gaps are flagged explicitly — the simulator surfaces what it doesn't know rather than filling gaps with defaults silently.

**Scale without a cluster.** The LOD + uint8 + event-driven combination degrades gracefully: a laptop runs meaningful simulations, a GPU cluster runs proportionally faster. No infrastructure requirement.

Modernized assets joined overlays, refreshed interface tuning yielded reliable experience; polished outputs reflect today.

---

## Limitations

- **Quantum module:** Uses classical simulation of quantum-inspired algorithms (QAOA structure via Qiskit Aer or NumPy fallback, MPS-style compression). No real quantum hardware required or used.
- **Empirical base coverage:** Some of the 43 parameters carry `pending_empirical_data` flags. Additional cultural blocks (Nordic, South Asian, Middle Eastern) are partially complete.
- **Real-world validation:** Current PVU-BS benchmark cases are synthetic (for pipeline testing). Real-world opinion dynamics validation (N ≥ 10 independent cases) is in progress.
- **LLM dependence:** The Social Architect and regime selector work best with a cloud LLM. A heuristic fallback is always available but produces less contextually coherent strategies.
- **Social media connectors:** Twitter/X v2 API access requires a developer account with appropriate tier; throughput depends on third-party rate limits.

---

## Roadmap

- [ ] Real PVU-BS validation cases from public opinion datasets
- [ ] Additional cultural calibration blocks (Nordic, South Asian, Middle Eastern)
- [ ] LangChain agent executors with tool access (web search, real-time data retrieval)
- [ ] Node-targeted Social Architect (betweenness-centrality-guided intervention scheduling)
- [ ] Export simulation runs to standard formats (NetLogo, GEXF, CSV)

---

## Project Structure

```
MASSIVE/
├── app.py                        # Streamlit UI — 4 tabs (Simulation, Architect, Multilayer, Massive)
├── simulator.py                  # Core: 13 rules, LLM selector, EWS, TDA, Dask parallel
├── social_architect.py           # Social Architect: iterative LLM reverse-engineering agent
├── energy_engine.py              # Langevin engine (Numba JIT-compiled)
├── energy_runner.py              # Langevin simulation orchestrator
├── energy_schemas.py             # Pydantic v2 schemas for EnergyConfig
├── multilayer_engine.py          # 5D × 3-layer sociodemographic engine (Numba + θ-matrix)
├── massive_engine.py             # Scale engine: LOD, uint8, event-driven, GPU offload
├── extended_models.py            # Rules 10–12: Nash, Bayesian BN (pgmpy), SIR
├── langchain_workflows.py        # LangChain typed chains: strategy, narrative, landscape
├── programmatic_architect.py     # Archetype library + RAM/SQLite cache + LLM landscape gen
├── social_connectors.py          # Twitter/X (v2) and Reddit (praw) live data connectors
├── empirical_calibration.py      # 43-parameter empirical master dictionary
├── empirical_config.py           # Calibration loader + EMPIRICAL_BASE_LOADED flag
├── utility_logic.py              # Game-theoretic strategic force calculator
├── cache_manager.py              # RAM + SQLite landscape cache
├── llm_credentials.py            # Centralized API key resolution for all providers
├── schemas.py                    # Pydantic schemas: StrategyMatrix, GamePayoff
├── visualizations.py             # Network visualization helpers (Plotly + NetworkX)
├── i18n.py                       # Internationalization helpers (English / Spanish)
├── quantum/
│   ├── quantum_optimizer.py      # QAOA-inspired optimizer (Qiskit or classical fallback)
│   ├── tensor_network.py         # MPS-style compression for agent-state matrices
│   └── integration.py            # Drop-in helpers used by multilayer_engine and social_architect
├── benchmarks/                   # PVU-BS offline benchmark runner
│   ├── runner.py                 # CLI entry point (python -m benchmarks.runner)
│   ├── baselines.py              # Naive, MA, AR(1), Random regime baselines
│   ├── metrics.py                # MAE/RMSE/MAPE, Diebold-Mariano, Holm-Bonferroni
│   ├── turning_points.py         # Turning-point detection and F1 scoring
│   └── io.py                     # PVU case loader
├── configs/
│   ├── multilayer.yaml           # Layer weights and demographic attribute configuration
│   └── pvu.yaml                  # PVU runner configuration (split ratios, thresholds, seeds)
├── datasets/pvu_cases/           # Benchmark case folders (currently synthetic)
├── docs/validation/              # PVU-BS protocol (English + Spanish)
├── reports/validation/           # Auto-generated benchmark outputs (metrics.json, report.md)
├── tests/                        # 200+ unit and integration tests
├── .env.example                  # Environment variable template
├── README.md                     # This file (English)
└── README_ES.md                  # Spanish documentation
```

---

## Testing

```bash
pytest tests/
```

The test suite covers: simulator core, energy engine, multilayer engine, massive-scale engine, game-theory layer, social architect, empirical calibration, PVU benchmark runner, visualizations, and LLM integration. Tests run in CI on every push.

---

## Contributing

Contributions are welcome. Please:

1. Fork the repository and create a feature branch.
2. Follow the existing code style (Google-style docstrings, type hints, `pytest` for tests).
3. Add or update tests for any changed behavior and run `pytest tests/` before opening a PR.
4. For new empirical parameters, include source references and cultural variance metadata matching the format in `BEYONDSIGHT_EMPIRICAL_MASTER`.

See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community standards.

---

## License

[Apache License 2.0](LICENSE) — free for personal, academic, and commercial use with attribution.

Design, architecture, and system logic by [Adlgr87](https://github.com/Adlgr87).  
For consulting or collaboration inquiries, contact via [GitHub](https://github.com/Adlgr87).

---

*Many behaving as One.*
