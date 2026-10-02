"""CLI entry point for generating Ground Truth Layer 1 artefacts.

Usage::

    python -m ground_truth
"""

from __future__ import annotations

from ground_truth._generate import generate_all

if __name__ == "__main__":
    result = generate_all()
    print("\nGenerated artefacts:")
    for key, path in result.items():
        if isinstance(path, list):
            for p in path:
                print(f"  {key}: {p}")
        else:
            print(f"  {key}: {path}")
