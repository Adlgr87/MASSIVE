# MASSIVE Optimization Workflow Status

Tracks `workflow_MASSIVE_optimization.md` against `main`.

## FASE 1 — CRÍTICAS

| Fix | Status | Notes |
|-----|--------|-------|
| 1.1 Global `np.random` in engines | **Done** | Local `default_rng` in `massive_engine`, `multilayer_engine`, `energy_engine`, `simulator`, `visualizations`, `energy_runner` |
| 1.2 Delete root wrappers | **Rejected (intentional)** | Root `schemas.py`, `utility_logic.py`, `intervention_optimizer.py`, etc. are **deprecated re-exports** required for backward compatibility (`CLAUDE.md` / remediation). Not deleted. |
| 1.3 Consolidate Stability* classes | **Partial** | Canonical import: `massive_core.analysis`. Physics/sparse variants kept (different roles). Full file move deferred (high risk). |
| 1.4 SyntaxWarning in tests | **Done** | raw string match in `tests/test_contracts.py` |

## FASE 2 — ALTA

| Fix | Status | Notes |
|-----|--------|-------|
| 2.1 Type hints (public surface) | **Done (slice 1)** | Services, `rng.py`, `forecast/targets.py`; `mypy.ini` gradual |
| 2.2 `len()` in loops | **Done (core hot paths)** | energy JIT, app animation, perturbation_theory |
| 2.3 Google docstrings | **Done (public services + rng)** | Service layer fully documented |
| 2.4 TODO triage | **Done (tool)** | `scripts/todo_triage.py` — core tree currently clean |

## FASE 3 — MEDIA

| Fix | Status | Notes |
|-----|--------|-------|
| 3.1 `config/` package | **Done** | `config.py` → `massive_core/config/` with `ScientificRuntimeConfig` re-export for BC |
| 3.2 AppSettings + YAML | **Done** | `settings.py` + `defaults.yaml`; env overrides |
| 3.3 Logging setup | **Done** | `logging_setup.py`; wired in `api.py` |
| 3.4 micro_massive RNG | **Done** | `seed`/`rng` on agent, influence, orchestrator, forer |
| 3.5 Naming policy | **Done** | `docs/NAMING_CONVENTIONS.md` — no mass rename of `step`/`to_dict` |
| 3.6 API CORS / rate limit | **Done** | Driven by `get_app_settings()` with env override |

## FASE 4 — BAJA (slice included)

| Fix | Status | Notes |
|-----|--------|-------|
| 4.1 Config-driven defaults | **Done (slice)** | YAML + AppSettings for sim defaults, CORS, rate limit |
| 4.2 Broader type-hint pass | **Deferred** | Beyond public services; continue incrementally |
| 4.3 Deep perf (beyond len) | **Deferred** | Profile-driven; no speculative rewrites |

## Verify

```bash
PYTHONHASHSEED=42 python -m pytest tests/ -q
python scripts/todo_triage.py
```

## Remaining (optional / later)

- Broader type-hint pass on `massive_core/`
- Profile-guided performance work
- MutaLambda nested layout (owner-side)
