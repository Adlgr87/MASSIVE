"""
RNG utilities for MASSIVE.

Provides local, seedable generators for reproducible stochastic dynamics.
See also CLAUDE.md §8 (reproducibility).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

import numpy as np


def get_default_rng(seed: Optional[int] = None) -> np.random.Generator:
    """Return a NumPy Generator, optionally seeded.

    Args:
        seed: Optional integer seed. If None, entropy is drawn from OS.

    Returns:
        A ``numpy.random.Generator`` instance.
    """
    if seed is not None:
        return np.random.default_rng(seed)
    return np.random.default_rng()


def create_seed_sequence(seed: int, n_children: int) -> list[int]:
    """Spawn hierarchical child seeds from a parent seed.

    Args:
        seed: Parent seed.
        n_children: Number of independent child seeds.

    Returns:
        List of ``n_children`` integer seeds suitable for ``default_rng``.
    """
    if n_children < 0:
        raise ValueError("n_children must be >= 0")
    root = np.random.SeedSequence(seed)
    children = root.spawn(n_children)
    return [int(child.generate_state(1)[0]) for child in children]


@contextmanager
def with_rng(
    rng: Optional[np.random.Generator] = None,
    seed: Optional[int] = None,
) -> Iterator[np.random.Generator]:
    """Yield a temporary RNG for a code block.

    Args:
        rng: Existing generator to use as-is.
        seed: Seed used when ``rng`` is None.

    Yields:
        Generator to use inside the context.
    """
    if rng is not None:
        yield rng
    else:
        yield get_default_rng(seed)


def ensure_rng(
    rng: Optional[np.random.Generator] = None,
    seed: Optional[int] = None,
) -> np.random.Generator:
    """Return ``rng`` or create a new generator from ``seed``.

    Args:
        rng: Optional existing generator.
        seed: Optional seed when creating a new generator.

    Returns:
        A usable ``numpy.random.Generator``.
    """
    if rng is not None:
        return rng
    return get_default_rng(seed)
