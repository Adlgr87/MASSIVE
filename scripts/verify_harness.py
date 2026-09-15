#!/usr/bin/env python3
"""Unified verification harness for the MASSIVE audit-remediation workflow.

Runs every quality gate in sequence with a one-line summary per stage:

  Stage 1 -- ruff
  Stage 2 -- black --check
  Stage 3 -- mypy-slice
  Stage 4 -- pytest with coverage
  Stage 5 -- TypeScript type regeneration + diff
  Stage 6 -- mkdocs build --strict
  Stage 7 -- G-1 guardrails (AST parse, bare-except, TODO triage, pip-audit,
            TS-types diff, mkdocs, smoke test)

Modes
-----
Normal  (``python scripts/verify_harness.py``):

    Runs all stages.  Exits non-zero if **any** stage fails -- expected to
    be "red" at the Wave-0 baseline (commit 473b04a6).

Baseline (``python scripts/verify_harness.py --baseline``):

    Runs all stages, collects metrics, writes ``reports/audit_baseline.json``.
    Always exits 0 so that a *measurement* never blocks the pipeline.
"""

from __future__ import annotations

import argparse
import ast
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REPORTS = REPO / "reports"
BASELINE_FILE = REPORTS / "audit_baseline.json"

# Guardrail finding IDs (G-1 rule).
D1_010 = "D1-010"
D2_007 = "D2-007"
D2_015 = "D2-015"
D3_020 = "D3-020"
D5_017 = "D5-017"
D6_018 = "D6-018"
D8_008 = "D8-008"
D8_009 = "D8-009"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(cmd, capture=True, timeout=300):
    """Run *cmd* in the repo root, returning the CompletedProcess."""
    return subprocess.run(
        cmd,
        cwd=str(REPO),
        capture_output=capture,
        text=True,
        timeout=timeout,
    )


def _ok(proc):
    return proc.returncode == 0


def _count_ruff_issues(stdout):
    m = re.search(r"Found\s+(\d+)\s+error", stdout)
    return int(m.group(1)) if m else 0


def _count_black_files(stdout):
    """Count files that black would reformat.

    Handles both per-file output ('would reformat path') and the
    summary line ('X files would be reformatted').
    """
    count = 0
    for line in stdout.splitlines():
        if line.startswith("would reformat "):
            count += 1
    # Also parse the summary line: "103 files would be reformatted"
    m = re.search(r"(\d+)\s+files would be reformatted", stdout)
    if m:
        return int(m.group(1))
    return count


def _count_mypy_errors(stdout):
    m = re.search(r"Found\s+(\d+)\s+error", stdout)
    return int(m.group(1)) if m else 0


def _parse_pytest_summary(stdout):
    out = {"tests_total": 0, "tests_passed": 0, "tests_failed": 0, "tests_errors": 0}
    m = re.search(r"(\d+)\s+passed", stdout)
    if m:
        out["tests_passed"] = int(m.group(1))
    m = re.search(r"(\d+)\s+failed", stdout)
    if m:
        out["tests_failed"] = int(m.group(1))
    m = re.search(r"(\d+)\s+errors", stdout)
    if m:
        out["tests_errors"] = int(m.group(1))
    out["tests_total"] = out["tests_passed"] + out["tests_failed"] + out["tests_errors"]
    return out


def _count_loc():
    total = 0
    skip = {
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        "site",
        "dist",
        "build",
    }
    for p in REPO.rglob("*.py"):
        if any(part in skip for part in p.parts):
            continue
        try:
            with open(p, encoding="utf-8", errors="ignore") as fh:
                total += sum(1 for _ in fh)
        except OSError:
            continue
    return total


def _count_root_entries():
    return len([p for p in REPO.iterdir() if not p.name.startswith(".")])


def _coverage_pct():
    try:
        import coverage

        cov = coverage.Coverage(data_file=str(REPO / ".coverage"))
        cov.load()
        with open(os.devnull, "w") as devnull:
            pct = cov.report(file=devnull)
        return round(pct, 1)
    except Exception:
        return None


def _get_sha():
    proc = _run(["git", "rev-parse", "HEAD"])
    return proc.stdout.strip() if _ok(proc) else "unknown"


