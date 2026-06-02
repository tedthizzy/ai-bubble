from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from bubble.analysis.physical_execution_summary import build_physical_execution_summary

if TYPE_CHECKING:
    from pathlib import Path


def _write_terms(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_physical_execution_summary_collapses_exact_duplicate_terms(tmp_path: Path):
    terms = [
        {
            "term_type": "onsite_generation_mw",
            "value": "360.5",
            "unit": "MW",
            "quote": "five 38 MW turbines and five 34.1 MW turbines",
            "source_uri": "https://example.com/permit",
            "document_id": "permit-1",
            "project_name": "Compute Campus",
            "operator": "GPU Cloud",
            "jurisdiction": "Texas",
            "authority": "TCEQ",
            "permit_or_docket": "123",
        },
        {
            "term_type": "onsite_generation_mw",
            "value": "360.5",
            "unit": "MW",
            "quote": "five 38 MW turbines and five 34.1 MW turbines",
            "source_uri": "https://example.com/permit",
            "document_id": "permit-1",
            "project_name": "Compute Campus",
            "operator": "GPU Cloud",
            "jurisdiction": "Texas",
            "authority": "TCEQ",
            "permit_or_docket": "123",
        },
        {
            "term_type": "utility_generation_capacity_mw",
            "value": "1200",
            "unit": "MW",
            "quote": "utility proposes 1,200 MW for data center load",
            "source_uri": "https://example.com/docket",
            "document_id": "docket-1",
            "project_name": "Utility Load",
            "operator": "Utility Co",
            "jurisdiction": "Louisiana",
            "authority": "LPSC",
            "permit_or_docket": "U-1",
        },
        {
            "term_type": "queue_bypass_or_no_queue",
            "value": "present",
            "unit": "flag",
            "quote": "behind the meter and does not require ISO queue approval",
            "source_uri": "https://example.com/offgrid",
            "document_id": "permit-2",
            "project_name": "Offgrid Campus",
            "operator": "Miner Co",
            "jurisdiction": "West Virginia",
            "authority": "WVDEP",
            "permit_or_docket": "456",
        },
    ]
    _write_terms(tmp_path / "physical" / "physical_execution_terms.csv", terms)

    summary = build_physical_execution_summary([tmp_path], top_limit=5)

    assert summary.term_rows == 4
    assert summary.distinct_terms == 3
    assert summary.duplicate_term_rows_collapsed == 1
    assert summary.by_term_type["onsite_generation_mw"] == 2
    assert summary.distinct_by_term_type["onsite_generation_mw"] == 1
    assert summary.onsite_generation_mw_term_sum == 360.5
    assert summary.utility_generation_capacity_mw_term_sum == 1200
    assert summary.risk_term_counts == {"queue_bypass_or_no_queue": 1}
    assert summary.projects == 3
    assert summary.source_uris == 3
    assert summary.top_mw_terms[0]["project_name"] == "Utility Load"
    assert "not project-deduped capacity" in summary.caveat


def test_physical_execution_summary_handles_missing_artifact(tmp_path: Path):
    summary = build_physical_execution_summary([tmp_path])

    assert summary.term_rows == 0
    assert summary.distinct_terms == 0
    assert summary.by_term_type == {}
    assert summary.top_mw_terms == []
    assert summary.top_risk_terms == []
