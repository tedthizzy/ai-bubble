"""Dated capital graph inputs and review status remain explicit."""

from __future__ import annotations

import csv
import hashlib
import json
from typing import TYPE_CHECKING

import pytest
from scripts.refresh_capital_graph_2026_09_16 import build_capital, load_ferc_deals, select_deals

if TYPE_CHECKING:
    from pathlib import Path


FIELDS = [
    "deal_id",
    "deal_type",
    "title",
    "parties",
    "primary_party",
    "counterparty_roles",
    "source_uri",
    "source_type",
    "human_review_status",
    "content_hash",
]


def _write_deals(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _row(deal_id: str, source_type: str, review: str) -> dict[str, str]:
    return {
        "deal_id": deal_id,
        "deal_type": "ppa" if source_type == "ferc" else "debt_facility",
        "title": deal_id,
        "parties": "Generator|Utility" if source_type == "ferc" else "Borrower|Lender",
        "primary_party": "Generator" if source_type == "ferc" else "Borrower",
        "counterparty_roles": json.dumps(
            {"seller": ["Generator"], "buyer": ["Utility"]}
            if source_type == "ferc"
            else {"borrower": ["Borrower"], "lender": ["Lender"]}
        ),
        "source_uri": f"https://example.com/{deal_id}",
        "source_type": source_type,
        "human_review_status": review,
        "content_hash": hashlib.sha256(deal_id.encode()).hexdigest(),
    }


def test_complete_graph_uses_only_dated_inputs_and_reports_review(tmp_path: Path) -> None:
    ferc = tmp_path / "dated" / "ppa_deals.csv"
    edgar = tmp_path / "dated_edgar" / "deals.csv"
    _write_deals(ferc, [_row("ferc-1", "ferc", "pending")])
    _write_deals(edgar, [_row("edgar-1", "sec_edgar", "approved")])
    root = tmp_path / "graph"

    result = build_capital(mode="complete", ferc_path=ferc, edgar_path=edgar, output_root=root)

    assert result["selection"]["source_rows"] == {"edgar": 1, "ferc": 1}
    assert result["selection"]["graph_deals"] == 2
    assert result["selection"]["pending_graph_deals"] == 1
    assert result["selection"]["reviewed_graph_deals"] == 1
    assert (
        result["inputs"]["ferc_ppa_deals"]["sha256"]
        == hashlib.sha256(ferc.read_bytes()).hexdigest()
    )
    assert (
        result["inputs"]["edgar_deals"]["sha256"] == hashlib.sha256(edgar.read_bytes()).hexdigest()
    )
    assert result["graph_summary"]["deals_scanned"] == 2
    repeat = build_capital(
        mode="complete", ferc_path=ferc, edgar_path=edgar, output_root=tmp_path / "repeat"
    )
    assert {name: record["sha256"] for name, record in result["outputs"].items()} == {
        name: record["sha256"] for name, record in repeat["outputs"].items()
    }
    with pytest.raises(FileExistsError, match="Refusing to replace"):
        build_capital(mode="complete", ferc_path=ferc, edgar_path=edgar, output_root=root)


def test_duplicate_source_rows_are_removed_but_conflicts_fail(tmp_path: Path) -> None:
    ferc = tmp_path / "ppa_deals.csv"
    row = _row("ferc-1", "ferc", "pending")
    _write_deals(ferc, [row, row])
    deals, counts = select_deals([("ferc", load_ferc_deals(ferc))])
    assert len(deals) == 1
    assert counts["exact_duplicate_rows_removed"] == 1

    conflicting = {**row, "content_hash": "f" * 64}
    _write_deals(ferc, [row, conflicting])
    with pytest.raises(ValueError, match="Conflicting duplicate source row"):
        select_deals([("ferc", load_ferc_deals(ferc))])
