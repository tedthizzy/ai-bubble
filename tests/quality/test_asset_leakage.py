"""Sub-$50B asset-leakage fixtures (root cause 1, below the mega guard).

Positive fixtures are the real 0643 leakage (HBT "total loans", PennyMac MIT UPB);
negative controls are legitimate debt that must NOT be flagged (boilerplate
"forward-looking" + a real first-mortgage bond).
"""

from __future__ import annotations

from bubble.quality.asset_leakage import quote_is_asset_side, summarize_asset_leakage


def test_high_confidence_markers_flag_asset_figures() -> None:
    assert quote_is_asset_side("HBT Financial had total assets of $6.8 billion, total loans of $4.7 billion")
    assert quote_is_asset_side("Servicing portfolio UPB of $733.6 billion at year end")
    assert quote_is_asset_side("Loans eligible for repurchase / Financing capacity across multiple banks")


def test_boilerplate_and_real_debt_are_not_flagged() -> None:
    # 'forward-looking' boilerplate co-occurs with real debt -> must NOT flag.
    assert not quote_is_asset_side(
        "current economic and industry conditions, expected future developments (forward-looking statements)"
    )
    # A real first-mortgage bond prospectus -> committed debt, not an asset figure.
    assert not quote_is_asset_side(
        "The Series CCC bonds will be issued under a supplemental indenture and the first mortgage"
    )
    # A plain committed credit agreement.
    assert not quote_is_asset_side("$5 billion senior unsecured revolving credit agreement")


def test_summary_flags_sub_threshold_leakage_with_packets() -> None:
    rows = [
        {
            "metric_use_status": "approved_for_metric_use",
            "metric_group_id": "source-instrument:hashes:a:amount:4700000000",
            "supported_amount_usd": "4700000000",
            "entity": "HBT Financial, Inc.",
            "evidence_quote": "total assets of $6.8 billion, total loans of $4.7 billion",
            "packet_id": "adjudication:hbt",
        },
        {
            "metric_use_status": "approved_for_metric_use",
            "metric_group_id": "source-instrument:hashes:b:amount:5000000000",
            "supported_amount_usd": "5000000000",
            "entity": "Real Borrower Corp",
            "evidence_quote": "$5 billion senior unsecured revolving credit agreement, as Administrative Agent",
            "packet_id": "adjudication:real",
        },
        # A >$50B group is out of scope for THIS sweep (handled by the mega guard).
        {
            "metric_use_status": "approved_for_metric_use",
            "metric_group_id": "source-instrument:hashes:c:amount:60000000000",
            "supported_amount_usd": "60000000000",
            "entity": "Mega",
            "evidence_quote": "servicing portfolio UPB of $733.6 billion",
            "packet_id": "adjudication:mega",
        },
    ]

    s = summarize_asset_leakage(rows, mega_threshold=50e9)

    assert s["leaked_count"] == 1  # only HBT (real debt excluded; mega out of scope)
    assert s["leaked_gross_usd"] == 4.7e9
    assert s["leaked_packets"][0]["packet_id"] == "adjudication:hbt"
