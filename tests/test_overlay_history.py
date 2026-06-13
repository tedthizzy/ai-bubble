"""Unit tests for overlay history persistence (src/bubble/overlay_history.py)."""

from __future__ import annotations

from bubble.overlay_history import build_history_record, merge_history

PAYLOAD = {
    "generated_utc": "2026-06-13T02:05:49Z",
    "credit": {
        "hy_oas": {"value": 2.78, "ytd_chg": -0.05},
        "ccc_oas": {"value": 9.56, "ytd_chg": 0.68},
        "bb_oas": {"value": 1.69, "ytd_chg": -0.02},
    },
    "quotes": {
        "CoreWeave": {"sym": "CRWV", "close": 100.55, "chg_pct": -1.2},
        "Nebius": {"sym": "NBIS", "close": 232.36},
        "Microsoft": {"sym": "MSFT", "close": 500.0},  # not a cluster key -> excluded
    },
    "signals": [
        {"id": "S1_new_issue_spread", "status": "contra", "value_bp": 332},
        {"id": "S1b_failed_print", "status": "neutral", "event": None},
        {"id": "S3_bdc_discount_differential", "status": "neutral", "differential_pp": 7.5},
        {"id": "S4_demand_trajectory", "status": "contra", "yoy_growth_pct": 252.9},
    ],
}


class TestBuildRecord:
    def test_date_is_utc_day(self) -> None:
        rec = build_history_record(PAYLOAD)
        assert rec["date"] == "2026-06-13"

    def test_credit_levels_flattened(self) -> None:
        rec = build_history_record(PAYLOAD)
        assert rec["hy_oas"] == 2.78
        assert rec["ccc_oas"] == 9.56
        assert rec["bb_oas"] == 1.69

    def test_only_cluster_closes_kept(self) -> None:
        rec = build_history_record(PAYLOAD)
        assert rec["cluster_close"] == {"CRWV": 100.55, "NBIS": 232.36}
        assert "MSFT" not in rec["cluster_close"]

    def test_signal_status_and_value_extracted(self) -> None:
        rec = build_history_record(PAYLOAD)
        assert rec["signal_status"]["S1_new_issue_spread"] == "contra"
        assert rec["signal_value"]["S1_new_issue_spread"] == 332
        assert rec["signal_value"]["S3_bdc_discount_differential"] == 7.5
        # S1b has no numeric headline key -> absent from signal_value, present in status
        assert "S1b_failed_print" not in rec["signal_value"]
        assert rec["signal_status"]["S1b_failed_print"] == "neutral"
        assert rec["s3_differential_pp"] == 7.5

    def test_missing_credit_is_none_not_crash(self) -> None:
        rec = build_history_record({"generated_utc": "2026-06-13T00:00:00Z"})
        assert rec["hy_oas"] is None
        assert rec["signal_status"] == {}
        assert rec["cluster_close"] == {}


class TestMergeHistory:
    def test_append_new_date(self) -> None:
        a = {"date": "2026-06-12", "hy_oas": 2.80}
        b = {"date": "2026-06-13", "hy_oas": 2.78}
        assert [r["date"] for r in merge_history([a], b)] == ["2026-06-12", "2026-06-13"]

    def test_same_date_replaces_latest_run_wins(self) -> None:
        early = {"date": "2026-06-13", "hy_oas": 2.80}
        late = {"date": "2026-06-13", "hy_oas": 2.78}
        merged = merge_history([early], late)
        assert len(merged) == 1
        assert merged[0]["hy_oas"] == 2.78

    def test_output_sorted_ascending(self) -> None:
        existing = [{"date": "2026-06-13"}, {"date": "2026-06-11"}]
        merged = merge_history(existing, {"date": "2026-06-12"})
        assert [r["date"] for r in merged] == ["2026-06-11", "2026-06-12", "2026-06-13"]

    def test_dateless_record_dropped(self) -> None:
        existing = [{"date": "2026-06-12"}]
        merged = merge_history(existing, {"hy_oas": 2.78})
        assert merged == existing

    def test_corrupt_existing_rows_ignored(self) -> None:
        existing = [{"no_date": 1}, {"date": "2026-06-12"}]
        merged = merge_history(existing, {"date": "2026-06-13"})
        assert [r["date"] for r in merged] == ["2026-06-12", "2026-06-13"]
