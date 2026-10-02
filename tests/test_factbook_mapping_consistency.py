"""Guards that the descriptive FACTBOOK_TO_MASSIVE table matches live code.

``FACTBOOK_TO_MASSIVE`` is documentation stored as data: nothing executes it.
That is exactly why it drifted — its ``budget_balance`` entry documented a
sign-only transformation that scored a deficit (1.0) *higher* than a surplus
(0.9), the opposite of the implementation in ``CountryData``.

These tests pin the directional claims the table makes, so documentation and
behaviour cannot silently disagree again.
"""

from __future__ import annotations

import pytest

from massive.core.factbook.context import CountryData
from massive.core.factbook.mappings import (
    FACTBOOK_TO_MASSIVE,
    diversity_index,
    herfindahl_index,
)


def _context(**overrides) -> CountryData:
    """Build a CountryData whose derived params are recomputed on init."""
    base: dict = {"budget_revenues": 100.0}
    base.update(overrides)
    return CountryData(**base)


class TestFiscalConstraint:
    """The table and the implementation must agree on direction."""

    def test_surplus_scores_above_balanced_above_deficit(self):
        surplus = _context(budget_surplus_deficit=20.0)
        balanced = _context(budget_surplus_deficit=0.0)
        deficit = _context(budget_surplus_deficit=-20.0)

        s = surplus.massive_params["fiscal_constraint"]
        b = balanced.massive_params["fiscal_constraint"]
        d = deficit.massive_params["fiscal_constraint"]

        assert d < b < s, f"fiscal capacity not monotonic: deficit={d}, balanced={b}, surplus={s}"
        assert b == pytest.approx(0.5)

    def test_magnitude_matters_not_just_sign(self):
        """The old documented lambda depended only on sign; this must not."""
        small = _context(budget_surplus_deficit=-5.0).massive_params["fiscal_constraint"]
        large = _context(budget_surplus_deficit=-40.0).massive_params["fiscal_constraint"]
        assert large < small

    def test_table_entry_describes_a_ratio_not_a_sign(self):
        entry = FACTBOOK_TO_MASSIVE["intervention_optimizer"]["budget_balance"]
        transformation = entry["transformation"]
        assert "revenues" in transformation, "fiscal mapping must be relative to revenues"
        assert "x / abs(x)" not in transformation, "sign-only transformation is inverted"


class TestSocialPressureMapping:
    """The table says `herfindahl_index`; verify the live code agrees.

    (The audit flagged this as a contradiction; it is not one — the live
    `1 - diversity_index` is algebraically the Herfindahl index. Pinned here
    so the equivalence is not broken by accident.)
    """

    def test_weight_equals_herfindahl(self):
        groups = {"a": 60.0, "b": 30.0, "c": 10.0}
        ctx = _context(ethnic_groups=groups)
        weight = ctx.massive_params["social_pressure_weights"]["ethnic"]
        assert weight == pytest.approx(herfindahl_index(groups))
        assert weight == pytest.approx(1.0 - diversity_index(groups))

    def test_absent_data_is_neutral_not_maximal(self):
        ctx = _context()
        weights = ctx.massive_params["social_pressure_weights"]
        for key in ("ethnic", "religious", "language"):
            assert weights[key] == pytest.approx(0.5), (
                f"{key}: missing data must map to the neutral 0.5, not to maximum pressure"
            )
