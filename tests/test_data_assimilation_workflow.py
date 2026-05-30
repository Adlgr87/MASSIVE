import numpy as np

from massive_core import run_scientific_simulation
from massive_core.data_assimilation import AssimilationResult, assimilate_history_observations


def test_assimilate_history_observations_moves_final_mean_toward_observation():
    history = [
        {"opinion": 0.0},
        {"opinion": 0.1},
        {"opinion": 0.2},
    ]

    result = assimilate_history_observations(
        history,
        observations={2: 1.0},
        observation_variance=1e-6,
        n_ensemble=20,
        ensemble_spread=0.0,
        seed=1,
    )

    assert isinstance(result, AssimilationResult)
    assert result.assimilated_mean.shape == (3, 1)
    assert result.observation_steps == [2]
    assert abs(result.assimilated_mean[-1, 0] - 1.0) < abs(0.2 - 1.0)
    assert result.to_dict()["observation_steps"] == [2]


def test_scientific_runner_adds_assimilation_only_when_enabled():
    base_state = {
        "opinion": 0.5,
        "propaganda": 0.7,
        "confianza": 0.4,
        "opinion_grupo_a": 0.72,
        "opinion_grupo_b": 0.28,
        "pertenencia_grupo": 0.65,
    }
    np.random.seed(3)

    disabled = run_scientific_simulation(
        base_state,
        pasos=4,
        cada_n_pasos=2,
        config={"proveedor": "heurístico"},
        observations={4: 0.9},
        verbose=False,
    )
    enabled = run_scientific_simulation(
        base_state,
        pasos=4,
        cada_n_pasos=2,
        config={"proveedor": "heurístico"},
        scientific_config={"enable_data_assimilation": True},
        observations={4: 0.9},
        verbose=False,
    )

    assert disabled.assimilation_result is None
    assert enabled.assimilation_result is not None
    assert enabled.to_dict()["assimilation_result"]["observation_steps"] == [4]
