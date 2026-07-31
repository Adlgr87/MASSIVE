# MASSIVE Optimization Workflow Status

Tracks `workflow_MASSIVE_optimization.md` against `main`.

## FASE 1 — CRÍTICAS

| Fix | Status | Notes |
|-----|--------|-------|
| 1.1 Global `np.random` in engines | **Done** | Local `default_rng` in engines/simulator; steppers use local RNG fallback |
| 1.2 Delete root wrappers | **Rejected (intentional)** | Deprecated re-exports kept for BC (`CLAUDE.md`) |
| 1.3 Consolidate Stability* classes | **Partial** | Canonical: `massive_core.analysis`; physics/sparse variants kept |
| 1.4 SyntaxWarning in tests | **Done** | raw string in `tests/test_contracts.py` |

## FASE 2 — ALTA

| Fix | Status | Notes |
|-----|--------|-------|
| 2.1 Type hints (public surface) | **Done (slice)** | Services, rng, forecast; `mypy.ini` gradual |
| 2.2 `len()` in loops | **Done (core hot paths)** | energy JIT, app animation, perturbation_theory |
| 2.3 Google docstrings | **Done (public services + rng)** | Service layer documented |
| 2.4 TODO triage | **Done (tool)** | `scripts/todo_triage.py` |

## FASE 3 — MEDIA

| Fix | Status | Notes |
|-----|--------|-------|
| 3.1 `config/` package | **Done** | `ScientificRuntimeConfig` + AppSettings + YAML |
| 3.2 Rename `step`/`to_dict` | **Rejected (policy)** | See `docs/NAMING_CONVENTIONS.md` |
| 3.3 Migrate to `@dataclass` | **Done (data types)** | Result/config types already dataclasses; engines kept as classes |
| 3.4 micro_massive RNG | **Done** | agent, influence, orchestrator, forer, **game** |
| 3.5 Logging / API settings | **Done** | `logging_setup.py`; CORS + rate limit from settings |

## FASE 4 — BAJA

| Fix | Status | Notes |
|-----|--------|-------|
| 4.1 Empty `__init__.py` | **Done** | `micro_massive.core` / `utils` export public API |
| 4.2 Centralized logging | **Done** | FASE 3 package; API wires `configure_logging()` |
| 4.3 Coverage tooling | **Done** | `pytest-cov` in dev extras; `[tool.coverage.*]` in `pyproject.toml` |
| 4.4 Stepper local RNG | **Done** | `EulerMaruyamaStepper` owns Generator; no global `randn` |

## Verify

```bash
PYTHONHASHSEED=42 python -m pytest tests/ -q
PYTHONHASHSEED=42 python -m pytest tests/ --cov=massive_core --cov=micro_massive --cov-report=term-missing:skip-covered
python scripts/todo_triage.py
```

## Workflow complete (implementable scope)

| Phase | PR | Commit |
|-------|-----|--------|
| FASE 1 | #69 | opt-phase1-critical |
| FASE 2 | #70 | opt-phase2-high |
| FASE 3 | #71 | opt-phase3-medium |
| FASE 4 | (this) | opt-phase4-low |

## FASE 5+ — post-workflow backlog

See **`docs/BACKLOG_POST_WORKFLOW.md`** (implementable B1–B20 closed or deferred/owner).

Highlights: typecheck slice + CI, ENV_VARS, rate-limit file backend, rotating logs,
repro fixtures, profile_hotspot, deprecation warnings on root wrappers.

## Deferred / owner-side

- Full Stability* file consolidation (high risk)
- Profile-driven deep perf / full multilayer Langevin Rust port
- MutaLambda nested layout / benches (owner-side)
- Hard CI coverage ≥30% gate (informational snapshot in CI)
