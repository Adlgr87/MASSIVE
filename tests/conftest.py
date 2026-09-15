"""
tests/conftest.py — Shared fixtures and pytest hooks for MASSIVE test suite.

Provides:
  - Automatic skipping of test modules whose optional dependencies are missing
    (e.g. plotly for test_visualizations.py).
  - Common fixtures: numpy reproducible seed, CfC router singleton reset,
    and reusable engine/config helpers.
"""

from __future__ import annotations

import importlib.util

import numpy as np
import pytest

# ── Optional-dependency collection guards ─────────────────────────────────

# Map of dependency-module → test-file (relative to this conftest).
# If the dependency is unavailable the corresponding test module is skipped
# during collection (no ImportError crash).
_OPTIONAL_MODULES: dict[str, str] = {
    "plotly": "test_visualizations.py",
    "langchain": "test_integration_llm.py",
    "dask": "test_sparse_refactor.py",
}


def _dep_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


collect_ignore: list[str] = []
for _dep, _test_file in _OPTIONAL_MODULES.items():
    if not _dep_available(_dep):
        collect_ignore.append(_test_file)


# ── Pytest markers ────────────────────────────────────────────────────────


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "requires_torch: skip when PyTorch is not available",
    )
    config.addinivalue_line(
        "markers",
        "requires_plotly: skip when plotly is not available",
    )


def pytest_collection_modifyitems(config, items):
    """Auto-skip tests guarded by ``requires_torch`` / ``requires_plotly``."""
    torch_ok = _dep_available("torch")
    plotly_ok = _dep_available("plotly")

    skip_torch = pytest.mark.skip(reason="PyTorch no disponible")
    skip_plotly = pytest.mark.skip(reason="plotly no disponible")

    for item in items:
        if "requires_torch" in item.keywords and not torch_ok:
            item.add_marker(skip_torch)
        if "requires_plotly" in item.keywords and not plotly_ok:
            item.add_marker(skip_plotly)


# ── Shared fixtures ───────────────────────────────────────────────────────


@pytest.fixture
def reproducible_seed() -> int:
    """Seed NumPy's legacy RNG for deterministic test runs (fixed seed)."""
    np.random.seed(42)
    return 42


@pytest.fixture
def np_rng(reproducible_seed) -> np.random.RandomState:
    """Return a seeded ``RandomState`` for tests that need one."""
    return np.random.RandomState(reproducible_seed)


@pytest.fixture
def cfc_router():
    """Provide a fresh ``CfCRouter`` singleton, resetting it after the test."""
    from cfc_router import CfCRouter

    CfCRouter._instance = None
    router = CfCRouter()
    yield router
    CfCRouter._instance = None


@pytest.fixture
def bipolar_engine():
    """A ``SocialEnergyEngine`` configured for bipolar opinion dynamics."""
    from energy_engine import SocialEnergyEngine

    return SocialEnergyEngine(range_type="bipolar", temperature=0.0, lambda_social=0.5)


@pytest.fixture
def unipolar_engine():
    """A ``SocialEnergyEngine`` configured for unipolar opinion dynamics."""
    from energy_engine import SocialEnergyEngine

    return SocialEnergyEngine(range_type="unipolar", temperature=0.0, lambda_social=0.3)


@pytest.fixture
def sample_brexit_state():
    """Initial opinion state for a Brexit-style simulation (bipolar)."""
    return {
        "opinion": 0.5,
        "propaganda": 0.7,
        "confianza": 0.4,
        "opinion_grupo_a": 0.72,
        "opinion_grupo_b": 0.28,
        "pertenencia_grupo": 0.65,
    }
