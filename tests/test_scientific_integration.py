import numpy as np

from energy_engine import SocialEnergyEngine
from massive_core.config import ScientificRuntimeConfig
from massive_core.numerics import EulerMaruyamaStepper, create_stepper
from multilayer_engine import COL_OPINION, MultilayerEngine


def test_runtime_config_defaults_keep_legacy_solver():
    cfg = ScientificRuntimeConfig.from_dict(None)

    assert cfg.solver == "legacy"
    assert cfg.enable_stability_diagnostics is False
    assert create_stepper(cfg.solver) is None
    assert isinstance(create_stepper("euler_maruyama"), EulerMaruyamaStepper)


def test_energy_engine_opt_in_euler_matches_legacy_deterministic_path():
    opinions = np.array([0.0, 0.5, -0.5], dtype=float)
    adj = np.array(
        [
            [0.0, 1.0, 0.0],
            [1.0, 0.0, 1.0],
            [0.0, 1.0, 0.0],
        ],
        dtype=float,
    )
    legacy = SocialEnergyEngine(range_type="bipolar", temperature=0.0, lambda_social=0.5)
    scientific = SocialEnergyEngine(
        range_type="bipolar",
        temperature=0.0,
        lambda_social=0.5,
        scientific_config={"solver": "euler_maruyama"},
    )

    legacy_next = legacy.step(opinions, adj, [], [], eta=0.01)
    scientific_next = scientific.step(opinions, adj, [], [], eta=0.01)

    np.testing.assert_allclose(scientific_next, legacy_next, atol=1e-12)
    assert scientific.last_numerical_diagnostics.method == "euler_maruyama"


def test_multilayer_engine_opt_in_euler_matches_legacy_without_noise():
    legacy = MultilayerEngine(N=12, seed=7, dt=0.01)
    scientific = MultilayerEngine(
        N=12,
        seed=7,
        dt=0.01,
        scientific_config={"solver": "euler_maruyama"},
    )
    legacy.theta[:] = 0.0
    scientific.theta[:] = 0.0

    legacy_next = legacy.step()
    scientific_next = scientific.step()

    np.testing.assert_allclose(scientific_next, legacy_next, atol=1e-12)
    assert np.all(scientific_next[:, COL_OPINION] >= -1.0)
    assert np.all(scientific_next[:, COL_OPINION] <= 1.0)
    assert scientific.last_numerical_diagnostics.method == "euler_maruyama"
