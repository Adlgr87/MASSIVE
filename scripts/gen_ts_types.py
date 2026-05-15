#!/usr/bin/env python3
"""Generate TypeScript types from Pydantic models in backend/app/models.

This script is the single source of truth for the TypeScript API contract.
Run it whenever you change a DTO model::

    python scripts/gen_ts_types.py

Output: ``frontend/src/types/api.generated.ts``

The CI workflow ``validate_ts_types.yml`` runs this script and fails if the
committed file is out of sync with the current model definitions.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Path setup — make the repository root importable
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.models import (  # noqa: E402
    ArchitectEventMessage,
    Feasibility,
    ForecastPoint,
    ForecastResponse,
    InterventionLogEntry,
    InterventionRecord,
    SimAgentLite,
    SimAggregateMetrics,
    SimEventKind,
    SimEventMessage,
    SimMode,
    SimSnapshotMessage,
    SimulationSnapshotPayload,
    SnapshotRecord,
    TimelineTick,
    TimelineResponse,
)

# Ordered list: enums first, then models (dependency order so TS is valid).
_ENUMS: List[Any] = [SimMode, SimEventKind]

_MODELS: List[Any] = [
    SimAgentLite,
    SimAggregateMetrics,
    SimulationSnapshotPayload,
    SimSnapshotMessage,
    SimEventMessage,
    SnapshotRecord,
    TimelineTick,
    TimelineResponse,
    ForecastPoint,
    Feasibility,
    ForecastResponse,
    InterventionRecord,
    InterventionLogEntry,
    ArchitectEventMessage,
]

_OUT = ROOT / "frontend" / "src" / "types" / "api.generated.ts"

# ---------------------------------------------------------------------------
# JSON-Schema → TypeScript converter
# ---------------------------------------------------------------------------


def _schema_to_ts(schema: Dict[str, Any], defs: Dict[str, Any]) -> str:
    """Recursively convert a JSON Schema fragment to a TypeScript type string."""

    # --- direct $ref ---
    if "$ref" in schema:
        return schema["$ref"].split("/")[-1]

    # --- allOf (Pydantic v2 wraps $ref in allOf for annotated fields) ---
    if "allOf" in schema:
        parts = schema["allOf"]
        if len(parts) == 1:
            return _schema_to_ts(parts[0], defs)
        return " & ".join(_schema_to_ts(p, defs) for p in parts)

    # --- anyOf (used for Optional[X] → X | null) ---
    if "anyOf" in schema:
        non_null = [s for s in schema["anyOf"] if s.get("type") != "null"]
        has_null = len(non_null) < len(schema["anyOf"])
        if len(non_null) == 1:
            inner = _schema_to_ts(non_null[0], defs)
        else:
            inner = " | ".join(_schema_to_ts(s, defs) for s in non_null)
        return f"{inner} | null" if has_null else inner

    # --- const (Literal["value"] in Pydantic v2) ---
    if "const" in schema:
        v = schema["const"]
        return f'"{v}"' if isinstance(v, str) else str(v)

    t = schema.get("type")

    # --- string ---
    if t == "string":
        if "enum" in schema:
            return " | ".join(f'"{v}"' for v in schema["enum"])
        return "string"

    # --- numbers ---
    if t in ("number", "integer"):
        return "number"

    # --- boolean ---
    if t == "boolean":
        return "boolean"

    # --- array ---
    if t == "array":
        items = schema.get("items", {})
        return f"{_schema_to_ts(items, defs)}[]"

    # --- object ---
    if t == "object":
        additional = schema.get("additionalProperties")
        if additional and isinstance(additional, dict):
            return f"Record<string, {_schema_to_ts(additional, defs)}>"
        return "Record<string, unknown>"

    return "unknown"


def _model_to_interface(model_cls: Any, defs: Dict[str, Any]) -> str:
    """Render a Pydantic model as a TypeScript ``export interface`` block."""
    schema = model_cls.model_json_schema()
    properties: Dict[str, Any] = schema.get("properties", {})
    required_set = set(schema.get("required", []))

    lines = [f"export interface {model_cls.__name__} {{"]
    for field_name, field_schema in properties.items():
        ts_type = _schema_to_ts(field_schema, defs)
        optional = "?" if field_name not in required_set else ""
        lines.append(f"  {field_name}{optional}: {ts_type};")
    lines.append("}")
    return "\n".join(lines)


def _enum_to_ts(enum_cls: Any) -> str:
    """Render a Python ``str`` Enum as a TypeScript ``export enum`` block."""
    lines = [f"export enum {enum_cls.__name__} {{"]
    for member in enum_cls:
        lines.append(f'  {member.name} = "{member.value}",')
    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    # Collect all $defs from all model schemas (for cross-model $ref resolution).
    all_defs: Dict[str, Any] = {}
    for model_cls in _MODELS:
        schema = model_cls.model_json_schema()
        all_defs.update(schema.get("$defs", {}))

    sections: List[str] = [
        "// ============================================================",
        "// AUTO-GENERATED — do not edit manually.",
        "// Source of truth: backend/app/models (Pydantic v2).",
        "// Regenerate with:  python scripts/gen_ts_types.py",
        "// ============================================================",
        "",
    ]

    for enum_cls in _ENUMS:
        sections.append(_enum_to_ts(enum_cls))
        sections.append("")

    for model_cls in _MODELS:
        sections.append(_model_to_interface(model_cls, all_defs))
        sections.append("")

    content = "\n".join(sections)
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(content, encoding="utf-8")
    print(f"✓  Generated {_OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
