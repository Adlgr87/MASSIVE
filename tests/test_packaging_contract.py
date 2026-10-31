"""Packaging contract tests.

These pin the class of defect that reached ``main``: ``pyproject.toml`` declared a
``social_connectors`` py-module that had been deleted, so every downstream clone
and wheel carried an invalid packaging declaration. Nothing caught it because
setuptools only warns.

They also guard the opposite failure: a package glob that silently resolves to
nothing, which makes a module ship-invisible without any error.
"""

from __future__ import annotations

import importlib
import tomllib
from pathlib import Path

import pytest
from setuptools import find_packages

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"

# Modules that were deleted from the tree. Referencing them from Python code is a
# latent ImportError; they may still appear in CHANGELOG/archive docs.
REMOVED_MODULES = (
    "social_connectors",
    "mamba_engine",
    "energy_engine_pure",
    "rust_core",
    "opinion_sources",
)


@pytest.fixture(scope="module")
def pyproject() -> dict:
    with open(PYPROJECT, "rb") as fh:
        return tomllib.load(fh)


class TestPyModulesResolve:
    def test_every_py_module_exists(self, pyproject: dict):
        declared = pyproject["tool"]["setuptools"]["py-modules"]
        assert declared, "no py-modules declared"
        missing = [name for name in declared if not (REPO_ROOT / f"{name}.py").is_file()]
        assert not missing, (
            f"pyproject declares py-modules that do not exist: {missing}. "
            "setuptools only warns, so the wheel silently ships without them."
        )

    def test_every_py_module_is_importable(self, pyproject: dict):
        """A declared module must at least import in the repo environment."""
        failures = {}
        for name in pyproject["tool"]["setuptools"]["py-modules"]:
            try:
                importlib.import_module(name)
            except Exception as exc:  # noqa: BLE001 - reporting, not handling
                failures[name] = f"{type(exc).__name__}: {exc}"
        assert not failures, f"declared py-modules failed to import: {failures}"


class TestPackageGlobsResolve:
    def test_every_include_glob_matches_a_package(self, pyproject: dict):
        globs = pyproject["tool"]["setuptools"]["packages"]["find"]["include"]
        empty = [glob for glob in globs if not find_packages(where=str(REPO_ROOT), include=[glob])]
        assert not empty, (
            f"these include globs match no package: {empty}. "
            "A glob that resolves to nothing ships nothing, silently."
        )

    def test_console_scripts_targets_exist(self, pyproject: dict):
        scripts = pyproject["project"].get("scripts", {})
        assert scripts, "no console scripts declared"
        for name, target in scripts.items():
            module_path, _, attribute = target.partition(":")
            assert attribute, f"{name}: target {target!r} has no ':function' part"
            module = importlib.import_module(module_path)
            assert hasattr(module, attribute), f"{name}: {module_path} has no {attribute}"


class TestPackageDataExists:
    def test_declared_package_data_files_exist(self, pyproject: dict):
        package_data = pyproject["tool"]["setuptools"].get("package-data", {})
        missing = []
        for package, patterns in package_data.items():
            directory = REPO_ROOT / package.replace(".", "/")
            for pattern in patterns:
                if not list(directory.glob(pattern)):
                    missing.append(f"{package}:{pattern}")
        assert not missing, f"declared package-data not found: {missing}"


class TestNoRemovedModuleReferences:
    @pytest.mark.parametrize("removed", REMOVED_MODULES)
    def test_python_code_does_not_import_removed_module(self, removed: str):
        offenders = []
        for path in REPO_ROOT.rglob("*.py"):
            rel = path.relative_to(REPO_ROOT)
            if any(part in {".venv", "node_modules", "build", "site"} for part in rel.parts):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for needle in (f"import {removed}\n", f"import {removed} ", f"from {removed} import"):
                if needle in text:
                    offenders.append(str(rel))
                    break
        assert (
            not offenders
        ), f"Python code still imports the removed module {removed!r}: {offenders}"
