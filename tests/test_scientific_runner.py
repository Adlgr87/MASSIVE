import numpy as np

from massive_core import ScientificSimulationResult, run_scientific_simulation
from massive_core.config import ScientificRuntimeConfig


BASE_STATE = {
    "opinion": 0.5,
    "propaganda": 0.7,
    "confianza": 0.4,
    "opinion_grupo_a": 0.72,
    "opinion_grupo_b": 0.28,
    "pertenencia_grupo": 0.65,
}


def test_scientific_runner_keeps_report_disabled_by_default():
    np.random.seed(0)

    result = run_scientific_simulation(
        BASE_STATE,
        pasos=5,
        cada_n_pasos=2,
        config={"proveedor": "heurístico"},
        verbose=False,
    )

    assert isinstance(result, ScientificSimulationResult)
    assert len(result.history) == 6
    assert result.summary["pasos"] == 5
    assert result.scientific_report is None
    assert result.to_dict()["scientific_report"] is None


def test_scientific_runner_adds_serializable_report_when_enabled():
    np.random.seed(1)

    result = run_scientific_simulation(
        BASE_STATE,
        pasos=6,
        cada_n_pasos=2,
        config={"proveedor": "heurístico", "dt": 0.5},
        scientific_config={"enable_scientific_report": True},
        verbose=False,
    )
    payload = result.to_dict()

    assert result.scientific_report is not None
    assert payload["scientific_report"]["n_steps"] == 6
    assert payload["scientific_report"]["state_dim"] == 1
    assert payload["scientific_config"]["enable_scientific_report"] is True
    assert "spectral_radius" in payload["scientific_report"]


def test_scientific_runner_accepts_runtime_config_object():
    np.random.seed(2)
    cfg = ScientificRuntimeConfig(enable_scientific_report=True)

    result = run_scientific_simulation(
        BASE_STATE,
        pasos=3,
        cada_n_pasos=1,
        config={"proveedor": "heurístico"},
        scientific_config=cfg,
        verbose=False,
    )

    assert result.scientific_config is cfg
    assert result.scientific_report is not None
