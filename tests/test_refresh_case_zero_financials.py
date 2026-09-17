"""Guard the date alignment used by the keyless September SEC financial snapshot."""

from __future__ import annotations

import unittest
from datetime import date

from scripts.refresh_case_zero_financials import current_liquidity, fact_rows


def observation(value: int, start: str | None, end: str) -> dict:
    return {"value_usd": value, "start": start, "end": end}


def liquidity_facts(report_end: str) -> dict:
    return {
        "cash": observation(500, None, report_end),
        "remaining_fiscal_year_principal_schedule": observation(100, None, report_end),
        "first_full_year_principal_schedule": observation(200, None, report_end),
        "operating_cash_flow": {
            "quarter": observation(300, "2026-04-01", report_end),
            "year_to_date": None,
            "annual": None,
        },
        "cash_capex": {
            "quarter": None,
            "year_to_date": observation(250, "2026-01-01", report_end),
            "annual": None,
        },
    }


class FinancialSnapshotAlignmentTest(unittest.TestCase):
    def test_future_filing_cannot_restate_as_of_snapshot(self) -> None:
        companyfacts = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {
                                    "val": 100,
                                    "start": "2026-04-01",
                                    "end": "2026-06-30",
                                    "filed": "2026-08-01",
                                    "form": "10-Q",
                                    "accn": "old",
                                },
                                {
                                    "val": 999,
                                    "start": "2026-04-01",
                                    "end": "2026-06-30",
                                    "filed": "2026-09-17",
                                    "form": "10-Q/A",
                                    "accn": "future",
                                },
                            ]
                        }
                    }
                }
            }
        }
        rows = fact_rows(companyfacts, (("us-gaap", "Revenues"),), date(2026, 9, 16))
        self.assertEqual([row["value_usd"] for row in rows], [100])

    def test_cash_flow_spans_must_match_exactly(self) -> None:
        facts = liquidity_facts("2026-06-30")
        result = current_liquidity("CRWV", facts, {}, "2026-06-30")
        self.assertIsNone(result["cash_after_capex"])
        self.assertEqual(result["operating_cash_flow"]["value_usd"], 300)
        self.assertEqual(result["cash_capex"]["value_usd"], 250)

        facts["cash_capex"]["quarter"] = observation(250, "2026-04-01", "2026-06-30")
        derived = {
            "quarter_cash_after_capex": observation(50, "2026-04-01", "2026-06-30")
        }
        result = current_liquidity("CRWV", facts, derived, "2026-06-30")
        self.assertEqual(result["cash_after_capex"]["value_usd"], 50)
        self.assertEqual(result["cash_flow_span"], "quarter")

    def test_verified_annual_debt_bucket_expires_with_report_date(self) -> None:
        facts = liquidity_facts("2026-06-30")
        result = current_liquidity("CRWV", facts, {}, "2026-06-30")
        self.assertEqual(
            result["first_full_year_principal_schedule"]["bucket"], "calendar 2027"
        )
        later = liquidity_facts("2026-09-30")
        later_result = current_liquidity("CRWV", later, {}, "2026-09-30")
        self.assertIsNone(later_result["first_full_year_principal_schedule"])
        self.assertIsNone(later_result["remaining_fiscal_year_principal_schedule"])


if __name__ == "__main__":
    unittest.main()