class StageResult:
    """Result of a single verification stage."""

    def __init__(self, name, passed, metrics=None, detail=""):
        self.name = name
        self.passed = passed
        self.metrics = metrics or {}
        self.detail = detail


# ---------------------------------------------------------------------------
# Stage runners
# ---------------------------------------------------------------------------


def run_ruff():
    proc = _run(["ruff", "check", "."], timeout=120)
    return StageResult(
        "ruff",
        _ok(proc),
        {"ruff_issues": _count_ruff_issues(proc.stdout + proc.stderr)},
        proc.stdout.strip()[-500:],
    )


def run_black():
    proc = _run(["black", "--check", "."], timeout=120)
    return StageResult(
        "black",
        _ok(proc),
        {"black_files": _count_black_files(proc.stdout + proc.stderr)},
        proc.stdout.strip()[-500:],
    )


def run_mypy_slice():
    proc = _run([sys.executable, "scripts/typecheck_slice.py"], timeout=120)
    return StageResult(
        "mypy-slice",
        _ok(proc),
        {"mypy_errors": _count_mypy_errors(proc.stdout + proc.stderr)},
        proc.stdout.strip()[-500:],
    )


def run_pytest():
    proc = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "-q",
            "--cov",
            "--cov-report=term-missing",
            "--cov-report=json:" + str(REPO / "cov.json"),
        ],
        timeout=600,
    )
    summary = _parse_pytest_summary(proc.stdout + proc.stderr)
    pct = _coverage_pct()
    if pct is not None:
        summary["coverage_pct"] = pct
    return StageResult("pytest+coverage", _ok(proc), summary, proc.stdout.strip()[-800:])


def run_ts_types():
    proc = _run([sys.executable, "scripts/gen_ts_types.py"], timeout=60)
    if not _ok(proc):
        return StageResult("ts-types-regen", False, detail=proc.stderr[:500])
    diff = _run(["git", "diff", "--exit-code", "frontend/src/types/api.generated.ts"], timeout=30)
    return StageResult("ts-types-diff", _ok(diff), detail="in sync" if _ok(diff) else "out of sync")


def run_mkdocs():
    proc = _run([sys.executable, "-m", "mkdocs", "build", "--strict"], timeout=120)
    return StageResult("mkdocs-strict", _ok(proc), detail=proc.stdout[-300:])


def run_guard_ast_parse():
    """G-1 D1-010: AST-parse every Python file (no syntax errors)."""
    bad = []
    for f in glob.glob("**/*.py", recursive=True):
        if any(x in f for x in (".venv", "node_modules", "/site/", "/dist/")):
            continue
        try:
            with open(f) as fh:
                ast.parse(fh.read(), f)
        except SyntaxError as e:
            bad.append(f"{f}:{e.lineno}")
    return StageResult(f"G1-ast-parse [{D1_010}]", not bad, detail="; ".join(bad))


def run_guard_bare_except():
    """G-1 D2-007: No bare ``except:`` in tracked Python files.

    Uses ``git grep`` so that ``.venv`` and ``node_modules`` are never scanned.
    A bare ``except:`` is one with no exception type — we match the pattern
    ``except:`` followed by end-of-line or a comment.
    """
    proc = _run(
        ["bash", "-c", r'git grep -nE "^\s*except:\s*$|^\s*except:\s*#" -- "*.py"'],
        timeout=30,
    )
    found = proc.stdout.strip() != ""
    return StageResult(
        f"G1-no-bare-except [{D2_007}]",
        not found,
        detail=proc.stdout.strip()[:200] if found else "none found",
    )


def run_guard_todo_triage():
    """G-1 D2-015: Run todo triage (expect 0 TODO/FIXME markers)."""
    proc = _run([sys.executable, "scripts/todo_triage.py"], timeout=60)
    clean = "No TODO/FIXME markers" in proc.stdout
    return StageResult(f"G1-todo-triage [{D2_015}]", _ok(proc) and clean, detail=proc.stdout[:500])


def run_guard_pip_audit():
    """G-1 D5-017: pip-audit — no known vulnerabilities."""
    if shutil.which("pip-audit"):
        cmd = ["pip-audit", "-r", "requirements.txt", "--no-deps"]
    else:
        cmd = [sys.executable, "-m", "pip_audit", "-r", "requirements.txt", "--no-deps"]
    proc = _run(cmd, timeout=120)
    return StageResult(f"G1-pip-audit [{D5_017}]", _ok(proc), detail=proc.stdout[:500])


