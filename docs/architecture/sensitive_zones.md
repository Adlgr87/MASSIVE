# Sensitive zones (surgical-only edits)

These modules form the high-coupling core of MASSIVE. Prefer **small, tested
slices** with explicit validation. Do not “clean up” across boundaries without
a contract test.

| Zone | Why sensitive |
|------|----------------|
| `simulator.py` | Legacy scalar engine; many call sites and rule registry |
| `app.py` | Streamlit UI contracts + history shape |
| `multilayer_engine.py` ↔ `simulator.py` ↔ `massive_engine.py` | Coupled dynamics / RNG / clipping |
| `social_architect.py` + `forecast/` | LLM + temporal forecast pipeline |
| `backend/app/models/` ↔ `scripts/gen_ts_types.py` ↔ `frontend/src/types` | Cross-language type sync |

## Rules of engagement

1. One behavioral change per PR when possible.
2. Keep backward-compatible re-exports until a major version.
3. Add/adjust pytest before touching RNG or history shape.
4. Prefer service layer (`services/`) for new UI/API wiring.
