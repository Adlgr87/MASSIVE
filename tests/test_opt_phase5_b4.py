"""FASE 5 B4 — type-hint slice smoke tests.

Full mypy gate: ``python scripts/typecheck_slice.py`` (not in default pytest —
~1 min and environment-sensitive).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from massive_core.data_assimilation.kalman import SparseEnsembleKalmanFilter
from massive_core.numerics.solvers import AdaptiveODESolver
from massive_core.numerics.stability import SparseStabilityAnalyzer


REPO = Path(__file__).resolve().parents[1]


def test_typecheck_slice_script_exists():
    script = REPO / "scripts" / "typecheck_slice.py"
    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    assert "massive_core/numerics/steppers.py" in text
    assert "disallow_untyped" not in text  # policy lives in mypy.ini
    mypy_ini = REPO / "mypy.ini"
    assert "massive_core.numerics" in mypy_ini.read_text(encoding="utf-8")


def test_sparse_enkf_local_rng_typed_predict():
    enkf = SparseEnsembleKalmanFilter(
        n_ensemble=4,
        n_state_dim=3,
        n_obs_dim=1,
        observable_indices=[0],
        observation_covariance=np.eye(1) * 0.1,
        rng=np.random.default_rng(11),
    )

    def model(x: np.ndarray) -> np.ndarray:
        return 0.9 * x

    out = enkf.predict(model)
    assert out.shape == (4, 3)


def test_sparse_stability_analyzer_signatures():
    def field(x: np.ndarray) -> np.ndarray:
        return -x

    analyzer = SparseStabilityAnalyzer(system_fn=field)
    report = analyzer.analyze_linear_stability(np.array([0.1, -0.2]))
    assert report.stable in (True, False)
    assert analyzer.compute_spectral_radius(np.eye(2)).__class__ is float


def test_adaptive_solver_diffusion_callable():
    def drift(x: np.ndarray) -> np.ndarray:
        return -0.1 * x

    def diffusion(x: np.ndarray) -> np.ndarray:
        return 0.05 * np.ones_like(x)

    solver = AdaptiveODESolver(drift=drift, diffusion=diffusion, rng=np.random.default_rng(0))
    x1, dt = solver.step(np.array([1.0, 0.5]), 0.01)
    assert x1.shape == (2,)
    assert dt > 0
