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
| **Deferred** | Documented; not implemented now |
| **Owner** | Operator / external tree |
| **Rejected** | Explicit non-goal (policy / BC) |

---

## FASE 5 — status board

| ID | Item | Status |
|----|------|--------|
| B1 | Intervention `model_validator` returns `self` | **Done** (#73) |
| B2 | Refresh experiments smoke/repro (local seed) | **Done** (#73) |
| B3 | Focused tests + coverage tooling notes | **Done** (#73) |
| B4 | Gradual type-hint / mypy slice (numerics/config/…) | **Done** (#74) |
| B4b | Extend type slice to physics/metalearning | **Done** |
| B5 | Coverage tests + CI informational snapshot | **Done** |
| B6 | Hard bit-equality repro tests (engines + multiples) | **Done** |
| B7 | `docs/ENV_VARS.md` full env map | **Done** |
| B8 | Full Stability* consolidation | **Deferred** (high risk; canonical import already `massive_core.analysis`) |
| B9 | DeprecationWarning on root wrappers | **Done** |
| B10 | Sensitive zones documented | **Done** (`docs/architecture/sensitive_zones.md`) |
| B11 | Root `progress.md` aligned | **Done** |
| B12 | EnKF level vs slope research note | **Done** (`docs/research/enkf_level_vs_slope.md`) |
| B13 | Multi-worker rate limit (`file` backend) | **Done** |
| B14 | Optional rotating file logging | **Done** |
| B15 | CI mypy job (non-blocking) | **Done** (`.github/workflows/typecheck.yml`) |
| B16 | Profile hotspot script | **Done** (`scripts/profile_hotspot.py`) |
| B17 | Rust full multilayer Langevin | **Deferred** (profile first; see `docs/rust_core_plan_ES.md`) |
| B18 | Do not Rust-migrate EnKF/MPS/networks yet | **Rejected** as work item (policy holds) |
| B19 | MutaLambda nested tests/benchmarks | **Owner** |
| B20 | Factbook local dumps gitignore | **Done** |

---

## Verify

```bash
PYTHONHASHSEED=42 python -m pytest tests/ -q
python scripts/typecheck_slice.py
python scripts/profile_hotspot.py --top 15
python scripts/todo_triage.py
```

## Explicit non-goals (still)

- Mass-rename of OOP verbs (`step`, `to_dict`) — `docs/NAMING_CONVENTIONS.md`
- Hard-delete BC re-export wrappers — `CLAUDE.md`
- Speculative rewrites without profile evidence

## Remaining optional (future)

1. Harden CI coverage gate once 3.11 baseline is known
2. Profile-driven single-hotspot PR (use B16 output)
3. EnKF directional-accuracy metric harness
4. MutaLambda nested layout (owner)
