# Archive — historical, non-normative

Everything under `docs/archive/` is **historical record**. It documents states of
the repository that no longer exist and must never be read as a description of
the current architecture.

Why this marker exists: after the Rust layer, `social_connectors`,
`massive_core/neural_physics`, `mamba_engine` and `energy_engine_pure` were
removed, around 120 references to those modules remained in the docs. They are
legitimate *history* here, but they were indistinguishable from current
documentation, which made onboarding actively misleading.

## How to read this directory

| Directory | Status |
|---|---|
| `docs/archive/` | historical; describes previous architectures, kept for audit trail |
| `docs/audit/` | point-in-time audit snapshots; findings may already be resolved |
| `docs/` (elsewhere) | **current** documentation |

## Ground rules

1. Do not update archive files to match the code. Their value is that they are a
   frozen record. If a claim here is wrong *today*, that is expected.
2. Any claim in an archive document that is still relevant must be restated in
   current documentation, not linked from here.
3. `CHANGELOG.md` is the authoritative history of *changes*; the archive holds
   the longer-form reasoning behind them.

## Dead module names you may encounter here

These no longer exist in the tree and must not be imported:

- `social_connectors` — split into `massive/core/sentiment.py` and `compare_arms.py`
- `massive_core/neural_physics/` — removed (0 references)
- `rust_core/`, `Cargo.toml` — the Rust layer was removed; the build is pure Python
- `mamba_engine` — never shipped
- `energy_engine_pure` — superseded by `energy_engine.py`
- `massive_core/opinion_sources` — removed

`tests/test_packaging_contract.py` enforces that no Python module imports these.