def run_guard_ts_types():
    """G-1 D3-020: TS types in sync (git diff exit code)."""
    proc = _run(["git", "diff", "--exit-code", "frontend/src/types/api.generated.ts"], timeout=30)
    return StageResult(
        f"G1-ts-types-sync [{D3_020}]", _ok(proc), detail="in sync" if _ok(proc) else "out of sync"
    )


def run_guard_mkdocs():
    """G-1 D6-018: mkdocs build --strict."""
    proc = _run([sys.executable, "-m", "mkdocs", "build", "--strict"], timeout=120)
    return StageResult(f"G1-mkdocs-strict [{D6_018}]", _ok(proc), detail=proc.stdout[-300:])


def run_guard_smoke():
    """G-1 D8-008/D8-009: Smoke test — simulator micro-run."""
    code = (
        "from simulator import simular, resumen_historial\n"
        "h = simular({'opinion':0.5,'propaganda':0.7,'confianza':0.4,"
        "'opinion_grupo_a':0.72,'opinion_grupo_b':0.28,'pertenencia_grupo':0.65},"
        " pasos=30, verbose=False)\n"
        "assert resumen_historial(h)['pasos'] == 30\n"
        "print('smoke OK')\n"
    )
    proc = _run([sys.executable, "-c", code], timeout=300)
    return StageResult(
        f"G1-smoke-test [{D8_008} {D8_009}]", _ok(proc), detail=proc.stdout.strip()[-300:]
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

STAGES = [
    ("ruff", run_ruff),
    ("black", run_black),
    ("mypy-slice", run_mypy_slice),
    ("pytest+coverage", run_pytest),
    ("ts-types", run_ts_types),
    ("mkdocs", run_mkdocs),
]

GUARDRAILS = [
    ("ast-parse", run_guard_ast_parse),
    ("no-bare-except", run_guard_bare_except),
    ("todo-triage", run_guard_todo_triage),
    ("pip-audit", run_guard_pip_audit),
    ("ts-types-sync", run_guard_ts_types),
    ("mkdocs-strict", run_guard_mkdocs),
    ("smoke-test", run_guard_smoke),
]


def run_all():
    results = []
    for name, fn in STAGES + GUARDRAILS:
        t0 = time.time()
        try:
            result = fn()
        except Exception as exc:
            result = StageResult(name, False, detail=f"EXCEPTION: {exc}")
        elapsed = time.time() - t0
        result.detail = (result.detail or "") + f" ({elapsed:.1f}s)"
        results.append(result)
    return results


def print_report(results):
    print("\n" + "=" * 70)
    print("  MASSIVE Verification Harness")
    print("=" * 70)
    all_pass = True
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}]  {r.name}")
        all_pass = all_pass and r.passed
    print("=" * 70)
    if all_pass:
        print("  ALL STAGES PASSED")
    else:
        failed = [r.name for r in results if not r.passed]
        print(f"  {len(failed)} stage(s) failed: {', '.join(failed)}")
    print("=" * 70 + "\n")


def write_baseline(results):
    REPORTS.mkdir(parents=True, exist_ok=True)
    metrics = {
        "commit_sha": _get_sha(),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    for r in results:
        metrics.update(r.metrics)
    metrics.setdefault("loc", _count_loc())
    metrics.setdefault("root_entries", _count_root_entries())
    for key in (
        "tests_total",
        "tests_passed",
        "tests_failed",
        "coverage_pct",
        "ruff_issues",
        "black_files",
        "mypy_errors",
    ):
        metrics.setdefault(key, 0)
    BASELINE_FILE.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    print(f"  Baseline written to {BASELINE_FILE.relative_to(REPO)}")
    return metrics


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Collect metrics and write reports/audit_baseline.json; always exit 0",
    )
    args = parser.parse_args()

    results = run_all()
    print_report(results)

    if args.baseline:
        metrics = write_baseline(results)
        print(f"  Baseline keys: {sorted(metrics)}")
        return 0

    all_pass = all(r.passed for r in results)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
