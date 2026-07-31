# MASSIVE naming conventions

Related: `workflow_MASSIVE_optimization.md` FIX 3.2

## Policy

**Do not mass-rename** methods like `step()`, `to_dict()`, `parse()`, or `validate()`
across modules. In this codebase they are intentional OOP verbs scoped to a class:

| Method | Meaning |
|--------|---------|
| `Engine.step()` | Advance one integration / simulation step |
| `Optimizer.step()` | Advance one optimization iteration (if present) |
| `Model.to_dict()` | Serialize this object (not a global serializer) |
| `Parser.parse()` | Parse the format owned by that parser |

Blind renames (`step` → `sim_step` everywhere) break Protocol implementations,
duck typing, and third-party call sites without improving clarity.

## Preferred imports

- Scientific flags: `from massive_core.config import ScientificRuntimeConfig`
- App settings: `from massive_core.config import get_app_settings`
- Logging: `from massive_core.config import configure_logging, get_logger`
- Stability analysis: `from massive_core.analysis import StabilityAnalyzer`

## When to rename

Only rename when:

1. Two callables in the **same module** collide, or
2. A public function is genuinely ambiguous without a class qualifier, or
3. A deprecation cycle can ship aliases for one major version.
