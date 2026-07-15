# MASSIVE — Backlog post-workflow (FASE 5+)

Prioritized improvements **outside** the completed remediation and optimization
workflows (`REMEDIATION_STATUS.md`, `OPTIMIZATION_STATUS.md`).

## Status legend

| Tag | Meaning |
|-----|---------|
| **P0** | Small, high ROI — do next |
| **P1** | Medium effort, clear value |
| **P2** | Larger / needs design or profiling |
| **Done** | Closed in a PR |
| **Rejected** | Explicit non-goal (policy / BC) |

---

## Mini-workflow FASE 5 — first slice (this PR track)

| ID | Item | Priority | Status |
|----|------|----------|--------|
| B1 | Fix Pydantic `Intervention` `model_validator` (must `return self`) | P0 | **Done** |
| B2 | Refresh `experiments/` smoke + reproducibility (local RNG, no stale “bug RNG” docs) | P0 | **Done** |
| B3 | Coverage baseline + focused tests for critical modules | P0 | **Done** |

### Coverage notes (B3)

- Tooling: `pytest-cov` + `[tool.coverage.*]` in `pyproject.toml` (FASE 4).
- Focused tests: `tests/test_opt_phase5.py` (Intervention, config, stepper/energy seeds).
- On some Python 3.14 + NumPy builds, `coverage` tracing can hit
  `ImportError: cannot load module more than once per process` during collection.
  Prefer measuring coverage in CI (stable 3.10–3.12 images) until local stack is fixed.

### Verify (FASE 5 slice)

```bash
PYTHONHASHSEED=42 python -m pytest tests/ -q
PYTHONHASHSEED=42 python experiments/00_smoke/run_smoke_tests.py
PYTHONHASHSEED=42 python experiments/05_reproducibility/run_reproducibility.py
PYTHONHASHSEED=42 python -m pytest tests/ --cov=massive_core --cov=micro_massive --cov=forecast --cov-report=term-missing:skip-covered
```

---

## Remaining backlog (ordered)

### P0 / P1 — next slices

| ID | Item | Notes |
|----|------|-------|
| B4 | Broader type-hint pass on `massive_core/` engines/numerics | Gradual mypy; extend beyond services |
| B5 | Raise line coverage toward 25–30% with module-by-module tests | Tooling ready (`pytest-cov` in `pyproject.toml`) |
| B6 | Harden reproducibility pytest fixtures (bit-equality) for engines + `simular_multiples` | Beyond experiment scripts |
| B7 | Document full `MASSIVE_*` env map for AppSettings | CORS/rate limit already partial |

### P1 / P2 — architecture & product

| ID | Item | Notes |
|----|------|-------|
| B8 | Full `Stability*` consolidation | High risk; keep physics/sparse variants unless proven isomorphic |
| B9 | Gradual deprecation of root wrappers (`schemas.py`, etc.) | Warnings → docs → major; do **not** hard-delete |
| B10 | Sensitive zones: surgical only | `simulator.py`, `app.py`, multilayer boundary, forecast/architect |
| B11 | Align root `progress.md` with post-#72 state | Cartography hygiene |
| B12 | EnKF: level vs slope / directional accuracy | Research from benchmark cards |
| B13 | API rate-limit shared store (multi-worker) | In-process dict is single-worker only |
| B14 | Optional rotating file logging | Console path already centralised |
| B15 | mypy gate in CI | After broader type coverage |

### P2 — performance (profile first)

| ID | Item | Notes |
|----|------|-------|
| B16 | Profile-guided hot paths | multilayer Langevin, energy JIT, sparse, ActiveSet |
| B17 | Rust: full `multilayer_langevin_step` | After statistical parity of pre-sampled noise |
| B18 | Do **not** Rust-migrate yet | EnKF BLAS, MPS/SVD, dynamic network build |

### Owner-side

| ID | Item | Notes |
|----|------|-------|
| B19 | MutaLambda nested `tests/` / `benchmarks/` | Core adapter done in remediation; nested layout is operator-owned |
| B20 | Factbook local JSON artifacts | Commit as fixtures or gitignore — do not leave ambiguous untracked dumps |

---

## Explicit non-goals (carry-forward policy)

- Mass-rename of OOP verbs (`step`, `to_dict`) — see `docs/NAMING_CONVENTIONS.md`
- Blind deletion of BC re-export wrappers — see `CLAUDE.md`
- Speculative rewrites without profile evidence

---

## Suggested next PR after FASE 5 slice

1. **B4 + B15** — type-hint numerics package + optional CI mypy (non-blocking first)
2. **B5** — coverage map + tests for lowest-covered critical modules
3. **B16** — one profiled hotspot PR only
