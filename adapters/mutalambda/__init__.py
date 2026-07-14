"""MutaLambda integration surface for MASSIVE."""

from adapters.mutalambda.massive_target import (
    MassiveTargetManifest,
    evaluate_massive_vector,
    make_objective,
)

__all__ = [
    "MassiveTargetManifest",
    "evaluate_massive_vector",
    "make_objective",
]
