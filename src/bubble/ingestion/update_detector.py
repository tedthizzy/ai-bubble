"""Continuous-update delta detector — the engine's "new data arrives" trigger.

A production forensic engine must update as new filings land. This module is the
core of that loop: given the set of filing accessions the engine has already
ingested (from the filing manifest) and a fresh EDGAR submissions snapshot for
the tracked CIKs, it computes the DELTA (accessions not yet ingested), prioritizes
by Burry-relevance of the form, and decides whether a re-run is warranted.

It is deterministic and provenance-preserving: it never fabricates a filing, only
diffs two disclosed sets, and labels each new filing with its form-relevance score
so a downstream scheduler can re-ingest + re-analyze the high-signal ones first.
The actual network fetch lives in a thin script wrapper; the diff/prioritize logic
here is pure and testable.
"""

from __future__ import annotations

from typing import Any

# Burry-relevance of each form type (higher = re-run sooner). Mirrors the
# filing-manifest form scores: annual/periodic + material-event + offering docs.
FORM_RELEVANCE: dict[str, int] = {
    "10-K": 100,
    "20-F": 100,
    "40-F": 95,
    "10-Q": 85,
    "8-K": 65,
    "6-K": 60,
    "S-1": 70,
    "424B5": 70,
    "424B2": 65,
    "S-4": 55,
    "DEF 14A": 50,
    "SC 13D": 45,
    "SC 13G": 35,
    "4": 20,
}
# A re-run is recommended when any new filing scores at/above this threshold
# (i.e. a 10-K/10-Q/8-K/offering doc landed — material to the thesis).
_RERUN_THRESHOLD = 65


def _form_score(form: str) -> int:
    form = str(form or "").strip().upper()
    if form in FORM_RELEVANCE:
        return FORM_RELEVANCE[form]
    # Form families (e.g. "8-K/A", "424B5") -> base form score.
    for key, score in FORM_RELEVANCE.items():
        if form.startswith(key.upper()):
            return score
    return 10


def detect_filing_updates(
    ingested_accessions: set[str] | list[str],
    fresh_submissions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Diff a fresh submissions snapshot against ingested accessions; prioritize the delta.

    fresh_submissions: list of {cik, accession, form, filing_date} dicts.
    Returns the new filings (sorted by form-relevance then date), a per-CIK count,
    and a rerun_recommended flag.
    """

    ingested = {str(a).strip() for a in ingested_accessions if str(a).strip()}
    seen_new: set[str] = set()
    deltas: list[dict[str, Any]] = []
    for sub in fresh_submissions:
        acc = str(sub.get("accession") or "").strip()
        if not acc or acc in ingested or acc in seen_new:
            continue
        seen_new.add(acc)
        form = str(sub.get("form") or "")
        deltas.append(
            {
                "cik": str(sub.get("cik") or "").strip(),
                "accession": acc,
                "form": form,
                "filing_date": str(sub.get("filing_date") or ""),
                "relevance": _form_score(form),
            }
        )

    deltas.sort(key=lambda d: (d["relevance"], d["filing_date"]), reverse=True)
    by_cik: dict[str, int] = {}
    for d in deltas:
        by_cik[d["cik"]] = by_cik.get(d["cik"], 0) + 1

    high_signal = [d for d in deltas if d["relevance"] >= _RERUN_THRESHOLD]
    rerun = bool(high_signal)
    return {
        "new_filing_count": len(deltas),
        "high_signal_count": len(high_signal),
        "rerun_recommended": rerun,
        "new_filings_by_cik": dict(sorted(by_cik.items(), key=lambda kv: -kv[1])),
        "top_new_filings": deltas[:25],
        "rerun_reason": (
            f"{len(high_signal)} new high-signal filing(s) (relevance >= {_RERUN_THRESHOLD}): "
            + ", ".join(f"{d['cik']}/{d['form']}" for d in high_signal[:8])
            if rerun
            else "no new high-signal filings since last ingest; re-run not warranted"
        ),
        "note": (
            "Continuous-update delta: diffs a fresh EDGAR submissions snapshot against the "
            "engine's ingested accessions, prioritizes new filings by form relevance (10-K/10-Q/8-K/"
            "offering docs trigger a re-run), and is deterministic + provenance-preserving (it only "
            "diffs disclosed accession sets, never invents a filing). Wire to a scheduler to re-ingest "
            "+ re-analyze the high-signal deltas first."
        ),
    }
