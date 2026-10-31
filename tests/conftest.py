"""
Root-level conftest.py for MASSIVE.

Handles pre-plugin-loading configuration so that ``pytest_configure`` and
fixtures in ``tests/conftest.py`` receive a clean environment.
"""

from __future__ import annotations

import sys
import types

import pytest

# ── Neutralise the broken libtmux pytest11 entry-point plugin ────────────
#
# ``libtmux`` registers itself as a pytest plugin via the ``pytest11`` entry
# point.  The installed version (0.39.0) is incompatible with pytest 9.x:
# its ``pytest_plugin.py`` applies ``@pytest.mark.skipif`` to a fixture
# function, which pytest 9.x forbids ("Marks cannot be applied to fixtures").
#
# Previously this was suppressed via ``addopts = "-p no:libtmux"``.  We now
# inject ``-p no:libtmux`` *programmatically* via ``pytest_load_initial_conftests``
# so that the project-level ``addopts`` stays clean.
#
# If the hook is not early enough, we also pre-empt the import by registering
# a placeholder module — when pytest's entry-point loader calls
# ``importlib.import_module("libtmux.pytest_plugin")`` it finds the stub in
# ``sys.modules`` and uses it instead of loading the broken real module.


def _install_libtmux_stub() -> None:
    if "libtmux.pytest_plugin" in sys.modules:
        return
    stub = types.ModuleType("libtmux.pytest_plugin")
    # Minimal no-op plugin so entry-point loading succeeds without side-effects.
    sys.modules["libtmux.pytest_plugin"] = stub


# Install the stub immediately on import — conftest.py runs early enough
# in pytest's startup to beat the entry-point plugin loader.
_install_libtmux_stub()


def pytest_load_initial_conftests(early_config, parser, args):
    """Disable the libtmux pytest plugin before it auto-loads.

    ``libtmux`` ships a ``pytest11`` entry-point plugin that is incompatible
    with pytest 9.x (it applies a mark to a fixture function).  Previously
    this was suppressed via ``addopts = "-p no:libtmux"``; we now inject the
    same directive programmatically so *addopts* stays clean.
    """
    try:
        idx = args.index("-p")
        if idx + 1 < len(args) and args[idx + 1] == "no:libtmux":
            return
    except ValueError:
        pass
    args.insert(0, "-p")
    args.insert(1, "no:libtmux")


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Emit a deterministic final-line summary.

    pytest 9.x suppresses the default terminal summary line ("X passed, Y
    skipped …") when ``-q`` is combined with non-TTY (piped) output, leaving
    the docs-link as ``tail -1`` instead.  CI scripts that pipe ``| tail -1``
    expect a pass/fail indicator, so we emit a concise one-line summary as the
    very last line of output.
    """
    stats = getattr(terminalreporter, "stats", {})
    failures = len(stats.get("failed", [])) + len(stats.get("error", []))
    terminalreporter.write_line(f"{failures} failed")


# ── Sealed-artefact protection ────────────────────────────────────────────────
#
# `configs/calibrated/pre_registration/*.yaml`, `datasets/ground_truth/splits.json`
# and `massive/core/_provenance_registry.json` are *evidence*: they record when
# a hypothesis and its thresholds were locked, i.e. before the data was seen.
#
# Before this guard existed, simply running the test suite re-stamped all of
# them (fresh `registered_at` / `sealed_at` on every run), so the seals were
# unable to prove anything. The guard below snapshots their bytes before the
# session and fails loudly if any of them changed.

_SEALED_ARTEFACT_GLOBS = (
    "configs/calibrated/pre_registration/*.yaml",
    "datasets/ground_truth/splits.json",
    "massive/core/_provenance_registry.json",
)


def _sealed_artefact_digests() -> dict[str, str]:
    """SHA-256 of every sealed artefact currently in the working tree."""
    import hashlib
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    digests: dict[str, str] = {}
    for pattern in _SEALED_ARTEFACT_GLOBS:
        for path in sorted(root.glob(pattern)):
            digests[str(path.relative_to(root))] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return digests


@pytest.fixture(scope="session", autouse=True)
def _isolate_mutable_artefacts(tmp_path_factory):
    """Redirect every mutable, versioned artefact to a temporary root.

    Tests legitimately exercise pre-registration, sealing and provenance with
    their own parameters (``n_agents=20``, ``ensemble_size=5``…). Writing those
    runs into the canonical files overwrote the real seals with test values on
    every test run. The three mutable artefacts therefore point at a temp copy
    for the whole session; the originals are restored on teardown.
    """
    import shutil
    from pathlib import Path

    import ground_truth._seals as seals_mod
    import massive.core.backtesting as bt_mod
    import massive.core.data_provenance as dp_mod

    root = Path(__file__).resolve().parent.parent
    tmp = tmp_path_factory.mktemp("artefacts")

    prereg_tmp = tmp / "pre_registration"
    registry_tmp = tmp / "_provenance_registry.json"
    splits_tmp = tmp / "splits.json"

    prereg_src = bt_mod._PREREG_DIR
    if prereg_src.is_dir():
        shutil.copytree(prereg_src, prereg_tmp, dirs_exist_ok=True)
    if dp_mod._REGISTRY_PATH.exists():
        shutil.copy2(dp_mod._REGISTRY_PATH, registry_tmp)
    if seals_mod.SPLITS_PATH.exists():
        shutil.copy2(seals_mod.SPLITS_PATH, splits_tmp)

    originals = (bt_mod._PREREG_DIR, dp_mod._REGISTRY_PATH, seals_mod.SPLITS_PATH)
    bt_mod._PREREG_DIR = prereg_tmp
    dp_mod._REGISTRY_PATH = registry_tmp
    seals_mod.SPLITS_PATH = splits_tmp
    dp_mod._reset_registry_cache()
    try:
        yield
    finally:
        bt_mod._PREREG_DIR, dp_mod._REGISTRY_PATH, seals_mod.SPLITS_PATH = originals
        dp_mod._reset_registry_cache()


@pytest.fixture(scope="session", autouse=True)
def _protect_sealed_artefacts():
    """Fail the session if any sealed artefact was mutated by the tests."""
    before = _sealed_artefact_digests()
    yield
    after = _sealed_artefact_digests()

    mutated = sorted(
        name
        for name in before.keys() | after.keys()
        if before.get(name) != after.get(name)
    )
    if mutated:
        raise AssertionError(
            "The test suite mutated sealed artefacts (pre-registration seals must "
            "be immutable once written):\n  "
            + "\n  ".join(mutated)
            + "\n\nRegister/seal into a temporary directory instead — pass "
            "`prereg_dir=` / `registry_path=` / `splits_path=`."
        )
