"""massive.cli — official MASSIVE command-line interface.

Usage::

    python -m massive.cli simulate --pasos 100 --seed 42
    python -m massive.cli benchmark --offline --seed 42
    python -m massive.cli serve --host 0.0.0.0 --port 8000
    python -m massive.cli version

Also installed as a console-script entry-point ``massive-cli`` (see
``pyproject.toml [project.scripts]``).
"""

from __future__ import annotations

from massive.cli.main import main

__all__ = ["main"]
