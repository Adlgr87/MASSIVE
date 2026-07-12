import numpy as np


def normalize_support_oppose(support, oppose, undecided=None):
    total_active = support + oppose
    if total_active == 0:
        return 0.0, 0.0
    sn = (support / total_active) * 100.0
    on = (oppose / total_active) * 100.0
    return round(sn, 4), round(on, 4)


def bernoulli_variance(support, oppose):
    p = support / 100.0
    q = oppose / 100.0
    return round(4.0 * p * q, 4)


def complement_difference(support, oppose):
    return round(1.0 - abs(support - oppose) / 100.0, 4)


def standard_deviation(values):
    return round(float(np.std(values)), 4)
