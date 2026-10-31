# MASSIVE Documentation

Welcome to the **MASSIVE** documentation — a hybrid social dynamics simulator
that combines a numerical physics core (Langevin dynamics, LOD super-agents,
data assimilation) with LLM layers used as *mathematical translators* and
regime selectors.

## Key Features

- **Hybrid Architecture:** Numerical simulation with optional LLM context-aware logic.
- **Multiple Models:** DeGroot, Friedkin-Johnsen, Hegselmann-Krause, Granovetter thresholds, evolutionary game theory and more.
- **Multi-Range Support:** Both `[0, 1]` probabilistic and `[-1, 1]` bipolar ranges, with unified range-normalized metrics.
- **Population Scale:** LOD super-agent compression runs 100M agents in ~8 GB RAM.
- **Real-World Calibration:** CIA World Factbook integration ([factbook.md](factbook.md)).
- **Security First:** API keys via environment variables, fail-closed auth, rate limiting.

## Getting Started

```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Or use the CLI, no server needed:

```bash
python -m massive.cli simulate --pasos 30
```

## Where to go next

| Topic | Link |
|---|---|
| HTTP API reference | [api.md](api.md) |
| **Variable coupling matrix** (what drives what) | [architecture/coupling_matrix.md](architecture/coupling_matrix.md) |
| Architecture (current) | [architecture/current-state.md](architecture/current-state.md) |
| Factbook integration | [factbook.md](factbook.md) |
| LLM interface & prompts | [MASSIVE_LLM_INTERFACE.md](MASSIVE_LLM_INTERFACE.md) |
| Validation protocol (PVU-BS) | [validation/README.md](validation/README.md) |
| Runbooks | [runbooks/local-development.md](runbooks/local-development.md) |
| Testing strategy | [testing/test-strategy.md](testing/test-strategy.md) |
| Docker / compose | [DOCKER.md](DOCKER.md) |
| Environment variables | [ENV_VARS.md](ENV_VARS.md) |

## Documentation status: canonical vs historical

This repository accumulated 100+ markdown files, several of which describe
architectures that no longer exist. To know what to trust:

| Location | Status | Trust it for |
|---|---|---|
| `README.md`, this page, `api.md`, `architecture/coupling_matrix.md`, `architecture/current-state.md` | **canonical** | how the system works *today* |
| `docs/architecture/*`, `docs/runbooks/*`, `docs/testing/*`, `docs/security/*` | **current** | design decisions and operations |
| `docs/audit/*` | **point-in-time** | a snapshot of findings at a date; items may already be resolved |
| `docs/validation/*`, `docs/calibration/*` | **current, but versioned** | results tied to a specific model version — check the seal/timestamp |
| `docs/archive/**` | **historical, non-normative** | nothing about the current code; kept as audit trail |
| `CHANGELOG.md` | **canonical** | what changed, and when |

`docs/archive/README.md` lists the module names that were removed (Rust layer,
`social_connectors`, `massive_core/neural_physics`, `mamba_engine`,
`energy_engine_pure`). References to them are history, not documentation.

If a claim in an archived document is still relevant, restate it in current
documentation instead of linking into the archive.
