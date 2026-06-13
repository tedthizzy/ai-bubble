"""History persistence for the hourly overlay (WS3.1).

The live overlay is latest-only; this compresses each run into one compact daily record
appended to viz/history.jsonl, so the explorer and the public track-record page can chart
drift in the credit dial, the S3' differential, and the pre-registered signal states over
time. Pure functions (no I/O) so they sit under mypy and unit tests; the script does the
file read/write.

One record per UTC day: the hourly bot overwrites the same day's record until the last run
of the day persists, which keeps the file at ~365 lines/year while giving a clean daily
series. The signal *statuses* are the calibration ledger the Q4 adjudication scores against.
"""

from __future__ import annotations

from typing import Any

# Cluster equities whose closes are worth a drift series (the names WS1.1 inverts).
_CLUSTER_KEYS = ("CoreWeave", "Nebius", "IREN", "Applied Digital")

# Per-signal headline scalar, in priority order (first present key wins).
_SIGNAL_VALUE_KEYS = (
    "value_bp",
    "ccc_minus_hy_ytd_pp",
    "differential_pp",
    "yoy_growth_pct",
)


def build_history_record(payload: dict[str, Any]) -> dict[str, Any]:
    """Compress one live.json payload into a compact daily history record."""
    generated = str(payload.get("generated_utc") or "")
    credit = payload.get("credit") or {}

    def _level(key: str) -> float | None:
        series = credit.get(key) or {}
        value = series.get("value")
        return float(value) if isinstance(value, int | float) else None

    signals = payload.get("signals") or []
    signal_status = {s["id"]: s["status"] for s in signals if "id" in s and "status" in s}
    signal_value: dict[str, Any] = {}
    for s in signals:
        sid = s.get("id")
        if not sid:
            continue
        for key in _SIGNAL_VALUE_KEYS:
            if key in s and s[key] is not None:
                signal_value[sid] = s[key]
                break

    s3: dict[str, Any] = next(
        (s for s in signals if s.get("id") == "S3_bdc_discount_differential"), {}
    )
    quotes = payload.get("quotes") or {}
    cluster_close = {
        q["sym"]: q["close"]
        for nid, q in quotes.items()
        if nid in _CLUSTER_KEYS and isinstance(q, dict) and "sym" in q and "close" in q
    }

    return {
        "date": generated[:10],
        "generated_utc": generated,
        "hy_oas": _level("hy_oas"),
        "ccc_oas": _level("ccc_oas"),
        "bb_oas": _level("bb_oas"),
        "s3_differential_pp": s3.get("differential_pp"),
        "signal_status": signal_status,
        "signal_value": signal_value,
        "cluster_close": cluster_close,
    }


def merge_history(existing: list[dict[str, Any]], record: dict[str, Any]) -> list[dict[str, Any]]:
    """Append-or-replace by UTC date, returning the series sorted ascending.

    A record with no usable date is dropped rather than corrupting the series.
    """
    if not record.get("date"):
        return [r for r in existing if r.get("date")]
    by_date = {r["date"]: r for r in existing if isinstance(r, dict) and r.get("date")}
    by_date[record["date"]] = record
    return [by_date[d] for d in sorted(by_date)]
