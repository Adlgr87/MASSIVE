from ingest.normalize import bernoulli_variance, complement_difference, standard_deviation


METRIC_REGISTRY = {
    "bernoulli": bernoulli_variance,
    "complement": complement_difference,
    "std_dev": standard_deviation,
}


def compute_polarization(support, oppose, method="bernoulli", extra=None):
    fn = METRIC_REGISTRY.get(method, bernoulli_variance)
    if method == "std_dev" and extra is not None:
        return fn(extra)
    return fn(support, oppose)


def pick_method(episode_type):
    mapping = {
        "E1": "complement",
        "E2": "bernoulli",
        "E3": "complement",
        "E4": "bernoulli",
        "E5": "bernoulli",
        "E6": "complement",
    }
    return mapping.get(episode_type, "bernoulli")
