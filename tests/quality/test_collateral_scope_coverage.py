"""Tests for the residual collateral-scope gap coverage metric."""

from __future__ import annotations

from bubble.quality.collateral_scope_coverage import summarize_collateral_scope_coverage


def _row(**overrides: str) -> dict[str, str]:
    base = {
        "packet_id": "adjudication:x",
        "entity": "Example Corp",
        "decision": "needs_deeper_extraction",
        "remaining_gap": "determine collateral scope",
        "evidence_quote": "",
        "exposure_basis_usd": "0",
    }
    base.update(overrides)
    return base


def test_summary_classifies_root_causes_of_collateral_gaps() -> None:
    rows = [
        # A: sole gap, quote has no scope language -> snippet-selection miss.
        _row(
            packet_id="A",
            evidence_quote="The borrower entered into a revolving credit agreement.",
            exposure_basis_usd="1000000000",
        ),
        # B: sole gap, quote determinately secured via first-lien only -> detection miss.
        _row(
            packet_id="B",
            evidence_quote="$730 million first lien notes due 2031, guaranteed.",
            exposure_basis_usd="3000000000",
        ),
        # C: multi-gap (not sole) containing the collateral gap, no scope language.
        _row(
            packet_id="C",
            remaining_gap="extract named counterparty and role | determine collateral scope",
            evidence_quote="no markers here",
            exposure_basis_usd="5000000000",
        ),
        # D: sole gap whose quote DOES carry a recognised marker (blocked for another
        # reason) -> counted as blocked but not a snippet-selection miss.
        _row(
            packet_id="D",
            evidence_quote="secured by a first priority security interest in the collateral",
            exposure_basis_usd="2000000000",
        ),
        # E: resolved -> excluded entirely.
        _row(packet_id="E", decision="supported_as_material_blocker", remaining_gap=""),
    ]

    summary = summarize_collateral_scope_coverage(rows)

    assert summary["blocked_collateral_gaps"] == 4  # A, B, C, D
    assert summary["sole_gap_count"] == 3  # A, B, D
    assert summary["sole_gap_exposure_usd"] == 6_000_000_000  # A + B + D
    assert summary["no_scope_language_count"] == 3  # A, B, C (D has a marker)
    assert summary["first_lien_marker_miss_count"] == 1  # B only
    assert summary["first_lien_marker_miss_packets"][0]["packet_id"] == "B"


def test_permitted_liens_quote_is_not_a_first_lien_miss() -> None:
    """Bare ``lien`` must not trip the first-lien detection — a negative-covenant
    ``permitted liens`` quote has no determinate secured scope."""

    rows = [
        _row(
            packet_id="neg",
            evidence_quote="The borrower shall not incur liens other than permitted liens.",
            exposure_basis_usd="9000000000",
        )
    ]

    summary = summarize_collateral_scope_coverage(rows)

    assert summary["blocked_collateral_gaps"] == 1
    assert summary["no_scope_language_count"] == 1
    assert summary["first_lien_marker_miss_count"] == 0
