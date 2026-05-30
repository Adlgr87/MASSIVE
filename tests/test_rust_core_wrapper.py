import numpy as np

from massive_core import rust_core


def test_langevin_opinion_update_wrapper_matches_numpy_formula():
    agents = np.array([[0.0, 0.2], [0.95, 0.4], [-0.95, 0.6]], dtype=np.float64)
    drift = np.array([1.0, 2.0, -2.0], dtype=np.float64)
    diffusion_noise = np.array([0.5, 0.5, -0.5], dtype=np.float64)
    jumps = np.array([0.0, 0.2, -0.2], dtype=np.float64)

    rust_core.langevin_opinion_update_inplace(
        agents,
        drift,
        diffusion_noise,
        jumps,
        dt=0.1,
        diffusion_sigma=0.2,
        x_min=-1.0,
        x_max=1.0,
    )

    expected = np.array([0.2, 1.0, -1.0])
    np.testing.assert_allclose(agents[:, 0], expected)
    np.testing.assert_allclose(agents[:, 1], [0.2, 0.4, 0.6])


def test_active_mask_step_reactivates_changed_neighbors():
    x_prev = np.zeros((3, 2), dtype=np.float64)
    x_new = x_prev.copy()
    x_new[1, 0] = 0.2
    adj = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 1.0],
            [0.0, 0.0, 0.0],
        ],
        dtype=np.float64,
    )

    active = rust_core.active_mask_step(x_prev, x_new, adj, threshold=0.1)

    np.testing.assert_array_equal(active, np.array([True, True, True]))


def test_multi_potential_gradient_wrapper_matches_reference_terms():
    x = np.array([[0.7, 0.6, 0.4, 0.5, 0.5]], dtype=np.float64)

    grad = rust_core.multi_potential_gradient(x)

    assert grad.shape == x.shape
    assert abs(grad[0, 0]) < 1e-12
    expected_coop = 2.0 * (0.6 - 0.8 * 0.85)
    assert np.isclose(grad[0, 1], expected_coop)
