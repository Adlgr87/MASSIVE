"""Benchmark router — ``POST /v1/benchmarks``.

Trigger PVU-BS benchmark runs on-demand.  Supports ``offline`` (no LLM),
``real`` (MASSIVE engine), and ``llm`` (with provider secrets) modes.
"""

from __future__ import annotations

import os
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from backend.app.models import BenchmarkRequest
from backend.app.security import get_api_key, rate_limit_dependency

router = APIRouter(
    prefix="/benchmarks",
    tags=["benchmarks"],
)


@router.post(
    "",
    dependencies=[Depends(get_api_key), Depends(rate_limit_dependency)],
)
async def v1_benchmarks(
    request: Request,
    payload: Annotated[BenchmarkRequest, Body()],
) -> dict[str, Any]:
    """Run the PVU-BS benchmark suite.

    Payload fields:
        cases: str         – path to cases directory (default ``datasets/pvu_cases``).
        mode: str          – ``"offline"`` | ``"real"`` | ``"llm"`` (default ``offline``).
        seed: int          – RNG seed (default 42, non-negative).
        out: str           – output directory (default ``reports/validation/ci``).

    Returns:
        Dict with ``mode``, ``seed``, ``results_count``, ``report`` summary.
    """
    import asyncio

    from benchmarks import runner as bench_runner

    mode = payload.mode
    if mode == "llm" and not any(
        os.getenv(k) for k in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY")
    ):
        raise HTTPException(
            status_code=503,
            detail="LLM mode requested but no LLM API key is configured",
        )

    cases = payload.cases
    seed = payload.seed
    out = payload.out

    # Path sanitization: reject absolute paths or directory traversal
    def _sanitize_path(p: str) -> str:
        """Ensure path is relative and contains no traversal sequences."""
        if p.startswith("/") or p.startswith(".."):
            raise HTTPException(
                status_code=400,
                detail="Path must be relative (no leading / or ..)",
            )
        if ".." in p.split(os.sep):
            raise HTTPException(
                status_code=400,
                detail="Path contains directory traversal (..)",
            )
        return p

    cases = _sanitize_path(cases)
    out = _sanitize_path(out)

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
