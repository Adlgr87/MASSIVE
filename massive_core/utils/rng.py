"""
RNG Utilities for MASSIVE

This module provides utilities for random number generation with reproducibility.
Following CLAUDE.md Section 8: Reproducibility requirements.

Functions:
    get_default_rng: Get default RNG with optional seed
    create_seed_sequence: Create hierarchical seed sequence
    with_rng: Context manager for temporary RNG
"""

from contextlib import contextmanager
from typing import Optional, Generator, Any
import numpy as np


def get_default_rng(seed: Optional[int] = None) -> np.random.Generator:
    """
    Get a default random number generator.
    
    Args:
        seed: Optional seed for reproducibility
        
    Returns:
        Random number generator
        
    Example:
        >>> rng = get_default_rng(42)
        >>> rng.random()
        0.37454011884736254
    """
    if seed is not None:
        return np.random.default_rng(seed)
    return np.random.default_rng()


def create_seed_sequence(seed: int, n_children: int) -> list:
    """
    Create a hierarchical seed sequence.
    
    This function creates a sequence of seeds derived from a parent seed,
    ensuring that each child seed is unique but reproducible.
    
    Following CLAUDE.md §8.2: "Seeds jerárquicos para cada caso"
    
    Args:
        seed: Parent seed
        n_children: Number of child seeds to generate
        
    Returns:
        List of child seeds
        
    Example:
        >>> seeds = create_seed_sequence(42, 5)
        >>> len(seeds)
        5
    """
    root = np.random.SeedSequence(seed)
    children = root.spawn(n_children)
    return [child.entropy for child in children]


@contextmanager
def with_rng(rng: Optional[np.random.Generator] = None, seed: Optional[int] = None):
    """
    Context manager for temporary RNG.
    
    This allows temporarily switching to a different RNG for a block of code.
    
    Args:
        rng: RNG to use (if None, creates new one from seed)
        seed: Seed to use if rng is None
        
    Yields:
        RNG to use in the context
        
    Example:
        >>> with with_rng(seed=42) as rng:
        ...     value = rng.random()
        >>> value
        0.37454011884736254
    """
    if rng is not None:
        yield rng
    else:
        if seed is not None:
            rng = np.random.default_rng(seed)
        else:
            rng = np.random.default_rng()
        try:
            yield rng
        finally:
            pass  # RNG is not stateful, no cleanup needed


def ensure_rng(rng: Optional[np.random.Generator] = None, seed: Optional[int] = None) -> np.random.Generator:
    """
    Ensure an RNG is available.
    
    This is a helper function that returns the provided RNG, or creates a new one
    if None is provided.
    
    Args:
        rng: Optional RNG
        seed: Optional seed if rng is None
        
    Returns:
        RNG (either the provided one or a new one)
        
    Example:
        >>> rng = ensure_rng(seed=42)
        >>> rng.random()
        0.37454011884736254
    """
    if rng is not None:
        return rng
    if seed is not None:
        return np.random.default_rng(seed)
    return np.random.default_rng()
