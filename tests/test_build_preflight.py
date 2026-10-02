"""Tests for the static Docker/Rust build preflight.

The preflight exists because `docker compose build` and `cargo build` cannot
run in every environment. These tests check it actually *detects* the three
defects it was written for — a checker that always passes is worthless.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_build_preflight.py"


def _run(cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(cwd / "scripts" / "verify_build_preflight.py")],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def repo_copy(tmp_path: Path) -> Path:
    """A minimal copy of the build-relevant files, safe to mutate."""
    dest = tmp_path / "repo"
    (dest / "scripts").mkdir(parents=True)
    (dest / "rust_core" / "src").mkdir(parents=True)
    (dest / "backend" / "app").mkdir(parents=True)
    (dest / "massive_core").mkdir(parents=True)
    (dest / "frontend").mkdir(parents=True)

    shutil.copy(SCRIPT, dest / "scripts" / SCRIPT.name)
    for rel in (
        "Dockerfile",
        "docker-compose.yml",
        "nginx.conf",
        "supervisord.conf",
        ".dockerignore",
        "requirements.txt",
        "rust_core/Cargo.toml",
        "rust_core/src/lib.rs",
        "massive_core/rust_core.py",
    ):
        src = ROOT / rel
        if src.exists():
            shutil.copy(src, dest / rel)
    (dest / "backend" / "app" / "main.py").write_text("app = None\n")
    for name in ("package.json", "package-lock.json"):
        shutil.copy(ROOT / "frontend" / name, dest / "frontend" / name)
    (dest / ".env").write_text("MASSIVE_API_KEY=x\n")
    return dest


def test_repository_passes_preflight():
    """The real repo must be ready to build."""
    result = _run(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_detects_command_without_its_apt_package(repo_copy: Path):
    dockerfile = repo_copy / "Dockerfile"
    dockerfile.write_text(dockerfile.read_text().replace("libcap2-bin nginx", "nginx"))
    result = _run(repo_copy)
    assert result.returncode == 1
    assert "setcap" in result.stdout and "libcap2-bin" in result.stdout


def test_detects_copy_source_missing_from_context(repo_copy: Path):
    """This is exactly finding C-09: nginx.conf outside the build context."""
    (repo_copy / "nginx.conf").unlink()
    result = _run(repo_copy)
    assert result.returncode == 1
    assert "nginx.conf" in result.stdout


def test_detects_unresolvable_cargo_lib_path(repo_copy: Path):
    manifest = repo_copy / "rust_core" / "Cargo.toml"
    manifest.write_text(
        manifest.read_text().replace('path = "src/lib.rs"', 'path = "rust_core/src/lib.rs"')
    )
    result = _run(repo_copy)
    assert result.returncode == 1
    assert "[lib] path" in result.stdout


def test_detects_copy_source_excluded_by_dockerignore(repo_copy: Path):
    ignore = repo_copy / ".dockerignore"
    ignore.write_text(ignore.read_text() + "\nnginx.conf\n")
    result = _run(repo_copy)
    assert result.returncode == 1
    assert "dockerignore" in result.stdout.lower()
