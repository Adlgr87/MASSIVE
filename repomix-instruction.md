# MASSIVE Repomix Instructions

This Repomix bundle is intended to help AI assistants inspect MASSIVE quickly and safely.

## Read order

1. Start with `CLAUDE.md`; its MASSIVE-specific protocols are mandatory for code changes.
2. Read `README.md` or `README_ES.md` for the product overview and repository map.
3. For runtime behavior, prioritize `simulator.py`, `massive_engine.py`, `energy_engine.py`, and `massive_core/`.
4. For compatibility checks, inspect the relevant files under `tests/` before proposing changes.

## Change discipline

- Keep the classic public APIs (`simular`, `simular_multiples`, `run_with_schedule`) backward-compatible.
- New capabilities should be opt-in and live in new modules unless an existing integration point must be touched.
- Preserve opinion range clipping rules documented in `CLAUDE.md`.
- Avoid committing generated Repomix bundles; regenerate them locally when needed.

## Useful local commands

```bash
npx --yes repomix@latest --config repomix.config.json
npx --yes repomix@latest --config repomix.config.json --compress -o repomix-output-compressed.xml
pytest tests/
```
