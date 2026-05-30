use ndarray::{Array1, Array2};
use numpy::{
    IntoPyArray, PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2, PyReadwriteArray2,
};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

const COL_OPINION: usize = 0;
const COL_COOP: usize = 1;
const COL_HIER: usize = 2;
const COL_INCOME: usize = 3;
const COL_INFO: usize = 4;

fn bimodal_grad(opinion: f64) -> f64 {
    4.0 * opinion * (opinion * opinion - 0.49)
}

fn compute_multi_potential_gradient(x: ndarray::ArrayView2<'_, f64>) -> Array2<f64> {
    let (n, kdim) = x.dim();
    let mut grad = Array2::<f64>::zeros((n, kdim));

    for i in 0..n {
        let op = x[[i, COL_OPINION]];
        grad[[i, COL_OPINION]] = bimodal_grad(op);

        if kdim > COL_COOP {
            let coop = x[[i, COL_COOP]];
            let align = 0.5 * (op + 1.0);
            grad[[i, COL_COOP]] = 2.0 * (coop - 0.8 * align);
        }
        if kdim > COL_HIER {
            let hier = x[[i, COL_HIER]];
            grad[[i, COL_HIER]] = -2.0 * hier * (1.0 - hier) * (2.0 * hier - 1.0);
        }
        if kdim > COL_INCOME {
            let inc = x[[i, COL_INCOME]];
            let hier = x[[i, COL_HIER]];
            grad[[i, COL_INCOME]] = 0.5 * (inc - 0.5) * (1.0 + hier);
        }
        if kdim > COL_INFO {
            let info = x[[i, COL_INFO]];
            let coop = x[[i, COL_COOP]];
            grad[[i, COL_INFO]] = 0.3 * (info - 0.5 - 0.2 * coop);
        }
    }

    grad
}

#[pyfunction]
fn multi_potential_gradient_rs<'py>(
    py: Python<'py>,
    x: PyReadonlyArray2<'_, f64>,
) -> PyResult<Bound<'py, PyArray2<f64>>> {
    let x_view = x.as_array();
    if x_view.ncols() == 0 {
        return Err(PyValueError::new_err("x must have at least one column"));
    }
    Ok(compute_multi_potential_gradient(x_view).into_pyarray(py))
}

#[pyfunction]
#[allow(clippy::too_many_arguments)]
fn langevin_opinion_update_inplace(
    mut agents: PyReadwriteArray2<'_, f64>,
    drift_vector: PyReadonlyArray1<'_, f64>,
    diffusion_noise: PyReadonlyArray1<'_, f64>,
    jump_values: PyReadonlyArray1<'_, f64>,
    dt: f64,
    diffusion_sigma: f64,
    x_min: f64,
    x_max: f64,
) -> PyResult<()> {
    let mut agents = agents.as_array_mut();
    let drift = drift_vector.as_array();
    let diffusion = diffusion_noise.as_array();
    let jumps = jump_values.as_array();
    let n = agents.nrows();

    if agents.ncols() == 0 {
        return Err(PyValueError::new_err(
            "agents must have at least one column",
        ));
    }
    if drift.len() != n || diffusion.len() != n || jumps.len() != n {
        return Err(PyValueError::new_err(
            "drift_vector, diffusion_noise and jump_values must match agents rows",
        ));
    }

    for i in 0..n {
        let updated =
            agents[[i, COL_OPINION]] + drift[i] * dt + diffusion_sigma * diffusion[i] + jumps[i];
        agents[[i, COL_OPINION]] = updated.clamp(x_min, x_max);
    }
    Ok(())
}

#[pyfunction]
fn active_mask_step_rs<'py>(
    py: Python<'py>,
    x_prev: PyReadonlyArray2<'_, f64>,
    x_new: PyReadonlyArray2<'_, f64>,
    adj: PyReadonlyArray2<'_, f64>,
    threshold: f64,
) -> PyResult<Bound<'py, PyArray1<bool>>> {
    let x_prev = x_prev.as_array();
    let x_new = x_new.as_array();
    let adj = adj.as_array();
    let (n, kdim) = x_prev.dim();

    if x_new.dim() != (n, kdim) {
        return Err(PyValueError::new_err("x_new must match x_prev shape"));
    }
    if adj.dim() != (n, n) {
        return Err(PyValueError::new_err("adj must have shape (N, N)"));
    }

    let mut changed = vec![false; n];
    for i in 0..n {
        let mut max_delta = 0.0_f64;
        for k in 0..kdim {
            max_delta = max_delta.max((x_new[[i, k]] - x_prev[[i, k]]).abs());
        }
        changed[i] = max_delta > threshold;
    }

    let mut active = changed.clone();
    for i in 0..n {
        if changed[i] {
            for j in 0..n {
                if adj[[i, j]] > 0.0 {
                    active[j] = true;
                }
            }
        }
    }

    Ok(Array1::from(active).into_pyarray(py))
}

#[pymodule]
fn massive_rust_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(multi_potential_gradient_rs, m)?)?;
    m.add_function(wrap_pyfunction!(langevin_opinion_update_inplace, m)?)?;
    m.add_function(wrap_pyfunction!(active_mask_step_rs, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use ndarray::array;

    #[test]
    fn gradient_matches_known_opinion_term() {
        let x = array![[0.7, 0.5, 0.5, 0.5, 0.5], [0.0, 0.5, 0.5, 0.5, 0.5]];
        let grad = compute_multi_potential_gradient(x.view());
        assert!(grad[[0, COL_OPINION]].abs() < 1e-12);
        assert!((grad[[1, COL_OPINION]] - 0.0).abs() < 1e-12);
    }
}
