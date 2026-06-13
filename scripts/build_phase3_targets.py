"""Phase 3 prep — select the deep-dive target set from the fragility map (OFFLINE).

Turns the Phase-1/2 ranking into a concrete, tiered list of entities for per-entity
deep-agent profiling. Honors the canary-over-beam preference (small obscure flagged
players matter as much as the giants) and guarantees cohort coverage so no sector is
missed. Produces analysis/phase3_targets.json, which the orchestrator passes to the
deep-dive workflow as `args` (workflow scripts have no filesystem access).

No network, no pull — pure selection over data already on disk.

Tiers:
  beam   — large flagged balance sheet (debt >= $20B): systemic if it breaks
  canary — small/obscure but high-signature (debt < $5B, composite >= 0.33):
           the thing that detonates first; weighted UP, never dropped for being small
  mid    — everything else above the inclusion threshold
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from classify_fragility_sectors import classify  # noqa: E402

MAP_JSON = ROOT / "analysis" / "economy_wide_fragility_map.json"
OUT_JSON = ROOT / "analysis" / "phase3_targets.json"

INCLUSION_COMPOSITE = 0.30
CANARY_COMPOSITE = 0.33
CANARY_MAX_DEBT = 5e9
BEAM_MIN_DEBT = 20e9
CANARY_TARGET_CAP = 50  # first deep-dive pass; full canary set (~1,078) extends the tail
BANK_SECTOR = "Bank / depository"


def seed_notes(r: dict) -> list[str]:
    """What the scan already establishes — the agent's starting hypotheses to verify."""
    s = r["signatures"]
    notes = []
    if s["leverage"] >= 0.7:
        notes.append(f"large debt footprint (${r['debt_notional_usd'] / 1e9:.0f}B gross)")
    if s["refi"] >= 0.5:
        notes.append(
            f"front-loaded refi wall (${r['near_term_notional_usd'] / 1e9:.0f}B due <=2027)"
        )
    if s["carry"] >= 0.4 and r["max_coupon"]:
        notes.append(f"distressed-priced tranche(s) up to {r['max_coupon'] * 100:.1f}%")
    if s["hidden"] >= 0.3:
        notes.append(f"structured/ring-fenced ({r['spv_flags']} SPV/non-recourse flags)")
    if s["concentration"] >= 0.4:
        notes.append(f"counterparty concentration (HHI {r['counterparty_hhi']:.2f})")
    if s["circular"] >= 0.3:
        notes.append("related-party / circular financing flagged")
    return notes


def main() -> None:
    data = json.loads(MAP_JSON.read_text())
    rows = data["top_200"]
    for r in rows:
        r["sector"] = classify(r["entity"], r["ai_tagged"])

    targets = []
    cohort_seen: dict[str, int] = {}
    for r in sorted(rows, key=lambda x: x["composite"], reverse=True):
        sector = r["sector"]
        comp = r["composite"]
        debt = r["debt_notional_usd"]
        is_bank = sector == BANK_SECTOR
        is_canary = comp >= CANARY_COMPOSITE and 0 < debt < CANARY_MAX_DEBT
        cohort_rank = cohort_seen.get(sector, 0)
        # include if above threshold, OR a canary, OR one of the top-3 in its cohort
        include = comp >= INCLUSION_COMPOSITE or is_canary or cohort_rank < 3
        if not include:
            continue
        cohort_seen[sector] = cohort_rank + 1
        if is_canary:
            tier = "canary"
        elif debt >= BEAM_MIN_DEBT:
            tier = "beam"
        else:
            tier = "mid"
        targets.append(
            {
                "entity": r["entity"],
                "cik": r["cik"],
                "ticker": r["ticker"],
                "sector": sector,
                "tier": tier,
                "off_corporate_leverage_axis": is_bank,
                "composite": comp,
                "ai_tagged": r["ai_tagged"],
                "debt_notional_usd": debt,
                "near_term_notional_usd": r["near_term_notional_usd"],
                "max_coupon": r["max_coupon"],
                "source_uri_count": r["source_uri_count"],
                "signatures": r["signatures"],
                "seed_hypotheses": seed_notes(r),
            }
        )

    # ---- canary tier: pulled from the dedicated small-debt canary lens (the composite
    # buries them, so they have their own ranked list). Ted's priority: these matter MORE.
    seen = {t["entity"] for t in targets}
    for rc in data.get("top_canaries", [])[:CANARY_TARGET_CAP]:
        if rc["entity"] in seen:
            continue
        seen.add(rc["entity"])
        sector = classify(rc["entity"], rc["ai_tagged"])
        targets.append(
            {
                "entity": rc["entity"],
                "cik": rc["cik"],
                "ticker": rc["ticker"],
                "sector": sector,
                "tier": "canary",
                "off_corporate_leverage_axis": sector == BANK_SECTOR,
                "composite": rc["composite"],
                "canary_score": rc["canary_score"],
                "ai_tagged": rc["ai_tagged"],
                "debt_notional_usd": rc["debt_notional_usd"],
                "near_term_notional_usd": rc["near_term_notional_usd"],
                "max_coupon": rc["max_coupon"],
                "source_uri_count": rc["source_uri_count"],
                "signatures": rc["signatures"],
                "seed_hypotheses": seed_notes(rc),
            }
        )

    # priority order: canaries first (fail first), then beams (systemic), then mid
    tier_order = {"canary": 0, "beam": 1, "mid": 2}
    targets.sort(key=lambda t: (tier_order[t["tier"]], -t.get("canary_score", t["composite"])))

    out = {
        "as_of": data["as_of"],
        "source": "analysis/economy_wide_fragility_map.json",
        "selection": {
            "inclusion_composite": INCLUSION_COMPOSITE,
            "canary_composite": CANARY_COMPOSITE,
            "canary_max_debt_usd": CANARY_MAX_DEBT,
            "beam_min_debt_usd": BEAM_MIN_DEBT,
            "note": "canary-over-beam: small high-signature names weighted up, never dropped",
        },
        "counts": {
            "total": len(targets),
            "canary_universe_total": data.get("canary_count", 0),
            "canary": sum(1 for t in targets if t["tier"] == "canary"),
            "beam": sum(1 for t in targets if t["tier"] == "beam"),
            "mid": sum(1 for t in targets if t["tier"] == "mid"),
            "banks_separate_track": sum(1 for t in targets if t["off_corporate_leverage_axis"]),
        },
        "targets": targets,
    }
    OUT_JSON.write_text(json.dumps(out, indent=2))
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")
    print(f"  {out['counts']}")


if __name__ == "__main__":
    main()
