"""Focused checks for the dated, keyless economy XBRL refresh."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import threading
import time
import unittest
from datetime import date
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "xbrl_economy_scan.py"
SPEC = importlib.util.spec_from_file_location("xbrl_economy_scan_for_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
SCAN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCAN)


class DatedXbrlRefreshTest(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.reference = self.root / "raw" / "sec_company_tickers_exchange.json"
        self.cache = self.root / "xbrl_economy_cache.json"
        self.output_json = self.root / "economy_xbrl_fragility.json"
        self.output_md = self.root / "economy_xbrl_fragility.md"
        self.reference.parent.mkdir()
        self.reference.write_text('"old reference"')
        self.cache.write_text('"old cache"')
        self.output_json.write_text('"old output"')
        self.output_md.write_text("old markdown")
        for name, path in (
            ("SEC_REF", self.reference),
            ("CACHE", self.cache),
            ("OUT_JSON", self.output_json),
            ("OUT_MD", self.output_md),
        ):
            patcher = mock.patch.object(SCAN, name, path)
            patcher.start()
            self.addCleanup(patcher.stop)
        sleep = mock.patch.object(SCAN.time, "sleep")
        sleep.start()
        self.addCleanup(sleep.stop)

    @staticmethod
    def reference_payload() -> dict:
        return {
            "fields": ["cik", "ticker", "name"],
            "data": [[111, "ONE", "Company One"], [222, "TWO", "Company Two"]],
        }

    def dated_path(self, original: Path) -> Path:
        suffix = ".jsonl" if original == self.cache else original.suffix
        return original.with_name(f"{original.stem}_2026-09-16{suffix}")

    def test_refresh_fetches_reference_and_filers_without_replacing_legacy(self) -> None:
        responses = [
            (self.reference_payload(), None, None),
            ({"facts": {"us-gaap": {}}}, None, None),
            (None, 404, "HTTP 404"),
        ]
        with mock.patch.object(SCAN, "fetch_sec_json", side_effect=responses) as fetch:
            self.assertEqual(SCAN.main(["--refresh-date", "2026-09-16"]), 0)
        self.assertEqual(fetch.call_count, 3)
        self.assertEqual(self.cache.read_text(), '"old cache"')
        self.assertEqual(self.output_json.read_text(), '"old output"')
        self.assertEqual(self.output_md.read_text(), "old markdown")
        output = json.loads(self.dated_path(self.output_json).read_text())
        self.assertEqual(output["filers_scanned"], 2)
        self.assertEqual(output["with_xbrl"], 1)
        self.assertEqual(output["without_xbrl_http_404"], 1)
        self.assertEqual([row["status"] for row in output["results"]], ["ok", "no_xbrl"])
        self.assertEqual(output["results"][1]["source_uri"],
                         "https://data.sec.gov/api/xbrl/companyfacts/CIK0000000222.json")
        self.assertIn("coverage", output["field_definitions"])
        self.assertEqual(len(output["reference_sha256"]), 64)
        self.assertIn("not observed distress", output["interpretation"])
        rows = [json.loads(line) for line in self.dated_path(self.cache).read_text().splitlines()]
        self.assertEqual([row["status"] for row in rows], ["ok", "no_xbrl"])
        self.assertTrue(all(row["fetched_at"] and row["source_uri"] for row in rows))
        self.assertTrue(self.dated_path(self.output_md).exists())
        self.assertIn(
            "XBRL ratio screen: SEC exchange-ticker reference universe",
            self.dated_path(self.output_md).read_text(),
        )

    def test_rate_limit_withholds_report_and_resumes_failed_filer(self) -> None:
        first_responses = [self.reference_payload(), None]

        def first_fetch(_url: str):
            if first_responses.pop(0) is None:
                return None, 429, "HTTP 429"
            return self.reference_payload(), None, None

        with mock.patch.object(SCAN, "fetch_sec_json", side_effect=first_fetch) as fetch:
            self.assertEqual(SCAN.main(["--refresh-date", "2026-09-16"]), 1)
        self.assertEqual(fetch.call_count, 2)
        self.assertFalse(self.dated_path(self.output_json).exists())

        with mock.patch.object(
            SCAN,
            "fetch_sec_json",
            side_effect=[({"facts": {"us-gaap": {}}}, None, None), (None, 404, "HTTP 404")],
        ) as fetch:
            self.assertEqual(SCAN.main(["--refresh-date", "2026-09-16"]), 0)
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(len(self.dated_path(self.cache).read_text().splitlines()), 3)

    def test_sec_empty_http_200_is_counted_separately_from_http_404(self) -> None:
        with mock.patch.object(
            SCAN, "fetch_sec_json",
            side_effect=[(self.reference_payload(), None, None), ({}, None, None),
                         (None, 404, "HTTP 404")],
        ):
            self.assertEqual(SCAN.main(["--refresh-date", "2026-09-16"]), 0)
        output = json.loads(self.dated_path(self.output_json).read_text())
        self.assertEqual(output["without_xbrl"], 2)
        self.assertEqual(output["without_xbrl_empty_http_200"], 1)
        self.assertEqual(output["without_xbrl_http_404"], 1)
        self.assertEqual(
            [row["no_xbrl_reason"] for row in output["results"]],
            ["empty_http_200", "http_404"],
        )

    def test_prior_v7_http_404_cache_row_gets_reason_in_memory(self) -> None:
        cache = self.dated_path(self.cache)
        cache.write_text(json.dumps({
            "cik": "0000000111", "selector_version": 7, "status": "no_xbrl"
        }) + "\n")
        self.assertEqual(SCAN.load_refresh_cache(cache)["0000000111"]["no_xbrl_reason"],
                         "http_404")
        self.assertNotIn("no_xbrl_reason", json.loads(cache.read_text()))

    def test_concurrent_fetches_preserve_rate_and_stop_after_429(self) -> None:
        reference = {
            "fields": ["cik", "ticker", "name"],
            "data": [[111, "ONE", "One"], [222, "TWO", "Two"], [333, "THREE", "Three"]],
        }
        both_started = threading.Event()
        lock = threading.Lock()
        starts: list[float] = []

        def fetch(url: str):
            if url == SCAN.SEC_REF_URL:
                return reference, None, None
            with lock:
                starts.append(time.monotonic())
                if len(starts) == 2:
                    both_started.set()
            if not both_started.wait(2):
                raise AssertionError("second companyfacts fetch did not overlap the first")
            if url.endswith("CIK0000000111.json"):
                return None, 429, "HTTP 429"
            return {"facts": {"us-gaap": {}}}, None, None

        with mock.patch.object(SCAN, "fetch_sec_json", side_effect=fetch):
            self.assertEqual(
                SCAN.main(["--refresh-date", "2026-09-16", "--requests-per-second", "8"]),
                1,
            )
        self.assertEqual(len(starts), 2)
        self.assertGreaterEqual(starts[1] - starts[0], 0.10)
        self.assertFalse(self.dated_path(self.output_json).exists())
        rows = [json.loads(line) for line in self.dated_path(self.cache).read_text().splitlines()]
        self.assertEqual({row["status"] for row in rows}, {"ok", "fetch_error"})

    def test_stale_interest_does_not_create_a_current_coverage_ratio(self) -> None:
        def item(value: float, end: str, start: str | None = None) -> dict:
            result = {
                "val": value,
                "end": end,
                "filed": "2026-08-26",
                "form": "10-K",
                "fp": "FY",
            }
            if start:
                result["start"] = start
            return result

        facts = {
            "facts": {
                "us-gaap": {
                    "LongTermDebt": {"units": {"USD": [item(5e9, "2026-07-26")]}},
                    "CashAndCashEquivalentsAtCarryingValue": {
                        "units": {"USD": [item(2e9, "2026-07-26")]}
                    },
                    "OperatingIncomeLoss": {
                        "units": {"USD": [item(10e9, "2026-01-25", "2025-01-27")]}
                    },
                    "DepreciationDepletionAndAmortization": {
                        "units": {"USD": [item(1e9, "2026-01-25", "2025-01-27")]}
                    },
                    "InterestExpense": {"units": {"USD": [item(1e8, "2024-01-28", "2023-01-30")]}},
                }
            }
        }
        row = SCAN.current_row(
            {"cik": "0001045810"}, facts, "ok", "https://data.sec.gov/example", None
        )
        self.assertEqual(row["debt_period_end"], "2026-07-26")
        self.assertEqual(row["interest_latest_period_end"], "2024-01-28")
        self.assertFalse(row["income_period_aligned"])
        self.assertIsNone(row["coverage"])
        self.assertEqual(row["classification"], "insufficient_data")

    def test_newer_interest_does_not_hide_same_year_interest_for_latest_ebitda(self) -> None:
        def annual(value: float, start: str, end: str) -> dict:
            return {
                "val": value, "start": start, "end": end,
                "filed": "2026-08-20", "form": "10-K", "fp": "FY",
            }

        fy2025 = ("2025-01-01", "2025-12-31")
        fy2026 = ("2025-07-01", "2026-06-30")
        facts = {"facts": {"us-gaap": {
            "OperatingIncomeLoss": {"units": {"USD": [annual(3e9, *fy2025)]}},
            "DepreciationAndAmortization": {"units": {"USD": [annual(1e9, *fy2025)]}},
            "InterestExpense": {"units": {"USD": [
                annual(1e9, *fy2025), annual(2e9, *fy2026),
            ]}},
        }}}
        row = SCAN.current_row(
            {"cik": "0000000111"}, facts, "ok", "https://data.sec.gov/example", None,
            date(2026, 9, 16),
        )
        self.assertEqual(row["ebitda_period_end"], "2025-12-31")
        self.assertEqual(row["interest_latest_period_end"], "2026-06-30")
        self.assertEqual(row["interest_period_end"], "2025-12-31")
        self.assertTrue(row["income_current"])
        self.assertEqual(row["coverage"], 4.0)

    def test_adequate_interest_coverage_with_unknown_net_debt_is_not_manageable(self) -> None:
        self.assertEqual(SCAN.classify(None, 10e9, 4.0), "insufficient_data")

    def test_negative_ebitda_has_no_numeric_coverage_ratio(self) -> None:
        def annual(value: float) -> dict:
            return {
                "val": value, "start": "2025-01-01", "end": "2025-12-31",
                "filed": "2026-02-01", "form": "10-K", "fp": "FY",
            }

        facts = {"facts": {"us-gaap": {
            "OperatingIncomeLoss": {"units": {"USD": [annual(-2e9)]}},
            "DepreciationAndAmortization": {"units": {"USD": [annual(1e8)]}},
            "InterestExpense": {"units": {"USD": [annual(2e8)]}},
        }}}
        row = SCAN.current_row(
            {"cik": "0000000111"}, facts, "ok", "https://data.sec.gov/example", None,
            date(2026, 9, 16),
        )
        self.assertTrue(row["income_current"])
        self.assertIsNone(row["coverage"])
        self.assertEqual(row["classification"], "negative_ebitda")

    def test_latest_shared_balance_date_is_used_when_cash_has_newer_quarter(self) -> None:
        def instant(value: float, end: str) -> dict:
            return {"val": value, "end": end, "filed": "2026-09-01", "form": "10-Q"}

        facts = {
            "facts": {
                "us-gaap": {
                    "LongTermDebt": {"units": {"USD": [instant(5e9, "2026-05-31")]}},
                    "CashAndCashEquivalentsAtCarryingValue": {
                        "units": {"USD": [
                            instant(2e9, "2026-05-31"),
                            instant(3e9, "2026-08-31"),
                        ]}}
                }
            }
        }
        row = SCAN.current_row(
            {"cik": "0000000111"}, facts, "ok", "https://data.sec.gov/example", None,
            date(2026, 9, 16),
        )
        self.assertEqual(row["balance_period_end"], "2026-05-31")
        self.assertEqual(row["cash_period_end"], "2026-05-31")
        self.assertEqual(row["cash_latest_period_end"], "2026-08-31")
        self.assertTrue(row["balance_sheet_current"])
        self.assertEqual(row["net_debt_b"], 3)

    def test_stale_annual_loss_is_withheld_from_current_classification(self) -> None:
        facts = {
            "facts": {
                "us-gaap": {
                    "OperatingIncomeLoss": {
                        "units": {"USD": [{
                            "val": -1e9, "start": "2018-01-01", "end": "2018-12-31",
                            "filed": "2019-03-01", "form": "10-K", "fp": "FY",
                        }]}
                    },
                    "DepreciationDepletionAndAmortization": {
                        "units": {"USD": [{
                            "val": 1e8, "start": "2018-01-01", "end": "2018-12-31",
                            "filed": "2019-03-01", "form": "10-K", "fp": "FY",
                        }]}
                    },
                }
            }
        }
        row = SCAN.current_row(
            {"cik": "0000000111"}, facts, "ok", "https://data.sec.gov/example", None,
            date(2026, 9, 16),
        )
        self.assertEqual(row["ebitda_period_end"], "2018-12-31")
        self.assertIsNone(row["ebitda_b"])
        self.assertEqual(row["classification"], "insufficient_data")


if __name__ == "__main__":
    unittest.main()
