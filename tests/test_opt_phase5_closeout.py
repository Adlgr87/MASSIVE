"""FASE 5 closeout tests: rate limit, logging, deprecations, services."""

from __future__ import annotations

import logging
import warnings
from pathlib import Path

import pytest

from massive_core.config import (
    InMemoryRateLimiter,
    FileRateLimiter,
    build_rate_limiter,
    clear_settings_cache,
    configure_logging,
    get_app_settings,
)
from services.simulation_service import run_scalar_simulation
from services.forecast_service import list_targets


def test_inmemory_rate_limiter_blocks():
    lim = InMemoryRateLimiter()
    assert lim.allow("a", 2) is True
    assert lim.allow("a", 2) is True
    assert lim.allow("a", 2) is False


def test_file_rate_limiter_shared(tmp_path: Path):
    path = tmp_path / "rl.json"
    a = FileRateLimiter(path)
    b = FileRateLimiter(path)
    assert a.allow("ip", 1) is True
    assert b.allow("ip", 1) is False


def test_build_rate_limiter_memory():
    lim = build_rate_limiter(backend="memory")
    assert isinstance(lim, InMemoryRateLimiter)


def test_configure_logging_with_file(tmp_path: Path):
    clear_settings_cache()
    log_path = tmp_path / "massive.log"
    configure_logging("INFO", force=True, log_file=str(log_path))
    log = logging.getLogger("massive.closeout")
    log.info("hello-closeout")
    # handler flush
    for h in logging.getLogger().handlers:
        h.flush()
    assert log_path.exists()
    assert "hello-closeout" in log_path.read_text(encoding="utf-8")


def test_app_settings_rate_limit_fields():
    clear_settings_cache()
    s = get_app_settings()
    assert s.rate_limit_backend in ("memory", "file")
    assert s.rate_limit_per_min >= 1


def test_root_schemas_emits_deprecation():
    import importlib
    import sys

    sys.modules.pop("schemas", None)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        importlib.import_module("schemas")
    assert any(issubclass(w.category, DeprecationWarning) for w in caught)


def test_simulation_service_seeded():
    out = run_scalar_simulation(
        {"opinion": 0.5, "propaganda": 0.0},
        pasos=5,
        config={"proveedor": "heurístico", "seed": 3},
    )
    assert "history" in out and len(out["history"]) == 6
    assert "summary" in out


def test_forecast_service_list_targets():
    targets = list_targets()
    assert isinstance(targets, list)
    assert targets
