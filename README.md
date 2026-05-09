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

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![tests](https://github.com/Adlgr87/MASSIVE/actions/workflows/pytest.yml/badge.svg)](https://github.com/Adlgr87/MASSIVE/actions/workflows/pytest.yml)
[![docs](https://github.com/Adlgr87/MASSIVE/actions/workflows/mkdocs.yml/badge.svg)](https://github.com/Adlgr87/MASSIVE/actions/workflows/mkdocs.yml)
[![PVU Validation](https://github.com/Adlgr87/MASSIVE/actions/workflows/pvu-validation.yml/badge.svg)](https://github.com/Adlgr87/MASSIVE/actions/workflows/pvu-validation.yml)

![MASSIVE UI Demo](docs/massive_ui_mockup.png)

<p align="left">
  <img src="https://github.com/user-attachments/assets/4a977da4-76f4-48aa-b793-bdb48f65b07c" alt="MASSIVE logo" width="140"/>
</p>

### Latest integrated updates

- Updated UI reference image to match the current MASSIVE interface (`docs/massive_ui_mockup.png`).
- Added the project logo to the Streamlit simulator header (`app.py`).
- Refreshed README visual references to remove the old sample naming.

Release mnemonic for this integration cycle: Model adapters join orchestration routines in tandem, yielding reliable empirical predictions over real-world trends.

Hybrid social dynamics simulator — Numerical core + LLM as regime selector. Built for scale, from a handful of agents to millions.

MASSIVE bridges the gap between classic mathematical models of opinion formation and the contextual flexibility of Large Language Models (LLMs). Its architecture is designed from the ground up to remain computationally tractable whether you are probing a small community or a population-scale social network.

At the heart of MASSIVE lies the **Social Architect** — a reverse-engineering LLM agent that discovers the precise sequence of mathematical interventions needed to steer any social network toward a desired outcome. Rather than predicting where a network *will* go, the Social Architect determines exactly *how to get* where you want.

Each individual is no longer a scalar opinion but a **multidimensional state vector** encoding simultaneous behaviors — cooperation, hierarchy recognition, income, information access — evolving in parallel across three superimposed network layers (social, digital, economic) modulated by fixed sociodemographic attributes such as religion, education, and age. At population scale, agents are organized into statistically representative clusters that preserve emergent social dynamics while reducing memory and compute by orders of magnitude.

## Theoretical Foundations and Research

The project is inspired by fundamental opinion dynamics models and cutting-edge research.

### Base Models (Opinion Dynamics)

- **DeGroot and Friedkin-Johnsen Models:** Base implementation for opinion evolution in social networks, considering neighbor influence and resistance to change (prejudices).
- **Hegselmann-Krause (2002) - Bounded Confidence:** Agents only interact with groups whose opinion is within a radius `ε`, fostering natural polarization and cluster formation.
- **Competitive Contagion (Beutel et al., 2012):** Models the spread of two rival narratives competing simultaneously in the system.
- **Heterogeneous Threshold (Granovetter, 1978):** Uses a normal distribution of thresholds in the population instead of a static one, enabling rapid social cascade phenomena.
- **Co-evolutionary Networks and Homophily (Axelrod, 1997):** Influence intensity varies by opinion similarity, generating endogenous echo chambers.
- **Replicator Equation — Evolutionary Game Theory (Taylor & Jonker, 1978):** Strategy frequencies evolve according to relative payoff via the replicator ODE integrated with RK45.
- **Confirmation Bias:** A cognitive transversal mechanism that systematically attenuates the weight of information contrary to the agent's current belief.
- **Langevin Energy Dynamics:** Physics-inspired stochastic differential equations where agents move through a configurable social energy landscape of attractors and repellers.
- **Multilayer Sociodemographic Langevin:** Vector extension of Langevin dynamics to five simultaneous behaviors per agent `(opinion, cooperation, hierarchy, income, info_access)`, across three superimposed network layers (social, digital, economic), with noise modulation by fixed demographic attributes (religion, education, age, gender). The multidimensional social potential generates emergent patterns: opinion polarization coexisting with cooperation clustering and hierarchy stratification.

### Extended Models

Three additional simulation rules (rules 10–12 in `extended_models.py`) expand the mathematical vocabulary of the Social Architect and the traditional simulator:

- **Nash Equilibrium — Game Theory (Nash, 1950):** Rule 10. Models stable mixed-strategy equilibria between social groups. At each step, a 2×2 coordination payoff matrix is built from the curre[...]  

- **Bayesian Opinion Network (Pearl, 1988):** Rule 11. A proper discrete Bayesian network (built with `pgmpy`) with nodes `Propaganda → Opinion ← Confianza, PresionSocial`. Evidence (propagand[...]  

- **SIR Epidemiological Contagion (Kermack & McKendrick, 1927):** Rule 12. Treats opinion adoption as an epidemic: Susceptible (can be influenced), Influenced (adopted), Resistant (immune to furth[...]  

### Hybrid Architecture

Unlike purely numerical simulations, MASSIVE uses an LLM (like Llama 3) to analyze historical trajectories and decide which mathematical transition regime is sociologically most coherent at ea[...] 

**Academic Connection:** MASSIVE's approach resonates with recent research like *"Opinion Consensus Formation Among Networked Large Language Models"* (January 2026), exploring how intelligent [...]  

### Cross-Cutting Mechanisms

Three mechanisms are applied transversally on top of any simulation rule at every step:

- **Confirmation Bias (Sunstein 2009, Nickerson 1998):** Incoming information that contradicts the agent's current position is systematically attenuated proportionally to the configured bias level[...]  

- **Dynamic Homophily (Axelrod 1997, Flache et al. 2017):** Group influence weights update automatically each step based on opinion similarity — the more similar a group's opinion, the stronger [...]  

- **Strategic Game Theory Layer (Nash 1950, Axelrod 1984):** A payoff-based force (`utility_logic.py`) biases each agent toward cooperation or defection depending on neighbors' average position re[...]  

### Early Warning Signals & Topological Analysis

MASSIVE monitors the simulation for proximity to tipping points using two complementary methods:

**Early Warning Signals (EWS) — Critical Slowing Down (Scheffer et al., 2009; Dakos et al., 2012):**  
Over a sliding window of the last 10 opinion values, the system continuously computes variance, lag-1 autocorrelation, and skewness. When any metric exceeds its threshold, a ⚠️ EWS warning is [...]  

**Topological Data Analysis — Persistent Homology (Carlsson, 2009; Perea & Harer, 2015):**  
When the optional `ripser` + `persim` packages are installed, MASSIVE performs Takens delay-embedding of the opinion time series and computes H1 persistence diagrams via Vietoris-Rips filtrati[...]  

### Empirical Calibration Base

Modeling complex social phenomena requires anchoring simulations to measurable, real-world parameters.  
Academic research spanning psychology, political science, and network theory provides this empirical foundation.  
Jointly calibrated from more than 40 peer-reviewed sources, each parameter carries variance metadata for cultural adaptation.  
Opinion dynamics treated in isolation from data risks producing mathematically elegant but sociologically hollow results.  
Rooting the simulator in these calibration indices shifts MASSIVE from a theoretical toy to a research-grade instrument.  
Indices covering algorithmic drift, parasocial influence, confirmation bias, temporal decay, and game-theoretic payoffs are pre-loaded.  
Together, they form a living empirical base that researchers can extend by adding parameters or updating cultural variance estimates.  
Years of accumulated social science converge into a normalized bipolar spectrum, ready to inform every simulation step.  
Researchers and practitioners alike can query the master dictionary at runtime to inspect source citations and confidence levels.  
Evidence-grounded parameters prevent the simulator from drifting into pure speculation, keeping outputs interpretable and falsifiable.  
Providing this layer of empirical accountability is what distinguishes MASSIVE from a pure mathematical sandbox.  
Over upcoming releases, additional cultural blocks — Nordic, South Asian, Middle Eastern — will be populated with localized estimates.  
Remaining gaps are flagged with `pending_empirical_data` tags, making the boundaries of current knowledge explicit rather than hidden.  
Transparency about uncertainty is, ultimately, the most honest form of scientific modeling.

#### Empirical Integrations and Functionality

The empirical data is integrated into the project through several key components:

- **`empirical_calibration.py`**: Contains the master dictionary `BEYONDSIGHT_EMPIRICAL_MASTER` with 43 parameters normalized to [-1.0, 1.0]. Each parameter includes metadata like source references (e.g., I1, I2, I3), cultural variances for different blocks (Latin, Anglo-Saxon, etc.), and notes on conflicts or resolutions.

- **`empirical_config.py`**: Loads the empirical base on import, setting the `EMPIRICAL_BASE_LOADED` flag. It derives runtime parameters in `BEYONDSIGHT_RUNTIME_PARAMS`, including validation flags for parameters without data.

- **Integration in `simulator.py`**: During simulation runs in the `simular()` function, empirical defaults are applied if available. For example:
  - `ruido_base` (noise level) is set from the `temperature` parameter.
  - `efecto_vecinos_peso` (social influence weight) from `social_influence_lambda`.
  - Payoff values for coordination and defection in game theory rules.

- **`apply_empirical_profile(cfg)` function**: Merges empirical values into the simulation configuration without overwriting user-specified settings. Supports cultural profiles that adjust base values (e.g., Latin profile increases algorithmic drift).

- **Cultural Adaptations**: Runtime profiles modify parameters based on cultural variance data, allowing simulations tailored to specific sociological contexts.

- **Validation and Warnings**: Parameters with null values are flagged in `validation_flags`. The Streamlit app (`app.py`) displays warnings for pending empirical data, ensuring users are aware of knowledge gaps.

- **Testing**: Unit tests in `tests/test_empirical_*.py` verify loading, application, and cultural modifications.

This integration ensures simulations are empirically grounded, enhancing their realism and applicability to real-world social dynamics.

The master dictionary consolidates 43 parameters spanning network dynamics, temporal decay, and game-theoretic payoffs, all normalized to the bipolar `[-1.0, 1.0]` spectrum.

## Multilayer Sociodemographic Engine

While the Energy Landscape Engine operates on scalar opinions, the **Multilayer Engine** (`multilayer_engine.py`) elevates each agent to a five-dimensional state vector capturing their distinct roles in social dynamics simultaneously:

```
x_i(t) = (opinion_i, cooperation_i, hierarchy_i, income_i, info_access_i)
```

### Three-layer architecture

Three differentiated adjacency matrices model the interaction spaces an individual inhabits in parallel:

| Layer | Network model | Phenomenon captured |
|-------|---------------|---------------------|
| **Social** | Watts-Strogatz (small world) | Face-to-face contacts, local community |
| **Digital** | Barabási-Albert (scale-free) | Social media, viral content, echo chambers |
| **Economic** | Hierarchical (star + hubs) | Authority flow, labor market, wages |

Layer weights (`w_social`, `w_digital`, `w_economic`) are tunable from the UI, enabling exploration of scenarios where digital influence overtakes community bonds or economic hierarchy dominates opinion formation.

### Sociodemographic modulation (theta_matrix)

Each agent has fixed attributes that modulate their sensitivity to noise and signals across each behavioral dimension:

```python
theta[i, opinion]     *= 1 + 0.5 * religion_i    # religious: more sensitive to moral signals
theta[i, cooperation] *= 1 + 0.3 * education_i   # educated: greater cooperative tendency
theta[i, hierarchy]   *= 1 + 0.4 * (age_i / 2)  # older: more deference to authority
```

This modulation produces realistic heterogeneity: two agents starting at the same opinion position diverge at different rates depending on their demographic profile, replicating variability observed in surveys and field studies.

### Multidimensional social potential

The gradient ∇U(x) acts on all five dimensions with independent but coupled dynamics:
- **Opinion**: double well (emergent polarization toward ±0.7)
- **Cooperation**: attraction toward the agent's social alignment level
- **Hierarchy**: bifurcation toward extremes (rebel ↔ conformist)
- **Income**: centering force with friction proportional to hierarchy level
- **Info access**: slow decay modulated by cooperation

### Programmatic API

```python
from multilayer_engine import MultilayerEngine

engine = MultilayerEngine(
    N=200,
    layer_weights=(0.4, 0.3, 0.3),   # social, digital, economic
    coupling=0.3,
    attr_config={"religion_prob": 0.35, "age_dist": (0.25, 0.45, 0.30)},
)
history = engine.run(steps=500)

# Trajectories by age group
traj_df = engine.trajectories_by_attribute("age_group")

# Behavioral correlation matrix (5×5)
corr = engine.behavior_correlation_matrix()

# Social landscape metrics
landscape = engine.get_landscape()
```

Layer and attribute defaults can be customized without touching code via `configs/multilayer.yaml`.

## Energy Landscape Engine

MASSIVE's **Energy Landscape Engine** models social dynamics as a physical system where every agent's opinion evolves according to a Langevin stochastic differential equation:

```
x_i(t+η) = x_i(t) − η·∇U(x_i) + η·λ·(x̄_neighbors − x_i) + √(2η·T)·ε
```

| Term | Meaning |
|---|---|
| `∇U(x)` | Gradient of the social energy landscape (attractors/repellers) |
| `λ` (`lambda_social`) | Balance: 0 = pure landscape, 1 = pure social network influence |
| `T` (`temperature`) | Noise / free will — higher = more chaotic individual behavior |
| `ε ~ N(0,1)` | Stochastic term (Euler-Maruyama integration) |

**Attractors** model forces of social cohesion (consensus points, factional identities, official positions). **Repellers** model forces of social division (moderation aversion, anti-consensus dyn[...]  

### Pre-built Social Archetypes

The **Programmatic Architect** (`programmatic_architect.py`) ships with 8 validated archetypes covering the most common sociological scenarios:

| Archetype key | Description |
|---|---|
| `polarizacion_extrema` | Two irreconcilable camps. Center is no-man's land. |
| `polarizacion_moderada` | Two groups with possible dialogue at the center. |
| `consenso_moderado` | Society gravitates toward agreements. |
| `consenso_forzado` | Strong institutional pressure toward a single position. |
| `fragmentacion_3_grupos` | Three coexisting factions that don't merge. |
| `fragmentacion_4_grupos` | Four tribal communities with high segmentation. |
| `caos_social` | No clear structure. Each agent acts on its own impulse. |
| `radicalizacion_progresiva` | Agents start at center and are pulled toward extremes. |

**Resolution pipeline** — for any free-text goal, the engine tries in order:
1. **Exact archetype match** (instant, no API call)
2. **RAM cache** (sub-millisecond, same process)
3. **SQLite cache** (`LandscapeCache`) — persists across Streamlit sessions and container restarts
4. **LLM one-shot generation** (Groq / OpenAI / OpenRouter / Ollama) with Pydantic validation
5. **Fallback** to `caos_social` if LLM fails or returns invalid config

## 🧠 Social Architect — The Crown Jewel

The **Social Architect** is MASSIVE's flagship feature and its most powerful capability. Where traditional simulations ask *"what will happen?"*, the Social Architect answers: **"what must I [...]**

### Concept: Sociological Reverse Engineering

You describe the **desired social outcome** in plain language — the final state you want a social network, community, or organization to reach. The Social Architect figures out the **exact sequ[...]  

Examples of what you can ask for:
- *"Eliminate polarization in 30 steps and achieve moderate consensus."*
- *"Gradually shift the majority opinion toward adoption of a new policy."*
- *"Dissolve an echo chamber and reconnect fragmented groups."*
- *"Reduce resistance to organizational change among informal leaders."*  

The system responds with a **structured intervention schedule** (`StrategyMatrix`): a timeline of mathematical regimes, their parameters, and a human-readable sociological narrative explaining wh[...]  

---

### Stochastic Dynamics: The Langevin Equations  

MASSIVE models social opinion as a continuous stochastic process. At each discrete time step `t`, the opinion of the representative agent evolves according to a **discrete-time Langevin equat[...]  

```
x(t + Δt)  =  f(x(t), r(t))  ·  α  +  b(x(t))  ·  (1 − α)  +  G(x(t))  +  η(t)
```

Where:

| Term | Meaning |
|---|---|
| `f(x(t), r(t))` | Output of the active dynamical regime `r` (e.g., Hegselmann-Krause, threshold, memory, replicator…) |
| `α` (alpha blend) | Blending weight between LLM-selected model and base tendency (default 0.80) |
| `b(x(t))` | Base tendency: `0.92 · opinion + 0.08 · propaganda` — inertia and media pressure |
| `G(x(t))` | Group polarization effect — weighted influence of ideological clusters A and B |
| `η(t) ~ 𝒩(0, σ(t)²)` | **Stochastic Wiener increment** — Gaussian white noise representing social unpredictability |

The **adaptive noise coefficient** `σ(t)` is the Langevin diffusion term and captures the idea that **distrust amplifies social volatility**:

```
σ(t) = σ_base + σ_distrust · (1 − trust(t))
```

- `σ_base = 0.03` — irreducible background noise (spontaneous opinion drift)
- `σ_distrust = 0.08` — extra volatility injected when institutional trust is low
- `trust(t) ∈ [0, 1]` — dynamically updated each step

As trust erodes, the diffusion coefficient grows, producing wider fluctuations and making the system harder to steer — a mathematically grounded model of societal instability. In the multi-simu[...]  

---

### The Iterative LLM–Simulation Loop

The Social Architect operates through a closed feedback loop that combines the reasoning power of an LLM with the rigor of mathematical simulation:

```
┌────────────────────────────────────────────────────────────────[...]
│                    SOCIAL ARCHITECT LOOP                        │
│                                                                 │
│  1. USER INPUT                                                  │
│     Desired sociological outcome (free text) +                  │
│     Initial network state                                       │
│              │                                                  │
│              ▼                                                  │
│  2. LLM PROPOSAL                                                │
│     The LLM (GPT-4o, Llama 3, Mistral…) reads the goal and     │
│     proposes a StrategyMatrix: a JSON schedule of              │
│     interventions (model_name, parameters, time windows)        │
│              │                                                  │
│              ▼                                                  │
│  3. NUMERICAL SIMULATION                                        │
│     run_with_schedule() executes each intervention phase        │
│     through the Langevin engine, step by step                   │
│              │                                                  │
│              ▼                                                  │
│  4. EVALUATION                                                  │
│     Score 0–100 computed from polarization, opinion delta,      │
│     variance. Qualitative feedback generated.                   │
│              │                                                  │
│         Score ≥ 90? ──YES──► 5. NARRATIVE (success)            │
│              │                                                  │
│             NO                                                  │
│              │                                                  │
│  6. REFINEMENT                                                  │
│     Feedback injected into LLM context. LLM proposes a         │
│     corrected strategy. Loop repeats (up to max_attempts).      │
│              │                                                  │
│         Best attempt ──────► 5. NARRATIVE (best effort)         │
└────────────────────────────────────────────────────────────────[...]
```

**Step-by-step breakdown:**

1. **User Input:** You describe the target state in natural language and optionally set the initial network conditions (opinion, trust, propaganda, group membership).

2. **LLM Proposal:** An LLM (local via Ollama or cloud via Groq / OpenAI / OpenRouter) receives a system prompt that encodes its role as a sociological strategist and a user prompt containing the[...]  

3. **Numerical Simulation:** `run_with_schedule()` steps through the timeline. In each phase, the specified dynamical regime is locked in and applied at every time step through the Langevin engin[...]  

4. **Evaluation:** `evaluar_resultado()` computes a score (0–100) based on how close the final state is to the stated objective. It analyses mean polarization, total opinion drift (`delta`), an[...]  

5. **Refinement:** If the score is below 90, the feedback (what went wrong, which metrics were off) is appended to the LLM context and a new iteration begins. The LLM can see all prior failures a[...]  

6. **Narrative:** Once a satisfactory strategy is found (or exhausted), `generar_narrativa_final()` asks the LLM to translate the dry mathematical schedule into a **rich sociological or organizat[...]  

---

### Two Operational Modes

| Mode | Use Case | Vocabulary & Framing |
|---|---|---|
| **Macro** | Public opinion, electoral campaigns, social media polarization, mass movements | Media campaigns, hashtags, echo chambers, political discourse, referendums |
| **Corporate** | Organizational change, HR, internal culture, team alignment | 1:1 meetings, OKRs, informal leaders, resistance to change, 30-60-90 day plans |

In **Corporate mode**, the Social Architect also receives network graph metrics (betweenness centrality, degree centrality) and can target specific high-influence nodes (informal leaders) as the [...]  

---

### Output: The StrategyMatrix

The result is a validated `StrategyMatrix` object containing:
- A **sequence of intervention phases**, each with: start/end time, mathematical regime, parameters, and sociological rationale.
- A **score** reflecting how precisely the simulation matched the stated goal.
- A **final narrative** — a consultant-quality report explaining the full strategy in plain language.

The Social Architect is, in essence, an **AI sociological engineer**: it searches the combinatorial space of mathematical intervention sequences, validates each candidate through the Langevin sim[...]  

---

### LangChain Integration

When the **LangChain toggle** is enabled in the sidebar, both the Social Architect and the Programmatic Architect route their LLM calls through typed `LangChain` chains (`langchain_workflows.py`)[...]  

- **Typed output parsing** — `JsonOutputParser` catches malformed JSON before it reaches the simulator.
- **Provider-agnostic** — supports `groq` (via `langchain-groq`), `openai`, `openrouter`, and `ollama` through the same chain interface.
- **Composable chains** — `strategy_chain`, `narrative_chain`, and `landscape_chain` can be extended with memory, tools, or agent executors in future iterations.

The fallback is always active: if LangChain is unavailable or the chain fails, the system reverts to direct HTTP calls.

## Installation

```bash
pip install -r requirements.txt
```

## Running the App

### Local Mode (Streamlit)
```bash
streamlit run app.py
```

The UI supports **English and Spanish** — use the Language toggle at the top of the sidebar to switch languages at any time.

### Running on Hugging Face Spaces
This repository is ready to be deployed as a **Hugging Face Space**. Simply connect this repo to a new Streamlit Space.

## Social Media Integration

MASSIVE can seed simulations with **real opinion data** fetched live from Twitter/X or Reddit. Configure credentials in the sidebar under **🌐 Datos de Redes Sociales**.

### Twitter / X

Requires a **Bearer Token** (Twitter Developer Portal → Project → App → Keys & Tokens).

| Credential | Where to get it |
|---|---|
| Bearer Token | [developer.twitter.com](https://developer.twitter.com) → Project → App → Keys & Tokens |

The connector queries the [Twitter v2 Recent Search API](https://developer.twitter.com/en/docs/twitter-api/tweets/search/introduction), applies keyword-based sentiment scoring, and returns the we[...]  

### Reddit

Requires a **script-type application** registered at [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps).

| Credential | Description |
|---|---|
| Client ID | App's client ID (shown under the app name) |
| Client Secret | App's secret |
| User Agent | Any string, e.g. `MASSIVE/1.0` |

The connector uses `praw` to search a subreddit, scores each post's title + body for sentiment, weights by Reddit vote score, and returns a distribution of community opinions.

Both connectors work with **bipolar** `[-1, 1]` and **unipolar** `[0, 1]` ranges. You can set credentials via environment variables to avoid re-entering them:

```env
TWITTER_BEARER_TOKEN=xxx
REDDIT_CLIENT_ID=xxx
REDDIT_CLIENT_SECRET=xxx
```

## Performance Optimization

### Numba — JIT-accelerated Langevin Engine

The `SocialEnergyEngine` in `energy_engine.py` uses **Numba** to JIT-compile the inner Langevin step loop via `@njit`. On first call, the kernel is compiled once; all subsequent calls are native-[...] 

### Dask — Parallel Multi-Simulation

The **⚡ Paralelizar con Dask** toggle in the UI activates `simular_multiples_dask()`, which wraps each of the N simulations in a `dask.delayed` task and executes them concurrently across all av[...] 

## Scale — Millions of Agents on Standard Hardware

`massive_engine.py` handles the computational demands of population-scale simulation through four integrated strategies, enabling runs with millions of agents on a laptop — no GPU cluster required.

### Strategy 1 — Sociological LOD (Super-Agents)

Inspired by Level-of-Detail rendering in video games: instead of simulating N individual agents, the engine groups them into **M super-agents** (clusters). Only M << N cluster centers are evolved by the Langevin equations; each center represents a group of agents with similar socio-psychological profiles.

| N agents | M clusters (auto) | Matrix size | RAM (float64) |
|---|---|---|---|
| 10 000 | 100 | 100×100 | ~0.08 MB |
| 100 000 | 316 | 316×316 | ~0.8 MB |
| 1 000 000 | 1 000 | 1000×1000 | ~8 MB |

The `apply_shock()` method lets you inject an external perturbation (news event, economic shock) that reactivates sleeping clusters and propagates through the network.

### Strategy 2 — State Quantization (uint8 personalities)

Agent state parameters are stored as unsigned 8-bit integers (0–255) instead of 64-bit floats, reducing RAM by **87.5%** per parameter. The mapping preserves sociologically meaningful resolution (≈ 0.008 per unit of opinion range).

```python
# Before: float64 — 8 bytes/parameter
opinion_naive = 0.857432   # 8 bytes

# After: uint8 — 1 byte/parameter
opinion_quant = 219         # 1 byte  → dequantize → 0.856...
```

Combined with LOD, the net memory reduction for N=1M agents reaches **>99.99%** vs a naive float64 implementation.

### Strategy 3 — Event-Driven Simulation (Gossip Sparsity)

In real social dynamics, not everyone changes their opinion at every moment. The `ActiveSet` class tracks which super-agents are "awake" based on whether their state changed by more than a configurable threshold (`sleep_threshold`).

- Agents whose neighbors changed significantly are automatically reactivated.
- Agents in stable consensus remain frozen — zero CPU cost until perturbed.
- The `active_history` metric shows the fraction of active super-agents per step, revealing when the system is converging.

### Strategy 4 — GPU Offloading

Matrix operations (social force computation, stochastic integration) are automatically delegated to GPU when **CuPy** or **PyTorch+CUDA** are detected. The CPU-side Numba JIT path is used as fallback, so the engine works on any machine without configuration changes.

### Programmatic API

```python
from massive_engine import MassiveSimEngine

# Simulate 1 million agents with all optimizations
engine = MassiveSimEngine(
    N=1_000_000,
    quantize=True,
    event_driven=True,
    sleep_threshold=5e-3,
    layer_weights=(0.4, 0.3, 0.3),
    coupling=0.3,
    dt=0.01,
    seed=42,
)

result = engine.run(steps=300)
print(f"Memory savings: {result['memory_savings_pct']:.1f}%")   # ≈ 99.99%
print(f"Mean opinion:   {result['mean_opinion']:+.3f}")
print(f"Speed:          {result['steps_per_second']:.0f} steps/s")

# Apply a news shock to 20% of the network
engine.apply_shock(shock_value=0.4, fraction=0.2)
result2 = engine.run(steps=100)
```

The `memory_report` property gives a detailed breakdown of savings by strategy:

```python
rep = engine.memory_report
# {'n_agents': 1000000, 'n_clusters': 1000, 'float64_MB': 40.0,
#  'lod_MB': 0.04, 'final_MB': 0.005, 'savings_pct': 99.99,
#  'strategies': ['LOD (Super-Agentes)', 'Cuantización uint8', 'Event-Driven'],
#  'gpu_backend': 'numpy'}
```



## Protocol of Validated Use (PVU-BS)

MASSIVE ships with a formal **validation protocol** that establishes the minimum evidence standard for claiming validated predictive performance on real-world opinion dynamics data.

### Key concepts

| Concept | Description |
|---------|-------------|
| **Independent case** | A `{network, time_series, interventions, metadata}` tuple where networks share < 10 % nodes and time windows don't overlap unmodelled global shocks. Cases sharing a confound get a `cluster_id`. |
| **Target variable** | Compound: **Polarization Index P(t)** (variance + extremity) + **Turning-Point Skill** (F1 on regime transitions). |
| **Anti-leakage** | Test metrics must never be seen before model config is frozen. Full rules in [docs/validation/PVU_BeyondSight_EN.md](docs/validation/PVU_BeyondSight_EN.md). |
| **Statistics** | Diebold–Mariano test + **Holm–Bonferroni** correction for multiple baselines × cases. Effect sizes (ΔMAE, ΔRMSE, TPS F1) are mandatory alongside p-values. |
| **Sample vs real** | `datasets/pvu_cases/sample_case_*` are **synthetic** — for pipeline testing only. Real PVU requires N ≥ 10 independent real-world cases. |

### Running the benchmark

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

---

## Project Structure

```
MASSIVE/
├── benchmarks/                   # PVU-BS offline benchmark runner
│   ├── runner.py                 # CLI entry point (python -m benchmarks.runner)
│   ├── baselines.py              # Naive, MA, AR(1), Random regime
│   ├── metrics.py                # MAE/RMSE/MAPE, Diebold–Mariano, Holm–Bonferroni
│   ├── turning_points.py         # Turning-point detection and F1 scoring
│   └── io.py                     # PVU case loader
├── configs/
│   ├── multilayer.yaml               # Layer and sociodemographic attribute configuration
│   └── pvu.yaml                  # Runner configuration (split ratios, thresholds, seeds)
├── datasets/
│   └── pvu_cases/                # PVU case folders (sample_case_001, sample_case_002, …)
├── docs/
│   └── validation/               # Bilingual PVU-BS protocol and templates (EN/ES)
├── reports/
│   └── validation/               # Auto-generated benchmark outputs (metrics.json, report.md)
├── tests/                        # Unit and integration tests
│   ├── test_energy_core.py       # Energy engine test suite (42 tests)
│   ├── test_game_theory.py       # Strategic Game Theory layer tests
│   ├── test_integration_llm.py   # LLM selector integration tests
│   ├── test_massive_engine.py    # Massive-scale engine tests (42 tests)
│   ├── test_multilayer.py        # Multilayer engine test suite (27 tests)
│   ├── test_pvu_runner.py        # PVU benchmark runner tests
│   ├── test_simulator.py         # Simulator core tests
│   ├── test_social_architect.py
│   └── test_visualizations.py
├── docs/                         # MkDocs documentation sources
├── .env.example                  # Environment variable template
├── .gitignore
├── app.py                        # Streamlit interface (4 tabs: Simulation, Architect, Multilayer, Massive)
├── cache_manager.py              # RAM + SQLite landscape cache
├── empirical_calibration.py      # Master empirical calibration dictionary (43 parameters)
├── empirical_config.py           # Calibration loader — EMPIRICAL_BASE_LOADED flag
├── energy_engine.py              # Langevin dynamics engine (Numba-accelerated)
├── energy_runner.py              # Langevin simulation orchestrator
├── energy_schemas.py             # Pydantic v2 schemas for EnergyConfig
├── extended_models.py            # Extended rules: Nash (10), Bayesian BN (11), SIR (12)
├── i18n.py                       # Internationalization helpers (English / Spanish)
├── langchain_workflows.py        # LangChain chains for Social & Programmatic Architects
├── massive_engine.py             # Massive-Scale Engine: LOD, uint8 quantization, event-driven, GPU
├── multilayer_engine.py          # Multilayer Sociodemographic Engine (5D vector + 3 layers + theta)
├── programmatic_architect.py     # Programmatic Architect (archetypes + cache + LLM)
├── README.md                     # Documentation (English)
├── README_ES.md                  # Documentation (Spanish)
├── requirements.txt              # Dependencies
├── schemas.py                    # Pydantic schemas for StrategyMatrix and Game Theory
├── simulator.py                  # Simulator core: 13 rules, EWS, TDA, Dask parallel, LLM logic
├── social_architect.py           # Social Architect inverse-engineering agent
├── social_connectors.py          # Twitter/X and Reddit API connectors
├── utility_logic.py              # Game Theory strategic force calculator
└── visualizations.py             # Network visualization helpers
```

## Security

API keys can be managed via environment variables. Copy `.env.example` to `.env` and fill in your keys:

- `GROQ_API_KEY`
- `OPENAI_API_KEY`
- `OPENROUTER_API_KEY`
- `TWITTER_BEARER_TOKEN` *(optional — social media integration)*
- `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` *(optional — social media integration)*

In Hugging Face Spaces, you can set these as **Secrets**.

## License

This project is licensed under the **Apache License 2.0** — free for personal, academic, and commercial use with attribution to the author.

The logic, structure, variables, and system design belong to [Adlgr87](https://github.com/Adlgr87). The code is open source so anyone can use, modify, and build on it — credit always appreciated.

For consulting inquiries or collaborations, contact [Adlgr87](https://github.com/Adlgr87) on GitHub.

---
*Many behaving as One.*
