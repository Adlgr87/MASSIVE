"""@deprecated — re-export only. Use massive.core.extended_models directly."""

from massive.core.extended_models import (  # noqa: F401
    regla_bayesiana,
    regla_nash,
    regla_sir,
)

__all__ = ["regla_nash", "regla_bayesiana", "regla_sir"]
