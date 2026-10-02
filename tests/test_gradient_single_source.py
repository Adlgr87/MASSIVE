"""The social potential gradient must have exactly one executable definition.

The audit found this law written out three times (the vectorized kernel, a
Python loop in ``multilayer_engine``, and the engine call sites). Three copies
means a change to the physics has to be made in three places, and nothing
fails if you only remember two.

``multilayer_engine.multi_potential_gradient`` now delegates to
``massive_core.kernels.multi_potential_gradient``. These tests pin that down:
if someone reintroduces a local implementation that drifts, they break here.
"""

from __future__ import annotations

import numpy as np
import pytest

from massive_core.kernels import multi_potential_gradient as kernel_grad
from multilayer_engine import _bimodal_grad
from multilayer_engine import multi_potential_gradient as engine_grad


def test_multilayer_delegates_to_the_shared_kernel():
    """Bit-for-bit, not approximately: it must be the same code path."""
    rng = np.random.default_rng(7)
    for _ in range(200):
        n = int(rng.integers(1, 60))
        x = rng.uniform(-1.0, 1.0, (n, 5))
        assert np.array_equal(engine_grad(x), kernel_grad(x))


def test_readable_scalar_helper_agrees_with_the_vectorized_column():
    """``_bimodal_grad`` is kept as the human-readable statement of the
    double-well law. It is only worth keeping if it cannot silently disagree
    with the column the engines actually integrate."""
    xs = np.linspace(-1.5, 1.5, 401)
    column = kernel_grad(np.column_stack([xs] + [np.zeros_like(xs)] * 4))[:, 0]
    scalar = np.array([_bimodal_grad(float(v)) for v in xs])
    assert np.array_equal(scalar, column)


@pytest.mark.parametrize("minimum", [0.7, -0.7])
def test_double_well_minima_are_where_the_docstring_says(minimum):
    """U = (x^2 - 0.49)^2 has stationary points at x = +/-0.7, the claim the
    engine's polarization behaviour rests on."""
    assert _bimodal_grad(minimum) == pytest.approx(0.0, abs=1e-12)


def test_gradient_pushes_away_from_the_unstable_centre():
    """x = 0 is also stationary but unstable; just off-centre the gradient must
    point outward, which is what produces the two opinion camps."""
    assert _bimodal_grad(0.1) < 0.0  # descending U pushes toward +0.7
    assert _bimodal_grad(-0.1) > 0.0  # and toward -0.7


def test_no_engine_reimplements_the_double_well():
    """Guard against a fourth copy appearing.

    The constant 0.49 (= 0.7^2) is this law's fingerprint. Docstrings may
    discuss it freely, so parse with ``ast`` and look only at numeric
    *literals* in executable code: an engine that hardcodes the well again has
    forked the physics.
    """
    import ast
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1]
    allowed = {"multilayer_engine.py"}  # the readable scalar helper
    offenders = set()
    for py in sorted(root.glob("*.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value == 0.49:
                offenders.add(py.name)
    assert offenders <= allowed, f"double-well reimplemented in: {offenders - allowed}"
