# MASSIVE Repomix Instructions

This bundle helps AI assistants inspect MASSIVE quickly and safely.

## Read order

1. `README.md` (or `README_ES.md`) — product overview, architecture diagram,
   verified endpoint inventory and repository map. Start here.
2. For runtime behaviour, prioritize the engines at the repo root —
   `simulator.py`, `massive_engine.py`, `energy_engine.py`,
   `multilayer_engine.py` — plus `massive_core/` for the opt-in scientific
   layer and `massive_core/kernels.py` for the vectorized hot path.
3. For the HTTP surface, read `backend/app/main.py` and `backend/app/routers/`.
   There is a single versioned API: everything is mounted under `/v1/*`.
4. For compatibility checks, inspect the relevant files under `tests/` before
   proposing changes.

## Change discipline

- Keep the classic public APIs backward-compatible: `simular`,
  `simular_multiples` and `run_with_schedule` (all in `simulator.py`).
- New capabilities should be opt-in and live in new modules unless an existing
  integration point must be touched.
- Preserve the opinion-range clipping rules: `bipolar` is `[-1, 1]`,
  `unipolar` is `[0, 1]`.
- Do not change numerical behaviour as a side effect of refactoring. The suite
  is seeded; a simulation run with a fixed seed must produce identical output
  before and after any non-functional change.
- Avoid committing generated Repomix bundles; regenerate them locally.

## Useful local commands

```bash
# Repomix has no committed config in this repo; pass the options you need.
npx --yes repomix@latest
npx --yes repomix@latest --compress -o repomix-output-compressed.xml

# Verification
pytest tests/
ruff check . && black --check .
make verify-build          # static Docker preflight (no Docker required)
```
