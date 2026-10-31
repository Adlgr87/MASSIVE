"""Tests for ``massive/core/sentiment.py``.

This module backs the stance-classification arm in ``compare_arms.py`` and had
**zero** test coverage, despite that comparison framework being the mechanism used
to choose between competing implementations. Its scoring silently determines
which arm "wins", so its contract needs to be pinned.
"""

from __future__ import annotations

import numpy as np
import pytest

from massive.core.sentiment import opinions_to_range, score_text


class TestScoreText:
    @pytest.mark.parametrize(
        "text",
        [
            "this is great",
            "excellent work, thanks",
            "I support this and I am happy",
            "love it, best decision, brilliant",
        ],
    )
    def test_positive_text_scores_positive(self, text: str):
        assert score_text(text) > 0

    @pytest.mark.parametrize(
        "text",
        [
            "this is terrible",
            "awful and wrong",
            "I hate this, worst decision",
            "fraud and violence",
            "una mentira, injusto",
        ],
    )
    def test_negative_text_scores_negative(self, text: str):
        assert score_text(text) < 0

    @pytest.mark.parametrize("text", ["", "the table is brown", "12345", "???"])
    def test_text_without_sentiment_words_is_neutral(self, text: str):
        assert score_text(text) == 0.0

    def test_mixed_sentiment_scores_lower_than_pure(self):
        """A mixed sentence must score below the same sentence made purely positive."""
        mixed = score_text("great but terrible")
        pure = score_text("great great")
        assert 0 <= mixed < pure

    def test_score_is_bounded(self):
        for text in ("great", "terrible", "great terrible", ""):
            assert -1.0 <= score_text(text) <= 1.0

    def test_case_and_punctuation_insensitive(self):
        assert score_text("GREAT!") == score_text("great")
        assert score_text("Great, wonderful.") == score_text("great wonderful")

    def test_repeated_hits_saturate_not_explode(self):
        """Repetition must not push the score outside [-1, 1]."""
        assert score_text("great " * 100) == pytest.approx(1.0)

    def test_lexicon_is_bilingual(self):
        """The lexicon must cover Spanish as well as English.

        MASSIVE backtests Spanish-language mobilisations (15M, estallido), so an
        English-only lexicon would silently score those cases as neutral.
        """
        assert score_text("excelente y bueno") > 0
        assert score_text("corrupción y mentira") < 0

    @pytest.mark.xfail(
        reason="Known limitation: the lexicon is a 73-word keyword list, so unseen "
        "sentiment words score 0. Documented here instead of silently accepted.",
        strict=True,
    )
    def test_documented_lexicon_gap(self):
        assert score_text("this is a disaster") < 0


class TestOpinionsToRange:
    def test_bipolar_is_identity_within_bounds(self):
        scores = np.array([-1.0, -0.25, 0.0, 0.5, 1.0])
        np.testing.assert_allclose(opinions_to_range(scores), scores)

    def test_bipolar_clips_out_of_range(self):
        scores = np.array([-3.0, 3.0])
        np.testing.assert_allclose(opinions_to_range(scores), np.array([-1.0, 1.0]))

    def test_unipolar_maps_minus_one_to_zero_and_one_to_one(self):
        scores = np.array([-1.0, 0.0, 1.0])
        np.testing.assert_allclose(opinions_to_range(scores, "unipolar"), np.array([0.0, 0.5, 1.0]))

    def test_unipolar_stays_within_zero_one(self):
        scores = np.array([-10.0, -1.0, 0.0, 1.0, 10.0])
        result = opinions_to_range(scores, "unipolar")
        assert result.min() >= 0.0
        assert result.max() <= 1.0

    def test_unknown_range_type_falls_back_to_bipolar(self):
        scores = np.array([-0.5, 0.5])
        np.testing.assert_allclose(opinions_to_range(scores, "not-a-range"), scores)
