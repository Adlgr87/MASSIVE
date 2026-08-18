"""DTOs for the Next-Gen UI (UI-NG) translator workflow.

These models are the typed contract between the React frontend and the
FastAPI backend. They follow the repository convention: Pydantic v2 with
``extra="forbid"`` and snake_case JSON keys.

The frontend mirrors these types in ``frontend/src/types.ts``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Conversation (translator) contract
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """Single message in the assistant conversation."""

    role: Literal["user", "assistant", "system"]
    content: str


class AssumptionItem(BaseModel):
    """One explicit assumption the interpreter made about missing context."""

    parameter: str
    value: str
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)


class ConversationRequest(BaseModel):
    """Payload for one translator turn."""

    messages: list[ChatMessage] = Field(min_length=1)
    language: Literal["es", "en"] = "es"


class ConversationResponse(BaseModel):
    """Structured assistant turn.

    ``action`` semantics:
      - ``clarify``: missing information, questions must be answered first.
      - ``propose``: a draft config is available for review.
      - ``ready``:   the draft is complete enough to run.
    """

    reply: str
    action: Literal["clarify", "propose", "ready"]
    assumptions: list[AssumptionItem] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    config_draft: dict[str, Any] = Field(default_factory=dict)
    mode: Literal["llm", "heuristic"]


# ---------------------------------------------------------------------------
# Simulation contract
# ---------------------------------------------------------------------------


class SimulateRequest(BaseModel):
    """Payload for a simulation run."""

    engine: Literal["scalar", "energy", "multilayer", "massive"] = "scalar"
    escenario: str = "campana"
    pasos: int = Field(default=50, ge=5, le=500)
    estado_inicial: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    seed: int | None = Field(default=None, ge=0)
    scientific: bool = True
    language: Literal["es", "en"] = "es"
    audience: Literal["general", "tecnico"] = "general"
    # engine-specific parameters
    n_agents: int | None = Field(default=None, ge=2, le=1_000_000)
    connectivity: float = Field(default=0.3, ge=0.01, le=1.0)
    range_type: Literal["bipolar", "unipolar"] = "bipolar"
    layer_weights: list[float] | None = None
    quantize: bool = True
    event_driven: bool = True


class Highlight(BaseModel):
    """One headline metric with a short human meaning."""

    label: str
    value: str
    meaning: str


class SimulateResponse(BaseModel):
    """Result of a simulation run, including the natural-language narrative."""

    run_id: str
    engine: str
    mode: Literal["llm", "heuristic"]
    language: str
    summary: dict[str, Any] = Field(default_factory=dict)
    scientific_report: dict[str, Any] | None = None
    series: dict[str, Any] = Field(default_factory=dict)
    narrative: str = ""
    highlights: list[Highlight] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class ExplainRequest(BaseModel):
    """Re-narrate a stored run with a different audience/language."""

    run_id: str
    language: Literal["es", "en"] = "es"
    audience: Literal["general", "tecnico"] = "general"


class ExplainResponse(BaseModel):
    """Narrative-only response."""

    run_id: str
    language: str
    audience: str
    narrative: str
    highlights: list[Highlight] = Field(default_factory=list)
    mode: Literal["llm", "template"]


class RunListItem(BaseModel):
    """Lightweight entry for the run history sidebar."""

    run_id: str
    engine: str
    language: str
    headline: str
    final_opinion: float | None = None
    dominant_rule: str | None = None
    mode: str


# ---------------------------------------------------------------------------
# Capabilities / status contract
# ---------------------------------------------------------------------------


class LLMStatus(BaseModel):
    """Configured LLM provider information."""

    configured: bool
    provider: str
    model: str


class CFCStatus(BaseModel):
    """Closed-form continuous-time model availability."""

    regime_selector: bool = False
    tau_matrix: bool = False
    architect_policy: bool = False


class StatusResponse(BaseModel):
    """Backend capabilities report consumed by the frontend status bar."""

    service: str
    version: str
    llm: LLMStatus
    cfc: CFCStatus
    rust_available: bool
    engines: list[str]
    factbook_countries: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=lambda: ["es", "en"])
