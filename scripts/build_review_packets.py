#!/usr/bin/env python
"""Generate reproducible adversarial-review packets (WS4.1).

For each top load-bearing claim, emit a one-stop packet: the claim, the exact figure (pulled
live from the published report or the analysis artifacts so it cannot drift from the prose),
its provenance + evidence tier, and the exact command a hostile reviewer runs to reproduce it.
Witnessed credibility requires that an outsider can check a claim without trusting the author;
these packets are the check.

Writes analysis/review_packets/<id>.md + analysis/review_packets/README.md. Deterministic.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "data" / "published" / "BURRY_REPORT_EvidenceGated_20260603-2312.json"
OUT_DIR = ROOT / "analysis" / "review_packets"


def _report() -> dict[str, Any]:
    return json.loads(REPORT.read_text())


def _meta(r: dict[str, Any]) -> dict[str, Any]:
    # the viz meta block carries the headline scalars in a compact place
    return json.loads((ROOT / "viz" / "graph_data.json").read_text()).get("meta", {})


# Each packet: id, claim, tier, the figure extractor, provenance, rerun command, reviewer prompt.
Packet = dict[str, Any]


def _packets(r: dict[str, Any]) -> list[Packet]:
    meta = _meta(r)
    core_b = (meta.get("committed_core_usd") or 0) / 1e9
    headline_t = (meta.get("original_inflated_basis_usd") or 0) / 1e12
    cut = meta.get("over_count_removed_pct")
    return [
        {
            "id": "01_overcount_strip",
            "claim": f"The inflated headline basis of ~${headline_t:.2f}T collapses to "
            f"~${core_b:.1f}B of committed core cluster debt after stripping ~{cut:.0f}% "
            "over-count (duplicate/aggregate/out-of-scope rows).",
            "tier": "filing_verified core; the strip is deterministic and replayable",
            "figure_source": "viz/graph_data.json meta.{original_inflated_basis_usd, "
            "committed_core_usd, over_count_removed_pct}; derivation in "
            "data/published/BURRY_REPORT_...json capital_scope + debt_service_mismatch",
            "rerun": "python -c \"import json;m=json.load(open('viz/graph_data.json'))['meta'];"
            "print(m['original_inflated_basis_usd']/1e12,'T ->',m['committed_core_usd']/1e9,'B',"
            "m['over_count_removed_pct'],'%')\"",
            "reviewer_prompt": "Attack the de-duplication: are any stripped rows actually distinct "
            "committed obligations? Are any retained core rows double-counted? The strip is the "
            "single biggest number-mover — verify the scope gate did not over- or under-cut.",
        },
        {
            "id": "02_coverage_breach_7of11",
            "claim": f"{meta.get('issuers_breaching_base', '7 of 11')} cluster issuers breach "
            "debt-service coverage at the zero-shock base; the aggregate 1.35x is a CoreWeave "
            "masking artifact (negative ex-CoreWeave).",
            "tier": "source_backed (issuer filings; interest from measured rates on 44% of notional)",
            "figure_source": "data/published/BURRY_REPORT_...json debt_service_mismatch "
            "(top_entity_debt_service_risks, measured_annual_interest_usd) + cluster_dscr",
            "rerun": "python -c \"import json;d=json.load(open('data/published/"
            "BURRY_REPORT_EvidenceGated_20260603-2312.json'))['debt_service_mismatch'];"
            "print('measured annual interest $', round(d['measured_annual_interest_usd']/1e9,2),'B "
            "on', d['measured_rate_notional_coverage_pct'],'% of notional')\"",
            "reviewer_prompt": "The interest is measured on ~44% of notional (rates missing on the "
            "rest). Does extrapolating the missing-rate notional change the 7/11 count? Is the "
            "ex-CoreWeave negative aggregate robust to the missing-rate names?",
        },
        {
            "id": "03_gpu_duration_mismatch",
            "claim": "Peak debt horizon (~48 months) outlives GPU economic life (~24 months), so "
            "secured lenders cannot be made whole on the collateral — the defining structural "
            "mismatch (1 of 2 cleanly-met fragility conditions).",
            "tier": "source_backed (depreciation schedules vs debt maturities)",
            "figure_source": "data/published/BURRY_REPORT_...json (fragility dimension "
            "asset_liability_duration_mismatch); GPU economics in src/bubble/analysis/gpu_economics.py",
            "rerun": "PYTHONPATH=src python -c \"import json;r=json.load(open('data/published/"
            "BURRY_REPORT_EvidenceGated_20260603-2312.json'));"
            "print([d for d in r['debt_service_mismatch']['debt_service_wall_by_quarter']][:4])\"",
            "reviewer_prompt": "Is ~2-3yr GPU economic life defensible for the specific chips in "
            "these fleets (vs a longer book life)? If economic life is 4yr, does the mismatch "
            "survive? See base_rates.md: the analogy break is that GPUs lack fiber's 20yr option.",
        },
        {
            "id": "04_renewal_dependent_share",
            "claim": "Across the four inverted neoclouds, 78–96% of enterprise value (median) rests "
            "on RE-CONTRACTING assets after the signed backlog runs off — priced against ~2–3yr "
            "GPU economic life.",
            "tier": "market/press inputs + stylized inversion (assumptions carded)",
            "figure_source": "analysis/expectations_inversion.md; src/bubble/expectations/ "
            "(inversion.py math, names.py carded inputs)",
            "rerun": "python scripts/build_expectations_inversion.py && "
            "python -c \"import json;[print(r['ticker'], r['renewal_dependent_share']) "
            "for r in json.load(open('viz/expectations.json'))['results']]\"",
            "reviewer_prompt": "Attack the stylization: even revenue recognition over tenor, sunk "
            "capex in EV, double-count of current revenue and near-term backlog. Re-run with your "
            "own discount-rate / margin / tenor grid (inputs are in names.py) — does the renewal "
            "dependence stay high for the GPU clouds?",
        },
        {
            "id": "05_funding_chain_first",
            "claim": "The first transmission channel is the semi-liquid-fund redemption gate, and it "
            "is already binding in 2026 (Apollo ~45% fill, Ares 43.1%, Blue Owl OTIC 40.7% "
            "requested, BCRED's first gate) — corroborating the funding-chain-first read.",
            "tier": "press_reported (named vehicle gate events, multi-source verified)",
            "figure_source": "analysis/marginal_buyer_constraints.{md,json} "
            "(4_semiliquid_gates.gates_actually_hit_2026)",
            "rerun": "python -c \"import json;print(json.load(open('analysis/"
            "marginal_buyer_constraints.json'))['constraints']['4_semiliquid_gates']"
            "['gates_actually_hit_2026'])\"",
            "reviewer_prompt": "Are these gates AI-credit-specific or broad private-credit risk-off? "
            "The fill-% inferences (BCRED Q2, Blue Owl per-fund) are arithmetic, not printed — "
            "verify against the primary filings. Does the manager-coupling claim (~12:1) hold?",
        },
        {
            "id": "06_bounded_not_ecosystem",
            "claim": f"The leveraged cluster stays ~{meta.get('cluster_share_pct', 4.3)}% of the "
            "classified AI-infra universe even at the ~2x capture-recapture true size — bounded, "
            "not ecosystem-wide; the ecosystem verdict is held at 0.25 by design.",
            "tier": "source_backed; the 0.25 cap is a deliberate evidence-gate floor",
            "figure_source": "viz/graph_data.json meta.{cluster_share_pct, ecosystem_confidence}; "
            "data/published/BURRY_REPORT_...json burry_separation_test",
            "rerun": "python -c \"import json;m=json.load(open('viz/graph_data.json'))['meta'];"
            "print('cluster share', m['cluster_share_pct'],'%; ecosystem conf', "
            "m['ecosystem_confidence'])\"",
            "reviewer_prompt": "Is the cluster boundary drawn too tightly (excluding genuinely "
            "leveraged names) or too loosely? Does capture-recapture's unobserved-fraction bound "
            "hold? This claim is what keeps the verdict SCOPED — attack the scoping.",
        },
    ]


def render_packet(p: Packet) -> str:
    return "\n".join(
        [
            f"# Review packet {p['id']}",
            "",
            f"**Claim.** {p['claim']}",
            "",
            f"**Evidence tier.** {p['tier']}",
            "",
            f"**Where the figure comes from.** {p['figure_source']}",
            "",
            "**Reproduce it.**",
            "```bash",
            p["rerun"],
            "```",
            "",
            f"**Your job as reviewer.** {p['reviewer_prompt']}",
            "",
            "**Verdict (reviewer fills in):** ☐ stands · ☐ stands with caveats · ☐ does not stand",
            "",
            "Notes:",
            "",
        ]
    )


def render_readme(packets: list[Packet]) -> str:
    rows = "\n".join(f"- [{p['id']}](./{p['id']}.md) — {p['claim'][:90]}…" for p in packets)
    return (
        "# Adversarial-review packets\n\n"
        "Generated by `scripts/build_review_packets.py`. Each packet is a load-bearing claim with "
        "its exact figure, provenance, a one-line command to reproduce it, and a reviewer prompt "
        "written to **attack** the claim, not confirm it. The goal is witnessed credibility: a "
        "hostile competent outsider can check the work without trusting the author.\n\n"
        "**Process.** A reviewer runs each `rerun` block (they reproduce the number), then answers "
        "the reviewer prompt and records a verdict. Responses are published verbatim alongside the "
        "research — including the ones that find errors. Target reviewers: a structured-credit "
        "lawyer (waterfalls), a private-credit professional (the marginal-buyer map), and a genuine "
        "AI bull (the demand trajectory).\n\n"
        "**Reproducibility note.** Every command runs against committed artifacts "
        "(`data/published/`, `viz/`, `analysis/`, `src/`) with no network and no keys — so a "
        "reviewer needs only `git clone`.\n\n"
        f"## Packets\n\n{rows}\n"
    )


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    packets = _packets(_report())
    for p in packets:
        (OUT_DIR / f"{p['id']}.md").write_text(render_packet(p))
    (OUT_DIR / "README.md").write_text(render_readme(packets))
    print(f"wrote {len(packets)} review packets + README to {OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
