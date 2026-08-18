"""Benchmark router — ``POST /v1/benchmarks``.

Trigger PVU-BS benchmark runs on-demand.  Supports ``offline`` (no LLM),
``real`` (MASSIVE engine), and ``llm`` (with provider secrets) modes.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.app.security import get_api_key, rate_limit_dependency

router = APIRouter(
    prefix="/benchmarks",
    tags=["benchmarks"],
)


@router.post("", dependencies=[Depends(get_api_key), Depends(rate_limit_dependency)])
async def v1_benchmarks(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    """Run the PVU-BS benchmark suite.

    Payload fields:
        cases: str         – path to cases directory (default ``datasets/pvu_cases``).
        mode: "offline" | "real" | "llm" (default ``offline``).
        seed: int          (default 42).
        out: str           – output directory (default ``reports/validation/ci``).

    Returns:
        Dict with ``mode``, ``seed``, ``results_count``, ``report`` summary.
    """
    import asyncio

    from benchmarks import runner as bench_runner

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON body required")

    mode = payload.get("mode", "offline")
    if mode == "llm" and not any(
        os.getenv(k) for k in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY")
    ):
        raise HTTPException(
            status_code=503,
            detail="LLM mode requested but no LLM API key is configured",
        )

    cases = payload.get("cases", "datasets/pvu_cases")
    seed = int(payload.get("seed", 42))
    out = payload.get("out", "reports/validation/ci")

    argv = ["--cases", cases, "--out", out, "--seed", str(seed)]
    if mode == "llm":
        argv.append("--llm")
    elif mode == "real":
        argv.append("--real")
    else:
        argv.append("--offline")

    def _run() -> dict[str, Any]:
        rc = bench_runner.main(argv)
        return {"return_code": rc, "mode": mode, "seed": seed, "cases": cases, "out": out}

    # Run CPU-bound benchmark in a thread to avoid blocking the event loop
    result = await asyncio.to_thread(_run)
    if result["return_code"] != 0:
        raise HTTPException(status_code=500, detail="Benchmark execution failed")
    return result
