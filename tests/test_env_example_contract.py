"""`.env.example` must describe reality.

A sweep found 15 variables documented there that no code read: setting
MASSIVE_LOG_LEVEL or MASSIVE_LLM_TIMEOUT_SECONDS did nothing at all, with no
warning. Some were then wired up; the rest are tagged [NOT YET READ BY CODE].

This test keeps both halves honest in both directions:
  * an untagged variable must actually be read somewhere, and
  * a tagged one must not be — otherwise the tag is now a lie.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = ROOT / ".env.example"
TAG = "[NOT YET READ BY CODE]"

# Searched in code only: docs mentioning a variable prove nothing about
# whether it is honoured.
CODE_GLOBS = ("*.py",)
SKIP_DIRS = {".venv", "node_modules", ".git", "docs", "tests", "__pycache__", "site"}


def _declared() -> dict[str, bool]:
    """Map variable name -> is it tagged as not implemented."""
    declared: dict[str, bool] = {}
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Z_0-9]+)=", line)
        if match:
            declared[match.group(1)] = TAG in line
    return declared


def _is_read_by_code(name: str) -> bool:
    """True when the variable name appears in a Python source file."""
    result = subprocess.run(
        ["grep", "-rl", "--include=*.py", name, str(ROOT)],
        capture_output=True,
        text=True,
    )
    for path in result.stdout.splitlines():
        rel = Path(path).relative_to(ROOT)
        if not any(part in SKIP_DIRS for part in rel.parts):
            return True
    return False


def test_env_example_declares_variables():
    assert _declared(), ".env.example parsed as empty — the regex or file moved"


def test_untagged_variables_are_actually_read():
    """If it is documented without a caveat, the code must honour it."""
    missing = [
        name for name, tagged in _declared().items() if not tagged and not _is_read_by_code(name)
    ]
    assert not missing, (
        "documented in .env.example but read by no code — either wire them up "
        f"or tag them {TAG}: {sorted(missing)}"
    )


def test_tagged_variables_are_genuinely_unimplemented():
    """The reverse: a stale tag understates what the project supports."""
    stale = [name for name, tagged in _declared().items() if tagged and _is_read_by_code(name)]
    assert not stale, f"tagged {TAG} but the code does read them — remove the tag: {sorted(stale)}"


def test_social_credentials_are_wired():
    """These three shipped unread for a long time; they now drive
    `massive_core.opinion_sources`. Pin that so they cannot silently regress
    back into decoration."""
    declared = _declared()
    for name in ("TWITTER_BEARER_TOKEN", "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"):
        assert name in declared, f"{name} vanished from .env.example"
        assert not declared[name], f"{name} is wired but tagged as unimplemented"
        assert _is_read_by_code(name)


def test_both_api_key_variables_are_read():
    """MASSIVE_API_KEYS was documented for rotation but never read."""
    for name in ("MASSIVE_API_KEY", "MASSIVE_API_KEYS"):
        assert _is_read_by_code(name), f"{name} is documented but no code reads it"
