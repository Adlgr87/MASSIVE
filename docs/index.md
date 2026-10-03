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
| HTTP API | [api.md](api.md) |
| Factbook integration | [factbook.md](factbook.md) |
| LLM interface & prompts | [MASSIVE_LLM_INTERFACE.md](MASSIVE_LLM_INTERFACE.md) |
| Validation protocol (PVU-BS) | [validation/README.md](validation/README.md) |
| Architecture (current) | [architecture/current-state.md](architecture/current-state.md) |
| Runbooks | [runbooks/local-development.md](runbooks/local-development.md) |
| Testing strategy | [testing/test-strategy.md](testing/test-strategy.md) |

> Historical working documents (audits, plans, experiment logs) are archived
> under `docs/archive/` and are not part of this site.
