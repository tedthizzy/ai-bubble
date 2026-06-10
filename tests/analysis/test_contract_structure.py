"""Contract-level structure aggregation (who bears the loss)."""

from __future__ import annotations

from bubble.analysis.contract_structure import aggregate_contract_structure


def _fac(
    name,
    recourse,
    *,
    verdict="filing_verified",
    spv=None,
    guarantors=None,
    bankruptcy_remote=None,
    gpu=None,
    principal=None,
    scope=None,
):
    return {
        "facility_name": name,
        "recourse": recourse,
        "borrower_spv": spv,
        "guarantors": guarantors or [],
        "bankruptcy_remote": bankruptcy_remote,
        "gpu_collateral": gpu,
        "principal_usd": principal,
        "guarantee_scope": scope,
        "verdict": verdict,
    }


def _rec(issuer, facs, overall="source_backed"):
    return {"issuer": issuer, "verified_facilities": facs, "overall": overall}


def test_blocks_without_source_backed() -> None:
    out = aggregate_contract_structure(
        [_rec("X", [_fac("F", "non_recourse")], overall="unreliable")]
    )
    assert out["status"] == "blocked_no_source_backed_contract_structure"


def test_rejected_facilities_excluded() -> None:
    out = aggregate_contract_structure(
        [
            _rec(
                "CoreWeave",
                [
                    _fac("DDTL", "full_recourse_to_parent"),
                    _fac("Ghost", "non_recourse", verdict="rejected_unsourced"),
                ],
            )
        ]
    )
    assert out["facility_count"] == 1
    assert out["recourse_breakdown_counts"]["non_recourse"] == 0


def test_parent_equity_read_and_principal() -> None:
    out = aggregate_contract_structure(
        [
            _rec(
                "CoreWeave",
                [
                    _fac(
                        "DDTL 1",
                        "full_recourse_to_parent",
                        guarantors=["CoreWeave Inc"],
                        principal=1_000_000_000,
                        gpu="yes",
                        scope="parent guaranty, no cap",
                    ),
                    _fac("DDTL 2", "full_recourse_to_parent", principal=500_000_000),
                ],
            )
        ]
    )
    assert out["status"] == "source_backed"
    assert out["recourse_breakdown_counts"]["full_recourse_to_parent"] == 2
    assert out["recourse_breakdown_principal_usd"]["full_recourse_to_parent"] == 1_500_000_000
    assert out["parent_guaranteed_facilities"] == 1
    assert out["gpu_collateralized_facilities"] == 1
    assert "loss_concentrates_on_parent_equity" in out["who_bears_downside_read"]


def test_ring_fenced_read() -> None:
    out = aggregate_contract_structure(
        [
            _rec(
                "SPVco",
                [
                    _fac("F1", "non_recourse", bankruptcy_remote="yes", spv="SPVco Financing LLC"),
                    _fac(
                        "F2", "non_recourse", bankruptcy_remote="yes", spv="SPVco Financing II LLC"
                    ),
                ],
            )
        ]
    )
    assert out["named_borrower_spv_facilities"] == 2
    assert out["bankruptcy_remote_facilities"] == 2
    assert "loss_ring_fenced_to_spv_creditors" in out["who_bears_downside_read"]
