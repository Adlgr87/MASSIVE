#!/usr/bin/env python3
"""Run the gradual mypy slice for MASSIVE (FASE 2 + FASE 5 B4 packages).

Usage:
    python scripts/typecheck_slice.py
    python scripts/typecheck_slice.py --strict-sparse  # include sparse engine
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

DEFAULT_TARGETS = [
    "services",
    "massive_core/utils/rng.py",
    "forecast/targets.py",
    "massive_core/config",
    "massive_core/diagnostics",
    "massive_core/data_assimilation",
    "massive_core/analysis",
    "massive_core/physics",
    "massive_core/metalearning",
    "massive_core/numerics/steppers.py",
    "massive_core/numerics/solvers.py",
    "massive_core/numerics/stability.py",
    "massive_core/numerics/__init__.py",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict-sparse",
        action="store_true",
        help="Also type-check multilayer_engine_sparse.py",
    )
    args = parser.parse_args()

    targets = list(DEFAULT_TARGETS)
    if args.strict_sparse:
        targets.append("massive_core/numerics/multilayer_engine_sparse.py")

    cmd = [sys.executable, "-m", "mypy", *targets]
    print("Running:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=REPO)
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
