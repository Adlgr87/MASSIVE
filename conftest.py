"""
Root-level conftest.py for MASSIVE.

Handles pre-plugin-loading configuration so that ``pytest_configure`` and
fixtures in ``tests/conftest.py`` receive a clean environment.
"""

from __future__ import annotations

import sys
import types

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
