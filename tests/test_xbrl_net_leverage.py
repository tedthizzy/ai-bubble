"""Regression cases for stale XBRL tag selection and fiscal-period alignment."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from xbrl_net_leverage import (
    INT_TAGS,
    ebitda_observation,
    latest_annual,
    total_debt_observation,
)


def fact(
    *, tag: str, value: float, end: str, start: str | None = None, filed: str | None = None
) -> tuple[str, dict]:
    row = {"val": value, "end": end, "filed": filed or end, "form": "10-K", "fp": "FY"}
    if start:
        row["start"] = start
    return tag, row


def companyfacts(*items: tuple[str, dict]) -> dict:
    tags: dict[str, dict] = {}
    for tag, row in items:
        tags.setdefault(tag, {"units": {"USD": []}})["units"]["USD"].append(row)
    return {"facts": {"us-gaap": tags}}


class XbrlSelectorTest(unittest.TestCase):
    def test_microsoft_debt_uses_latest_tag_across_candidates(self) -> None:
        facts = companyfacts(
            fact(tag="DebtLongtermAndShorttermCombinedAmount", value=1e9, end="2015-03-31"),
            fact(tag="LongTermDebt", value=6e9, end="2026-06-30"),
        )
        selected = total_debt_observation(facts)
        self.assertIsNotNone(selected)
        self.assertEqual(selected["value"], 6e9)
        self.assertEqual(selected["end"], "2026-06-30")

    def test_notes_payable_current_and_noncurrent_are_combined_only_at_same_date(self) -> None:
        facts = companyfacts(
            fact(tag="LongTermDebt", value=1e9, end="2022-05-31"),
            fact(tag="LongTermNotesPayable", value=5e9, end="2026-05-31"),
            fact(tag="NotesPayableCurrent", value=2e8, end="2026-05-31"),
        )
        selected = total_debt_observation(facts)
        self.assertIsNotNone(selected)
        self.assertEqual(selected["value"], 5.2e9)
        self.assertEqual(selected["end"], "2026-05-31")
        self.assertEqual(selected["tag"], "LongTermNotesPayable+NotesPayableCurrent")

    def test_nvidia_interest_uses_latest_annual_tag_and_ignores_quarter(self) -> None:
        facts = companyfacts(
            fact(tag="InterestExpense", value=1e8, start="2023-01-30", end="2024-01-28"),
            fact(tag="InterestExpenseDebt", value=2e8, start="2025-01-27", end="2026-01-25"),
            fact(tag="InterestExpenseDebt", value=9e8, start="2025-10-26", end="2026-01-25"),
        )
        self.assertEqual(latest_annual(facts, INT_TAGS), 2e8)

    def test_nvidia_current_nonoperating_interest_replaces_old_generic_tag(self) -> None:
        facts = companyfacts(
            fact(tag="InterestExpense", value=1e8, start="2023-01-30", end="2024-01-28"),
            fact(
                tag="InterestExpenseNonoperating",
                value=2.59e8,
                start="2025-01-27",
                end="2026-01-25",
            ),
        )
        self.assertEqual(latest_annual(facts, INT_TAGS), 2.59e8)

    def test_microsoft_explicit_depreciation_and_amortization_form_same_year_da(self) -> None:
        facts = companyfacts(
            fact(tag="OperatingIncomeLoss", value=155.237e9, start="2025-07-01", end="2026-06-30"),
            fact(tag="Depreciation", value=34.3e9, start="2025-07-01", end="2026-06-30"),
            fact(
                tag="AmortizationOfIntangibleAssets",
                value=4.7e9,
                start="2025-07-01",
                end="2026-06-30",
            ),
        )
        obs = ebitda_observation(facts)
        self.assertIsNotNone(obs)
        self.assertEqual(obs["value"], 194.237e9)
        self.assertEqual(obs["method"], "opinc+depreciation+intangible_amortization")

    def test_depreciation_without_amortization_cannot_stand_in_for_total_da(self) -> None:
        facts = companyfacts(
            fact(tag="OperatingIncomeLoss", value=3e9, start="2025-01-01", end="2025-12-31"),
            fact(tag="Depreciation", value=1e9, start="2025-01-01", end="2025-12-31"),
            fact(
                tag="AmortizationOfIntangibleAssets",
                value=1e8,
                start="2024-01-01",
                end="2024-12-31",
            ),
        )
        self.assertIsNone(ebitda_observation(facts))

    def test_net_income_ebitda_requires_tax_and_includes_da(self) -> None:
        base = [
            fact(tag="NetIncomeLoss", value=3e9, start="2025-01-01", end="2025-12-31"),
            fact(tag="InterestExpense", value=1e8, start="2025-01-01", end="2025-12-31"),
            fact(
                tag="DepreciationAndAmortization", value=2e8, start="2025-01-01", end="2025-12-31"
            ),
        ]
        self.assertIsNone(ebitda_observation(companyfacts(*base)))
        facts = companyfacts(
            *base,
            fact(tag="IncomeTaxExpenseBenefit", value=4e8, start="2025-01-01", end="2025-12-31"),
        )
        self.assertEqual(ebitda_observation(facts)["value"], 3.7e9)

    def test_ebitda_rejects_components_from_different_fiscal_years(self) -> None:
        facts = companyfacts(
            fact(tag="OperatingIncomeLoss", value=3e9, start="2025-01-01", end="2025-12-31"),
            fact(
                tag="DepreciationDepletionAndAmortization",
                value=1e9,
                start="2014-01-01",
                end="2014-12-31",
            ),
        )
        self.assertIsNone(ebitda_observation(facts))


if __name__ == "__main__":
    unittest.main()
