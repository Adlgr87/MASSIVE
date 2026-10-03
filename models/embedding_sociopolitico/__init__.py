"""
MASSIVE — Socio-political embedding model package.

Provides a lightweight, deterministic Sentence-Transformers-style encoder
that projects Spanish/English sociopolitical text into the 5-dimensional
opinion parameter space used by the MASSIVE simulation engine.

Usage:
    from models.embedding_sociopolitico import SocioPoliticalEncoder

    encoder = SocioPoliticalEncoder(seed=42)
    embedding = encoder.encode("La izquierda defiende la igualdad social")
    # embedding → array([opinion, cooperation, hierarchy, income, info_access])
"""

from __future__ import annotations

from models.embedding_sociopolitico.encoder import (
    DEFAULT_SEED,
    DIMENSIONS,
    EMBED_DIM,
    PROJECTION_DIM,
    SENTIMENT_LEXICON,
    SocioPoliticalEncoder,
    get_default_encoder,
)

__all__ = [
    "SocioPoliticalEncoder",
    "get_default_encoder",
    "DIMENSIONS",
    "EMBED_DIM",
    "PROJECTION_DIM",
    "DEFAULT_SEED",
    "SENTIMENT_LEXICON",
]

__version__ = "1.0.0"
