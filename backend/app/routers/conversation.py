"""Conversation router — the LLM translator endpoint (plain + SSE streaming).

Turn structure is identical whether the interpreter is a real LLM or the
deterministic scenario parser: ``reply + action + assumptions + questions +
config_draft``. The frontend never needs to know which one answered.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.app import llm_chat
from backend.app.llm_prompts import build_interpreter_messages
from backend.app.models.dto_ui import (
    AssumptionItem,
    ChatMessage,
    ConversationRequest,
    ConversationResponse,
)
from backend.app.scenario_parser import interpret_turn
from backend.app.security import get_api_key

log = logging.getLogger("massive.ui_ng.conversation")

router = APIRouter(tags=["conversation"], dependencies=[Depends(get_api_key)])


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _validate_llm_turn(text: str) -> ConversationResponse | None:
    """Parse and validate an LLM turn; returns None when unusable."""
    if text is None:
        return None
    data = llm_chat.extract_json(text)
    if data is None:
        log.warning("LLM turn returned unparseable JSON — falling back to heuristic")
        return None
    try:
        assumptions = [
            AssumptionItem(
                parameter=str(a.get("parameter", "param")),
                value=str(a.get("value", "")),
                reason=str(a.get("reason", "")),
                confidence=float(a.get("confidence", 0.5)),
            )
            for a in data.get("assumptions", [])
            if isinstance(a, dict)
        ]
        action = data.get("action", "propose")
        if action not in ("clarify", "propose", "ready"):
            action = "propose"
        draft = data.get("config_draft") or {}
        if not isinstance(draft, dict):
            draft = {}
        return ConversationResponse(
            reply=str(data.get("reply", "")),
            action=action,
            assumptions=assumptions,
            questions=[str(q) for q in data.get("questions", []) if isinstance(q, str)][:3],
            config_draft=draft,
            mode="llm",
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("LLM turn validation failed (%s) — falling back", exc)
        return None


def _llm_turn(messages: list[ChatMessage], language: str) -> ConversationResponse | None:
    """Ask the LLM for a structured translator turn. Returns None on failure."""
    text = llm_chat.chat_completion(
        build_interpreter_messages(
            [{"role": m.role, "content": m.content} for m in messages], language
        ),
        temperature=0.2,
        max_tokens=1400,
        json_mode=True,
    )
    return _validate_llm_turn(text)


def _interpret(messages: list[ChatMessage], language: str) -> ConversationResponse:
    """LLM first, deterministic heuristic fallback."""
    cfg = llm_chat.resolve_provider()
    llm_enabled = cfg["configured"] or cfg["provider"] == "ollama"
    if llm_enabled:
        result = _llm_turn(messages, language)
        if result is not None:
            return result
        log.info("LLM turn failed — using heuristic interpreter")
    return interpret_turn(messages, language)


@router.post("/api/conversation", response_model=ConversationResponse)
def api_conversation(req: ConversationRequest) -> ConversationResponse:
    """One translator turn: free-text scenario → structured draft + assumptions."""
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages required")
    return _interpret(req.messages, req.language)


@router.post("/api/conversation/stream")
def api_conversation_stream(req: ConversationRequest) -> StreamingResponse:
    """SSE variant of the translator turn.

    Events:
      - ``status``: {"mode": "llm"|"heuristic", ...}
      - ``token``:  {"text": "…"} (LLM deltas, only in LLM mode)
      - ``done``:   the full ConversationResponse JSON
      - ``error``:  {"detail": "…"}
    """
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages required")

    cfg = llm_chat.resolve_provider()
    llm_enabled = cfg["configured"] or cfg["provider"] == "ollama"

    def gen():
        if not llm_enabled:
            result = interpret_turn(req.messages, req.language)
            yield _sse("status", {"mode": "heuristic"})
            yield _sse("done", result.model_dump())
            return

        yield _sse("status", {"mode": "llm", "provider": cfg["provider"]})
        acc: list[str] = []
        try:
            for delta in llm_chat.chat_completion_stream(
                build_interpreter_messages(
                    [{"role": m.role, "content": m.content} for m in req.messages],
                    req.language,
                ),
                temperature=0.2,
                max_tokens=1400,
            ):
                acc.append(delta)
                yield _sse("token", {"text": delta})
        except Exception as exc:  # noqa: BLE001
            log.warning("LLM stream failed: %s", exc)

        result = _validate_llm_turn("".join(acc))
        if result is None:
            result = interpret_turn(req.messages, req.language)
            yield _sse("status", {"mode": "heuristic", "reason": "llm-unusable"})
        yield _sse("done", result.model_dump())

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
