import numpy as np

from massive_core import (
    build_cfc_regime_dataset_from_history,
    run_canonical_benchmarks,
    run_energy_scientific_simulation,
    run_multilayer_scientific_simulation,
)
from massive_core.benchmarks import stable_fixed_point_benchmark
from massive_core.metalearning import build_cfc_regime_dataset_from_histories


def test_canonical_benchmarks_pass_without_empirical_data():
    result = run_canonical_benchmarks()

    assert result["passed"] is True
    assert len(result["benchmarks"]) == 4
    assert stable_fixed_point_benchmark()["passed"] is True


def test_engine_scientific_runners_return_reports_and_diagnostics():
    energy = run_energy_scientific_simulation(
        opinions=np.array([0.0, 0.2, -0.2]),
        adj=np.eye(3),
        steps=3,
        temperature=0.0,
        scientific_config={"solver": "euler_maruyama", "enable_scientific_report": True},
    )
    multilayer = run_multilayer_scientific_simulation(
        steps=2,
        N=6,
        seed=4,
        scientific_config={"solver": "euler_maruyama", "enable_scientific_report": True},
    )

    assert energy.scientific_report is not None
    assert len(energy.numerical_diagnostics) == 3
    assert energy.numerical_diagnostics[-1]["method"] == "euler_maruyama"
    assert multilayer.scientific_report is not None
    assert len(multilayer.numerical_diagnostics) == 2
    assert multilayer.to_dict()["scientific_report"] is not None


def test_cfc_training_dataset_from_histories_matches_selector_shapes():
    history = []
    for step in range(8):
        history.append(
            {
                "opinion": 0.1 * step,
                "propaganda": 0.7,
                "confianza": 0.4,
                "opinion_grupo_a": 0.8,
                "opinion_grupo_b": 0.2,
                "pertenencia_grupo": 0.6,
                "_regla": step % 3,
            }
        )

    dataset = build_cfc_regime_dataset_from_history(history, window_size=3)
    combined = build_cfc_regime_dataset_from_histories([history, history], window_size=3)

    assert dataset.X_hist.shape == (5, 3)
    assert dataset.X_state.shape == (5, 8)
    assert dataset.y_regime.tolist() == [0, 1, 2, 0, 1]
    assert combined.X_hist.shape == (10, 3)
    assert combined.to_dict()["y_regime"][0] == 0
