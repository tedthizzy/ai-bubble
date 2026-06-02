"""Tests for the read-only report/docs consistency verifier.

Fixture-based only: every test constructs synthetic docs + summaries in a tmp
dir. Nothing here reads the live data/reports artifacts, so the checks stay
stable as the corpus is rebuilt.
"""

from __future__ import annotations

from bubble.quality.report_consistency import (
    CountExpectation,
    build_expectations,
    check_confidence_flags,
    check_invariant_audit_status,
    check_labeled_counts,
    check_metric_audit_coverage,
    check_metric_total_agreement,
    check_report_path_freshness,
    check_timestamp_freshness,
    latest_report_stem,
)


def test_flags_doc_referencing_stale_report_path() -> None:
    doc = (
        "Last updated 2026-06-02.\n"
        "Latest evidence-gated report: "
        "`data/reports/BURRY_REPORT_EvidenceGated_20260602-0237.md`\n"
        "See the JSON at data/reports/BURRY_REPORT_EvidenceGated_20260602-0237.json too.\n"
    )

    findings = check_report_path_freshness(
        doc_text=doc,
        doc_name="acquisition_status.md",
        latest_stem="BURRY_REPORT_EvidenceGated_20260602-0247",
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "stale_report_path"
    assert finding.severity == "error"
    assert finding.doc == "acquisition_status.md"
    assert "20260602-0237" in finding.actual
    assert "20260602-0247" in finding.expected


def test_flags_drifted_labeled_count() -> None:
    doc = "Source-backed deals: 62,952.\nCovered filings: 197,243.\n"
    expectations = [
        CountExpectation(
            key="source_backed_deals",
            pattern=r"Source-backed deals:\s*([\d,]+)",
            authoritative=63010,
        ),
    ]

    findings = check_labeled_counts(
        doc_text=doc, doc_name="acquisition_status.md", expectations=expectations
    )

    assert len(findings) == 1
    assert findings[0].check == "stale_count"
    assert findings[0].severity == "error"
    assert findings[0].actual == "62,952"
    assert "63,010" in findings[0].expected


def test_latest_report_stem_picks_newest_by_timestamp(tmp_path) -> None:
    for ts in ("20260602-0215", "20260602-0247", "20260601-0530"):
        (tmp_path / f"BURRY_REPORT_EvidenceGated_{ts}.json").write_text("{}")
        (tmp_path / f"BURRY_REPORT_EvidenceGated_{ts}.md").write_text("#")

    assert latest_report_stem(tmp_path) == "BURRY_REPORT_EvidenceGated_20260602-0247"


def test_build_expectations_maps_decision_and_invariant_metrics() -> None:
    decision_summary = {
        "decisions": 6699,
        "supported_as_material_blocker": 4322,
        "needs_deeper_extraction": 2377,
        "approved_for_metric_use": 2736,
        "final_metric_group_count": 2735,
        "final_metric_supported_amount_usd": 11894118495033.83,
    }
    invariant_audit = {
        "files_scanned": 63,
        "rows_scanned": 9208844,
        "violation_count": 0,
        "warning_count": 0,
    }

    exps = build_expectations(
        report={}, decision_summary=decision_summary, invariant_audit=invariant_audit
    )
    by_key = {e.key: e for e in exps}

    assert by_key["decisions.approved_for_metric_use"].authoritative == 2736
    assert by_key["invariant.rows_scanned"].authoritative == 9208844
    # money is normalized to trillions at 3 decimals for prose comparison
    assert by_key["decisions.final_metric_supported_usd_trillions"].authoritative == 11.894


def test_flags_failed_source_invariant_audit() -> None:
    findings = check_invariant_audit_status(
        {"passed": False, "violation_count": 2, "warning_count": 0}
    )

    checks = {f.check for f in findings}
    assert "invariant_audit_not_passing" in checks
    assert "invariant_audit_violations" in checks
    assert all(f.severity == "error" for f in findings)


def test_passing_source_invariant_audit_has_no_findings() -> None:
    assert (
        check_invariant_audit_status({"passed": True, "violation_count": 0, "warning_count": 0})
        == []
    )


def test_flags_report_metric_total_disagreeing_with_decision_summary() -> None:
    report = {
        "materiality_adjudication_decisions": {
            "final_metric_supported_amount_usd": 11_700_000_000_000.0
        }
    }
    decision_summary = {"final_metric_supported_amount_usd": 11_894_000_000_000.0}

    findings = check_metric_total_agreement(report=report, decision_summary=decision_summary)

    assert len(findings) == 1
    assert findings[0].check == "metric_total_mismatch"
    assert findings[0].severity == "error"


def test_flags_doc_claiming_wrong_confidence_flags() -> None:
    doc = "High-confidence final: True\nEvidence-gated bubble confidence: 80%\n"

    findings = check_confidence_flags(
        high_confidence_final=False,
        bubble_confidence=0.25,
        doc_text=doc,
        doc_name="FINAL_DELIVERY.md",
    )

    checks = {f.check for f in findings}
    assert "stale_high_confidence_final" in checks
    assert "stale_bubble_confidence" in checks
    assert all(f.severity == "error" for f in findings)


def test_matching_confidence_flags_have_no_findings() -> None:
    doc = "high_confidence_final: false\nbubble confidence: 25%\n"

    findings = check_confidence_flags(
        high_confidence_final=False,
        bubble_confidence=0.25,
        doc_text=doc,
        doc_name="acquisition_status.md",
    )

    assert findings == []


def test_flags_high_impact_answer_metric_without_audit() -> None:
    report = {
        "evidence_quality": {
            "claim_audits": [{"claim_id": "coverage.filings", "value": 197243}],
        },
        "burry_question_answers": {
            "how_large": {
                "current_debt_like_notional_usd": 1_200_000_000_000,  # $1.2T, unaudited
                "current_small_usd": 50_000_000,  # below threshold
                "current_count": 1022,  # not a usd metric
            }
        },
    }

    findings = check_metric_audit_coverage(report, threshold=100e9)

    assert len(findings) == 1
    assert findings[0].check == "unaudited_high_impact_metric"
    assert findings[0].severity == "warning"
    assert "current_debt_like_notional_usd" in findings[0].message


def test_audited_high_impact_metric_has_no_finding() -> None:
    report = {
        "evidence_quality": {
            "claim_audits": [{"claim_id": "x", "value": 1_200_000_000_000}],
        },
        "burry_question_answers": {
            "how_large": {"current_debt_like_notional_usd": 1_200_000_000_000}
        },
    }

    assert check_metric_audit_coverage(report, threshold=100e9) == []


def test_warns_on_stale_doc_timestamp() -> None:
    doc = "Source invariant audit: passed at 2026-06-02 02:35 UTC, 63 CSV files.\n"

    findings = check_timestamp_freshness(
        doc_text=doc,
        doc_name="acquisition_status.md",
        label="Source invariant audit",
        authoritative_iso="2026-06-02T03:07:08+00:00",
    )

    assert len(findings) == 1
    assert findings[0].check == "stale_timestamp"
    assert findings[0].severity == "warning"


def test_current_doc_timestamp_has_no_findings() -> None:
    doc = "Source invariant audit: passed at 2026-06-02 03:07 UTC.\n"

    findings = check_timestamp_freshness(
        doc_text=doc,
        doc_name="acquisition_status.md",
        label="Source invariant audit",
        authoritative_iso="2026-06-02T03:07:08+00:00",
    )

    assert findings == []


def test_agreeing_metric_totals_have_no_findings() -> None:
    report = {
        "materiality_adjudication_decisions": {
            "final_metric_supported_amount_usd": 11_711_518_495_033.83
        }
    }
    decision_summary = {"final_metric_supported_amount_usd": 11_711_518_495_033.83}

    assert check_metric_total_agreement(report=report, decision_summary=decision_summary) == []
