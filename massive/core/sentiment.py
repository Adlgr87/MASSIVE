"""Lightweight sentiment scoring for social text — no external deps.

Provides keyword-based sentiment scoring ([-1, 1] range) used by the
stance classification framework (`compare_arms.py`).

Score range: [-1, 1]
  - +1 = fully positive
  - -1 = fully negative
  -  0 = neutral / mixed
"""

from __future__ import annotations

import re

import numpy as np

_POSITIVE_WORDS = {
    "love",
    "great",
    "excellent",
    "good",
    "awesome",
    "best",
    "happy",
    "support",
    "agree",
    "yes",
    "win",
    "success",
    "positive",
    "amazing",
    "wonderful",
    "like",
    "thanks",
    "thank",
    "perfect",
    "brilliant",
    "hope",
    "trust",
    "unite",
    "peace",
    "bueno",
    "excelente",
    "amor",
    "apoya",
    "feliz",
    "genial",
    "gracias",
    "bien",
    "acuerdo",
    "progreso",
    "unidad",
    "paz",
    "confianza",
}
_NEGATIVE_WORDS = {
    "hate",
    "bad",
    "awful",
    "terrible",
    "worst",
    "corrupt",
    "lie",
    "liar",
    "fake",
    "no",
    "fail",
    "crisis",
    "wrong",
    "against",
    "reject",
    "disgrace",
    "fear",
    "angry",
    "sad",
    "unfair",
    "protest",
    "violence",
    "evil",
    "fraud",
    "scam",
    "malo",
    "odio",
    "corrupción",
    "mentira",
    "fraude",
    "miedo",
    "triste",
    "rechazo",
    "protesta",
    "violencia",
    "injusto",
}


def score_text(text: str) -> float:
    """Return a sentiment score in [-1, 1].

    Positive = +1, Negative = -1, Mixed/Neutral = 0.

    Keyword-based sentiment: count positive and negative keyword hits,
    return (pos - neg) / total.
    """
    words = re.findall(r"\w+", text.lower())
    pos = sum(1 for w in words if w in _POSITIVE_WORDS)
    neg = sum(1 for w in words if w in _NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0.0
    return float((pos - neg) / total)


def opinions_to_range(scores: np.ndarray, range_type: str = "bipolar") -> np.ndarray:
    """Convert [-1, 1] sentiment scores to the simulator's opinion range.

    - ``bipolar``: [-1, 1] unchanged.
    - ``unipolar``: mapped to [0, 1].
    """
    if range_type == "unipolar":
        return np.clip((scores + 1.0) / 2.0, 0.0, 1.0)
    return np.clip(scores, -1.0, 1.0)
