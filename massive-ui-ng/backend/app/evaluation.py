"""Quality evaluation for the UI-NG translator (golden set).

Evaluates the structured turn contract against a curated set of scenarios
(``eval_golden.json``) covering both languages and the most common social
dynamics: campaigns, polarization, elections, rejection (bipolar range),
trust, game theory and crises.

The heuristic interpreter is deterministic, so these checks act as regression
guards for the fallback path. When ``EVAL_LLM=1`` and a provider is
configured, the same cases are also evaluated against the real LLM path.

Run:

    python -m backend.app.evaluation            # heuristic mode
    EVAL_LLM=1 python -m backend.app.evaluation # LLM mode (needs API key)

Exit code is non-zero when the overall score drops below the threshold
(default 0.8), so the script can gate CI.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.app.models.dto_ui import ChatMessage, ConversationResponse  # noqa: E402
from backend.app.scenario_parser import interpret_turn  # noqa: E402

_GOLDEN = Path(__file__).with_name("eval_golden.json")


def _load_cases() -> list[dict[str, Any]]:
    return json.loads(_GOLDEN.read_text(encoding="utf-8"))["cases"]


def _score_case(
    case: dict[str, Any], resp: ConversationResponse
) -> tuple[float, list[str]]:
    """Score one case against its expectations. Returns (score 0..1, failures)."""
    expect: dict[str, Any] = case.get("expect", {})
    failures: list[str] = []
    checks = 0
    passed = 0

    def check(ok: bool, label: str) -> None:
        nonlocal checks, passed
        checks += 1
        if ok:
            passed += 1
        else:
            failures.append(label)

    draft = resp.config_draft or {}
    estado: dict[str, Any] = draft.get("estado_inicial") or {}
    cfg: dict[str, Any] = draft.get("config") or {}
    params = {a.parameter for a in resp.assumptions}

    if "action" in expect:
        check(resp.action == expect["action"], f"action={expect['action']}")
    if "mode" in expect:
        check(resp.mode == expect["mode"], f"mode={expect['mode']}")
    if "min_assumptions" in expect:
        check(len(resp.assumptions) >= expect["min_assumptions"], "min_assumptions")
    if "max_questions" in expect:
        check(len(resp.questions) <= expect["max_questions"], "max_questions")
    if "assumption_params" in expect:
        missing = set(expect["assumption_params"]) - params
        check(not missing, f"assumption_params missing {missing or 'none'}")
    for key in expect.get("estado_keys", []):
        check(key in estado, f"estado key {key}")
    for key in expect.get("config_keys", []):
        check(key in cfg, f"config key {key}")
    for key, (lo, hi) in expect.get("estado_ranges", {}).items():
        v = estado.get(key)
        check(isinstance(v, (int, float)) and lo <= float(v) <= hi, f"range {key}")
    if "estado_opinion_close_to" in expect:
        target = expect["estado_opinion_close_to"]
        tol = expect.get("estado_opinion_tolerance", 0.05)
        v = estado.get("opinion")
        check(isinstance(v, (int, float)) and abs(float(v) - target) <= tol,
              f"opinion ≈ {target}")
    if "estado_opinion_negative" in expect and expect["estado_opinion_negative"]:
        v = estado.get("opinion")
        check(isinstance(v, (int, float)) and float(v) < 0, "opinion negative")
    if "estado_confianza_min" in expect:
        v = estado.get("confianza")
        check(isinstance(v, (int, float)) and float(v) >= expect["estado_confianza_min"],
              "confianza_min")
    for key, val in expect.get("config_value", {}).items():
        check(cfg.get(key) == val, f"config[{key}]={val}")
    if "pasos_range" in expect:
        lo, hi = expect["pasos_range"]
        p = draft.get("pasos")
        check(isinstance(p, int) and lo <= p <= hi, "pasos_range")
    if "pasos_min" in expect:
        p = draft.get("pasos")
        check(isinstance(p, int) and p >= expect["pasos_min"], "pasos_min")
    if "pasos_max" in expect:
        p = draft.get("pasos")
        check(isinstance(p, int) and p <= expect["pasos_max"], "pasos_max")
    if "reply_contains_any" in expect:
        low = resp.reply.lower()
        check(any(w in low for w in expect["reply_contains_any"]), "reply_contains_any")

    return (passed / checks if checks else 1.0), failures


def evaluate(mode: str = "heuristic", verbose: bool = True) -> dict[str, Any]:
    """Run the golden set and return an aggregate report."""
    cases = _load_cases()
    results: list[dict[str, Any]] = []
    total_score = 0.0
    for case in cases:
        messages = [
            ChatMessage(role="user", content=case["description"]),
        ]
        if mode == "llm":
            from backend.app.routers.conversation import _llm_turn

            resp = _llm_turn(messages, case["language"])
            if resp is None:
                results.append({
                    "id": case["id"], "score": 0.0,
                    "failures": ["LLM unavailable — run with EVAL_LLM=0 for heuristic eval"],
                })
                continue
        else:
            resp = interpret_turn(messages, case["language"])
        score, failures = _score_case(case, resp)
        total_score += score
        results.append({"id": case["id"], "score": score, "failures": failures})
        if verbose:
            status = "✓" if score == 1.0 else "✗"
            print(f"  {status} {case['id']:<28} {score * 100:5.1f}%"
                  + (f"  — {'; '.join(failures)}" if failures else ""))
    n = max(len(cases), 1)
    overall = total_score / n
    return {"mode": mode, "cases": n, "overall": overall, "results": results}


def main() -> int:
    mode = "llm" if os.getenv("EVAL_LLM", "") == "1" else "heuristic"
    threshold = float(os.getenv("EVAL_THRESHOLD", "0.8"))
    print(f"MASSIVE translator evaluation — mode={mode}, threshold={threshold}")
    report = evaluate(mode=mode, verbose=True)
    overall = report["overall"]
    print(f"\nOverall score: {overall * 100:.1f}% ({report['cases']} cases)")
    if overall < threshold:
        print(f"FAILED: below threshold {threshold * 100:.0f}%")
        return 1
    print("PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
