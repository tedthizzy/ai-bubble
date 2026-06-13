"""Build the COMPLETE deep-dive target set — every scored entity, not a top-N sample.

The first pass deep-dived 143 of 2,091 scored entities (the cardinal-sin retreat). This
targets ALL of them, deduped against what's already profiled, tiered and ordered by
priority (canary-first, then by composite). Emits compact per-wave payloads the workflow
can bake in. No pull — pure selection over the full ranked set already on disk.

Output: analysis/full_targets_remaining.json (+ per-wave compact files)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FULL = ROOT / "analysis" / "economy_wide_fragility_map.full.json"
DONE = ROOT / "analysis" / "phase3_findings.json"
SECTOR_SCRIPT = ROOT / "scripts"
OUT = ROOT / "analysis" / "full_targets_remaining.json"
WAVE_DIR = ROOT / "analysis" / "deepdive_waves"
WAVE_SIZE = 450  # ~900 agents/wave, under the 1000/workflow cap

import sys  # noqa: E402

sys.path.insert(0, str(SECTOR_SCRIPT))
from classify_fragility_sectors import classify  # noqa: E402


def _norm(name: str) -> str:
    head = re.split(r"\s*[(\[]", name, maxsplit=1)[0]
    return re.sub(r"[^a-z0-9]+", " ", head.lower()).strip()[:40]


def seed_notes(r: dict) -> list[str]:
    s = r["signatures"]
    n = []
    if s["leverage"] >= 0.7:
        n.append(f"large debt (${r['debt_notional_usd'] / 1e9:.0f}B gross)")
    if s["refi"] >= 0.5:
        n.append(f"near-term refi (${r['near_term_notional_usd'] / 1e9:.0f}B <=2027)")
    if s["carry"] >= 0.4 and r["max_coupon"]:
        n.append(f"distressed coupon up to {r['max_coupon'] * 100:.1f}%")
    if s["hidden"] >= 0.3:
        n.append(f"structured/ring-fenced ({r['spv_flags']} flags)")
    if s["concentration"] >= 0.4:
        n.append(f"counterparty HHI {r['counterparty_hhi']:.2f}")
    if s["circular"] >= 0.3:
        n.append("related-party/circular")
    return n


def main() -> None:
    full = json.loads(FULL.read_text())["all_ranked"]
    done_keys = {_norm(f["entity"]) for f in json.loads(DONE.read_text())["findings"]}

    remaining = []
    for r in full:
        if _norm(r["entity"]) in done_keys:
            continue
        sector = classify(r["entity"], r["ai_tagged"])
        debt = r["debt_notional_usd"]
        s = r["signatures"]
        nonsize = 0.40 * s["carry"] + 0.25 * s["hidden"] + 0.20 * s["circular"] + 0.15 * s["concentration"]
        is_canary = 1e6 < debt < 5e9 and nonsize > 0.15
        remaining.append({
            "entity": r["entity"], "ticker": r["ticker"], "cik": r["cik"],
            "sector": sector,
            "tier": "canary" if is_canary else ("beam" if debt >= 20e9 else "mid"),
            "ai_tagged": r["ai_tagged"],
            "debt_notional_usd": debt, "near_term_notional_usd": r["near_term_notional_usd"],
            "max_coupon": r["max_coupon"],
            "signatures": {k: round(v, 2) for k, v in s.items() if v > 0},
            "seed_hypotheses": seed_notes(r),
            "_prio": (0 if is_canary else 1, -r["composite"]),
        })
    remaining.sort(key=lambda t: t["_prio"])
    for t in remaining:
        del t["_prio"]

    OUT.write_text(json.dumps({"remaining": len(remaining), "targets": remaining}, indent=2))
    # split into waves
    WAVE_DIR.mkdir(exist_ok=True)
    n_waves = (len(remaining) + WAVE_SIZE - 1) // WAVE_SIZE
    for w in range(n_waves):
        chunk = remaining[w * WAVE_SIZE:(w + 1) * WAVE_SIZE]
        (WAVE_DIR / f"wave_{w + 2:02d}.json").write_text(json.dumps(chunk))
    print(f"remaining to deep-dive: {len(remaining)} (after {len(done_keys)} done)")
    print(f"split into {n_waves} waves of <= {WAVE_SIZE} in {WAVE_DIR.relative_to(ROOT)}/")
    from collections import Counter
    print("tiers:", dict(Counter(t["tier"] for t in remaining)))


if __name__ == "__main__":
    main()
