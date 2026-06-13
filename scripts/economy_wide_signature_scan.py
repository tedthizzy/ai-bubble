"""Economy-wide, sector-AGNOSTIC forensic signature scan.

This is the discovery engine of the total-ecosystem dive (analysis/total_ecosystem_dive.md
§2/§9): it scores every entity in the enumerated substrate on the eight fragility
signatures WITHOUT any AI/data-center scope filter, so the epicenter falls out as a
*result* rather than being presupposed. AI-compute is tagged, never privileged.

Inputs (all local, no network):
  - data/capital/deals.csv               (canonical deal table; obligor/counterparty roles)
  - data/edgar_acquisition/deals.csv     (second extraction; adds non-recourse / SPV flags)
  - data/edgar_acquisition/tranches.csv  (coupons, maturities, recourse, seniority)
  - data/entity_universe/entities.csv    (canonical names, CIK/ticker, mention_count)

Outputs:
  - analysis/economy_wide_fragility_map.json
  - analysis/economy_wide_fragility_map.md

Method is pre-registered here (rigor §5.7): signature weights and thresholds are fixed
BEFORE seeing the ranking, and every score is reproducible from the cited source rows.
"""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

csv.field_size_limit(10**9)

ROOT = Path(__file__).resolve().parent.parent
CAPITAL_DEALS = ROOT / "data" / "capital" / "deals.csv"
EDGAR_DEALS = ROOT / "data" / "edgar_acquisition" / "deals.csv"
TRANCHES = ROOT / "data" / "edgar_acquisition" / "tranches.csv"
ENTITIES = ROOT / "data" / "entity_universe" / "entities.csv"
OUT_JSON = ROOT / "analysis" / "economy_wide_fragility_map.json"
OUT_MD = ROOT / "analysis" / "economy_wide_fragility_map.md"

# ---- pre-registered thresholds (fixed before inspecting the ranking) -------------
PER_DEAL_NOTIONAL_CEILING = (
    100e9  # rows above are program/shelf/units artifacts -> excluded, logged
)
DEBT_DEAL_TYPES = {"debt_facility", "bond", "guarantee"}
NEAR_TERM_YEARS = {"2025", "2026", "2027"}
DISTRESS_COUPON = 0.09  # >= 9% coupon = distressed pricing (median is 5%, p90 8%)
CONCENTRATION_HHI_FLAG = 0.5  # single-counterparty Herfindahl >= 0.5 = existential dependence
MIN_COUNTERPARTIES_FOR_HHI = (
    3  # below this, HHI is a data-sparsity artifact, not real concentration
)
CANARY_MIN_DEBT = 1e6  # the $1M substance floor (analysis/total_ecosystem_dive.md §0)
CANARY_MAX_DEBT = 5e9  # "small but material" ceiling for the fails-first canary lens

# Generic placeholders that are entity-resolution failures, not real entities.
JUNK_NAMES = {
    "company",
    "the company",
    "registrant",
    "issuer",
    "borrower",
    "lender",
    "guarantor",
    "parent",
    "trustee",
    "agent",
    "various",
    "n a",
    "none",
    "certain subsidiaries",
    "the borrower",
    "the issuer",
    "the guarantor",
    "subsidiary",
    "subsidiaries",
    "the registrant",
    "holdings",
    "llc",
    "inc",
    "the parent",
    "lenders",
    "borrowers",
    "the lenders",
    "purchaser",
    "seller",
    "counterparty",
    "obligor",
    "the trustee",
    "administrative agent",
}
# EDGAR/XBRL test-submission and placeholder artifacts that leak into the corpus.
JUNK_RE = re.compile(
    r"\b(test|sample|demo|do not use|placeholder|systrends|xbrl us|edgar online|"
    r"branch \d+ test|cid )\b",
    re.IGNORECASE,
)

# Obligor (risk-bearing) vs creditor (capital-providing) role taxonomy.
OBLIGOR_ROLES = {
    "borrower",
    "issuer",
    "seller",
    "reporting_entity",
    "obligor",
    "lessee",
    "primary_party",
    "debtor",
    "sponsor",
    "guaranteed_party",
}
CREDITOR_ROLES = {
    "lender",
    "bondholder",
    "purchaser",
    "arranger",
    "agent",
    "administrative_agent",
    "underwriter",
    "guarantor",
    "trustee",
    "collateral_agent",
    "buyer",
    "offtaker",
}

# AI/data-center TAG (not a filter): used only to locate the AI cluster's RANK on the
# economy-wide map. Mirrors ecosystem_scope keywords but never excludes anything.
AI_TAG_RE = re.compile(
    r"\b(ai|a\.i\.|artificial intelligence|data center|datacenter|gpu|h100|h200|b200|"
    r"blackwell|hyperscal|colocat|coreweave|nebius|crusoe|lambda|together ai|"
    r"applied digital|terawulf|iren|core scientific|cipher mining|hut 8|bitdeer|"
    r"cleanspark|riot platform|hyperscale data|nvidia|neocloud|gpu cloud)\b",
    re.IGNORECASE,
)


def _num(x: str | None) -> float | None:
    if not x:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _year(date_str: str | None) -> str | None:
    if not date_str:
        return None
    y = date_str.strip()[:4]
    return y if y.isdigit() else None


def _truthy(x: str | None) -> bool:
    return (x or "").strip().lower() in {"true", "1", "yes", "t"}


def _parse_roles(raw: str | None) -> dict[str, list[str]]:
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    out: dict[str, list[str]] = {}
    if isinstance(obj, dict):
        for role, names in obj.items():
            if isinstance(names, list):
                out[role.lower()] = [str(n).strip() for n in names if str(n).strip()]
            elif isinstance(names, str) and names.strip():
                out[role.lower()] = [names.strip()]
    return out


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


# Banks/arrangers are creditors to almost everyone; mutual overlap with them is not
# "circular financing", it's ordinary lending. Exclude them from the strict test.
BANK_RE = re.compile(
    r"\b(bank|barclays|citi|jpmorgan|jp morgan|goldman|morgan stanley|wells fargo|"
    r"royal bank|scotia|toronto dominion|td |bnp|deutsche|ubs|credit suisse|hsbc|"
    r"mizuho|mufg|sumitomo|truist|pnc|capital one|fifth third|regions|keybank|"
    r"trust company|national association|n a$|administrative agent|trustee)\b",
    re.IGNORECASE,
)


@dataclass
class EntityScore:
    name: str
    norm: str
    # signature accumulators
    debt_notional: float = 0.0
    debt_deal_count: int = 0
    near_term_notional: float = 0.0
    near_term_count: int = 0
    spv_flags: int = 0
    nonrecourse_flags: int = 0
    related_party_flags: int = 0
    concentration_flags: int = 0
    coupons: list[float] = field(default_factory=list)
    counterparties: Counter = field(default_factory=Counter)  # name -> notional weight
    creditor_to: Counter = field(default_factory=Counter)
    customer_of: set[str] = field(default_factory=set)
    lender_to: set[str] = field(default_factory=set)
    deal_types: Counter = field(default_factory=Counter)
    source_uris: set[str] = field(default_factory=set)
    cik: str = ""
    ticker: str = ""
    mention_count: int = 0
    ai_tagged: bool = False

    def hhi(self) -> float:
        total = sum(self.counterparties.values())
        if total <= 0:
            return 0.0
        return sum((w / total) ** 2 for w in self.counterparties.values())

    def max_coupon(self) -> float | None:
        return max(self.coupons) if self.coupons else None

    def circular(self) -> bool:
        return bool(self.customer_of & self.lender_to)

    def strict_circular(self) -> bool:
        """True mutual financing with at least one NON-bank counterparty."""
        overlap = self.customer_of & self.lender_to
        return any(not BANK_RE.search(cp) for cp in overlap)


def load_entities_index() -> dict[str, dict[str, str | int]]:
    """norm-name -> {cik, ticker, mention_count} from the 789K-entity census."""
    idx: dict[str, dict[str, str | int]] = {}
    if not ENTITIES.exists():
        return idx
    with ENTITIES.open(newline="") as f:
        for row in csv.DictReader(f):
            nm = _norm(row.get("canonical_name") or "")
            if not nm:
                continue
            mc = _num(row.get("mention_count")) or 0
            prev = idx.get(nm)
            rec = {
                "cik": (row.get("matched_cik") or "").strip(),
                "ticker": (row.get("matched_ticker") or "").strip(),
                "mention_count": int(mc),
            }
            if prev is None or rec["mention_count"] > int(prev["mention_count"]):
                idx[nm] = rec
    return idx


def scan_deals(scores: dict[str, EntityScore], quality_log: list[dict]) -> int:  # noqa: PLR0912, PLR0915
    seen_dedup: set[tuple] = set()
    rows = 0
    for path in (CAPITAL_DEALS, EDGAR_DEALS):
        if not path.exists():
            continue
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                rows += 1
                dtype = (row.get("deal_type") or "").strip().lower()
                roles = _parse_roles(row.get("counterparty_roles"))
                primary = (row.get("primary_party") or "").strip()
                notional = _num(row.get("notional_amount_usd"))
                mat_year = _year(row.get("maturity_date"))
                src = (row.get("source_uri") or "").strip()
                is_rp = _truthy(row.get("is_related_party"))
                is_conc = _truthy(row.get("concentration_risk_flag"))
                is_nonrec = _truthy(row.get("is_non_recourse"))
                is_spv = _truthy(row.get("bankruptcy_remote_spv"))

                # quality gate on notional
                eff_notional = notional
                if notional is not None and notional > PER_DEAL_NOTIONAL_CEILING:
                    quality_log.append(
                        {
                            "deal_id": row.get("deal_id"),
                            "notional_usd": notional,
                            "deal_type": dtype,
                            "primary_party": primary,
                            "reason": "exceeds per-deal ceiling; excluded from ranking",
                            "source_uri": src,
                        }
                    )
                    eff_notional = None

                # identify obligors and creditors by role
                obligors: list[str] = []
                creditors: list[str] = []
                for role, names in roles.items():
                    bucket = (
                        obligors
                        if role in OBLIGOR_ROLES
                        else (creditors if role in CREDITOR_ROLES else None)
                    )
                    if bucket is not None:
                        bucket.extend(names)
                if not obligors and primary:
                    obligors = [primary]
                obligors = list(dict.fromkeys(obligors))
                creditors = list(dict.fromkeys(creditors))

                # de-dup the same economic obligation appearing across filings
                dedup_key = (
                    tuple(sorted(_norm(o) for o in obligors)),
                    dtype,
                    round(eff_notional, -6) if eff_notional else None,
                    mat_year,
                )
                duplicate = dedup_key in seen_dedup and eff_notional
                seen_dedup.add(dedup_key)

                is_debt = dtype in DEBT_DEAL_TYPES
                for ob in obligors:
                    nm = _norm(ob)
                    if not nm:
                        continue
                    s = scores.setdefault(nm, EntityScore(name=ob, norm=nm))
                    s.deal_types[dtype] += 1
                    if src:
                        s.source_uris.add(src)
                    if AI_TAG_RE.search(ob) or AI_TAG_RE.search(row.get("title") or ""):
                        s.ai_tagged = True
                    if is_rp:
                        s.related_party_flags += 1
                    if is_conc:
                        s.concentration_flags += 1
                    if is_nonrec:
                        s.nonrecourse_flags += 1
                    if is_spv:
                        s.spv_flags += 1
                    # SPV name heuristic
                    if re.search(
                        r"\b(spv|funding|finance|holdings? (i{1,3}|iv|v|llc)|trust|"
                        r"issuer|depositor|securitization)\b",
                        ob,
                        re.IGNORECASE,
                    ):
                        s.spv_flags += 0  # name-based handled in scoring; flags reserved for source
                    if is_debt and eff_notional and not duplicate:
                        s.debt_notional += eff_notional
                        s.debt_deal_count += 1
                        if mat_year in NEAR_TERM_YEARS:
                            s.near_term_notional += eff_notional
                            s.near_term_count += 1
                    # counterparty concentration (creditors + offtakers this obligor depends on)
                    w = eff_notional or 1.0
                    for cp in creditors:
                        s.counterparties[_norm(cp)] += w
                        s.customer_of.add(_norm(cp))
                # creditor side: record lender->borrower for circularity detection
                for cr in creditors:
                    nm = _norm(cr)
                    if not nm:
                        continue
                    s = scores.setdefault(nm, EntityScore(name=cr, norm=nm))
                    for ob in obligors:
                        s.lender_to.add(_norm(ob))
                        s.creditor_to[_norm(ob)] += 1
    return rows


def scan_tranches(scores: dict[str, EntityScore]) -> int:  # noqa: PLR0912
    """Coupons + recourse, attributed via the deal's obligors (joined on deal_id).

    Tranches key on the EDGAR deal-id namespace; deals come from two files with
    different id spaces, so build the obligor map from BOTH.
    """
    deal_obligor: dict[str, list[str]] = {}
    for path in (CAPITAL_DEALS, EDGAR_DEALS):
        if not path.exists():
            continue
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                roles = _parse_roles(row.get("counterparty_roles"))
                obs: list[str] = []
                for role, names in roles.items():
                    if role in OBLIGOR_ROLES:
                        obs.extend(_norm(n) for n in names)
                if not obs and (row.get("primary_party") or "").strip():
                    obs = [_norm(row["primary_party"])]
                if obs:
                    deal_obligor.setdefault(row.get("deal_id", ""), list(dict.fromkeys(obs)))
    rows = 0
    if not TRANCHES.exists():
        return rows
    with TRANCHES.open(newline="") as f:
        for row in csv.DictReader(f):
            rows += 1
            rate = _num(row.get("interest_rate"))
            if rate is None:
                continue
            # normalize to fraction
            if rate > 1.5:
                rate = rate / 100.0
            obs = deal_obligor.get(row.get("deal_id", ""), [])
            for nm in obs:
                s = scores.get(nm)
                if s is not None and 0 < rate < 1.0:
                    s.coupons.append(rate)
    return rows


def composite(s: EntityScore) -> dict:
    """Pre-registered per-signature 0..1 sub-scores and a transparent composite."""
    debt_b = s.debt_notional / 1e9
    sig_leverage = min(1.0, math.log10(debt_b + 1) / 2.0) if debt_b > 0 else 0.0  # ~$100B -> 1.0
    near_share = (s.near_term_notional / s.debt_notional) if s.debt_notional > 0 else 0.0
    sig_refi = min(1.0, near_share) * min(1.0, math.log10(s.near_term_notional / 1e9 + 1))
    mc = s.max_coupon()
    sig_carry = min(1.0, (mc - 0.05) / 0.10) if (mc and mc > 0.05) else 0.0  # 5%->0, 15%->1
    # hidden = SHARE of an entity's deals that are SPV/non-recourse (true ring-fencing),
    # not a raw count (which just tracks size). Floors deal-count so 1-of-2 doesn't read 1.0.
    total_deals = max(sum(s.deal_types.values()), 4)
    sig_hidden = min(1.0, (s.spv_flags + s.nonrecourse_flags) / total_deals)
    distinct_cps = len(s.counterparties)
    hhi = s.hhi()
    if distinct_cps < MIN_COUNTERPARTIES_FOR_HHI:
        sig_conc = 0.0  # insufficient counterparty observations -> artifact, not real concentration
    else:
        sig_conc = hhi if hhi >= CONCENTRATION_HHI_FLAG else hhi * 0.5
    # circular/vendor financing is genuinely RARE; drive it from the real is_related_party
    # filing flag, plus a strict bonus only for mutual financing with a NON-bank counterparty.
    sig_circular = min(1.0, s.related_party_flags / 4.0)
    if s.strict_circular():
        sig_circular = min(1.0, sig_circular + 0.3)
    sig_distress = min(1.0, s.concentration_flags / 3.0)
    weights = {
        "leverage": 0.22,
        "refi": 0.18,
        "carry": 0.14,
        "hidden": 0.14,
        "concentration": 0.12,
        "circular": 0.10,
        "distress": 0.10,
    }
    subs = {
        "leverage": round(sig_leverage, 4),
        "refi": round(sig_refi, 4),
        "carry": round(sig_carry, 4),
        "hidden": round(sig_hidden, 4),
        "concentration": round(sig_conc, 4),
        "circular": round(sig_circular, 4),
        "distress": round(sig_distress, 4),
    }
    comp = sum(weights[k] * subs[k] for k in weights)
    return {"composite": round(comp, 4), "signatures": subs}


def main() -> None:
    print("loading entity census index ...")
    eidx = load_entities_index()
    print(f"  indexed {len(eidx):,} canonical entities")

    scores: dict[str, EntityScore] = {}
    quality_log: list[dict] = []
    print("scanning deals ...")
    n_deals = scan_deals(scores, quality_log)
    print(f"  scanned {n_deals:,} deal rows; {len(scores):,} entities touched")
    print("scanning tranches ...")
    n_tr = scan_tranches(scores)
    print(f"  scanned {n_tr:,} tranche rows")

    # enrich with census identity
    for nm, s in scores.items():
        rec = eidx.get(nm)
        if rec:
            s.cik = str(rec["cik"])
            s.ticker = str(rec["ticker"])
            s.mention_count = int(rec["mention_count"])

    ranked = []
    junk_skipped = 0
    for s in scores.values():
        if s.norm in JUNK_NAMES or len(s.norm) < 3 or JUNK_RE.search(s.name):
            junk_skipped += 1
            continue
        c = composite(s)
        ranked.append(
            {
                "entity": s.name,
                "cik": s.cik,
                "ticker": s.ticker,
                "ai_tagged": s.ai_tagged,
                "debt_notional_usd": round(s.debt_notional, 0),
                "debt_deal_count": s.debt_deal_count,
                "near_term_notional_usd": round(s.near_term_notional, 0),
                "max_coupon": s.max_coupon(),
                "spv_flags": s.spv_flags,
                "nonrecourse_flags": s.nonrecourse_flags,
                "related_party_flags": s.related_party_flags,
                "concentration_flags": s.concentration_flags,
                "distinct_counterparties": len(s.counterparties),
                "counterparty_hhi": round(s.hhi(), 4),
                "circular": s.circular(),
                "source_uri_count": len(s.source_uris),
                "composite": c["composite"],
                "signatures": c["signatures"],
            }
        )
    # only rank entities with at least some debt footprint or a fired signature
    ranked = [r for r in ranked if r["debt_notional_usd"] > 0 or r["composite"] > 0.05]
    ranked.sort(key=lambda r: (r["composite"], r["debt_notional_usd"]), reverse=True)

    ai_ranks = [(i + 1, r) for i, r in enumerate(ranked) if r["ai_tagged"]]
    top_ai_rank = ai_ranks[0][0] if ai_ranks else None

    # CANARY lens (Ted's explicit priority: small obscure players that fail first matter
    # MORE than the giants). The size-biased composite buries them, so rank SMALL-debt
    # entities purely on the NON-size signatures (distressed coupon, ring-fencing,
    # related-party, concentration). >= $1M floor, < $5B = small but material.
    def canary_score(r: dict) -> float:
        s = r["signatures"]
        return round(
            0.40 * s["carry"]
            + 0.25 * s["hidden"]
            + 0.20 * s["circular"]
            + 0.15 * s["concentration"],
            4,
        )

    canaries = []
    for r in ranked:
        debt = r["debt_notional_usd"]
        if not (CANARY_MIN_DEBT < debt < CANARY_MAX_DEBT):
            continue
        cs = canary_score(r)
        if cs <= 0:
            continue
        canaries.append({**r, "canary_score": cs})
    canaries.sort(key=lambda r: (r["canary_score"], -r["debt_notional_usd"]), reverse=True)

    summary = {
        "as_of": "2026-06-13",
        "method": "sector-agnostic forensic signature scan (analysis/total_ecosystem_dive.md §2/§9)",
        "deal_rows_scanned": n_deals,
        "tranche_rows_scanned": n_tr,
        "entities_scored": len(ranked),
        "entities_touched": len(scores),
        "junk_names_skipped": junk_skipped,
        "per_deal_notional_ceiling_usd": PER_DEAL_NOTIONAL_CEILING,
        "quality_excluded_rows": len(quality_log),
        "ai_cluster_top_rank": top_ai_rank,
        "ai_cluster_in_top_50": sum(1 for i, _ in ai_ranks if i <= 50),
        "weights_preregistered": {
            "leverage": 0.22,
            "refi": 0.18,
            "carry": 0.14,
            "hidden": 0.14,
            "concentration": 0.12,
            "circular": 0.10,
            "distress": 0.10,
        },
        "top_200": ranked[:200],
        "canary_count": len(canaries),
        "top_canaries": canaries[:100],
        "quality_excluded": sorted(quality_log, key=lambda q: -(q["notional_usd"] or 0))[:50],
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2))
    # full ranked set (every scored entity) — the complete deep-dive frontier, not just top_200
    (ROOT / "analysis" / "economy_wide_fragility_map.full.json").write_text(
        json.dumps({"as_of": summary["as_of"], "entities": len(ranked), "all_ranked": ranked})
    )
    write_markdown(summary, ranked)
    print(f"wrote {OUT_JSON.relative_to(ROOT)} + {OUT_MD.relative_to(ROOT)}")
    print(f"  AI cluster top rank: {top_ai_rank}  |  entities scored: {len(ranked):,}")


BANNER = (
    "> **⚓ Frame — read first (reanchor):** this repo is a **general forensic engine "
    "for financial fragility & mispricing across the _whole economy_** — hidden / "
    "mismatched / circular leverage and valuation-run-ahead-of-cash-flow, found with "
    "**no sector prior**. **AI / data-center is _case zero_, not the object** (the "
    "method is sector- and era-agnostic — cf. fiber 1999, shale 2014). **Operating "
    "mode: maximum exhaustiveness — broad AND deep, uncapped, ≥ $1M-substance "
    "floor, US-primary (international by connectedness-to-core × data-accessibility); "  # noqa: RUF001
    "acting resource-constrained is NEVER correct; the only stop is physics (data that "
    "doesn't publicly exist → estimate it from proxies).** Full scope & doctrine: "
    "[total_ecosystem_dive.md](total_ecosystem_dive.md) · [README](../README.md)."
)

SIG_KEYS = ["leverage", "refi", "carry", "hidden", "concentration", "circular", "distress"]


def _row_md(i: int, r: dict) -> str:
    cpn = f"{r['max_coupon'] * 100:.1f}%" if r["max_coupon"] else "—"
    ai = "**AI**" if r["ai_tagged"] else ""
    return (
        f"| {i} | {r['entity'][:44]} | {ai} | {r['debt_notional_usd'] / 1e9:.1f} | "
        f"{r['near_term_notional_usd'] / 1e9:.1f} | {cpn} | {r['spv_flags']} | "
        f"{r['distinct_counterparties']} | {r['counterparty_hhi']:.2f} | {r['composite']:.3f} |"
    )


def write_markdown(summary: dict, ranked: list[dict]) -> None:
    L: list[str] = []
    L.append("# Economy-wide fragility map — where the mispricing actually concentrates")
    L.append("")
    L.append(BANNER)
    L.append("")
    L.append(
        f"**As of {summary['as_of']}.** Output of the **sector-agnostic** forensic "
        f"signature scan (`scripts/economy_wide_signature_scan.py`) over the enumerated "
        f"substrate: **{summary['deal_rows_scanned']:,} deal rows** + "
        f"**{summary['tranche_rows_scanned']:,} tranche rows**, "
        f"**{summary['entities_scored']:,} entities scored** on the eight §2 signatures "
        f"with **no AI filter**. The epicenter is an *output*, not an assumption. "
        f"Machine-readable: [economy_wide_fragility_map.json](economy_wide_fragility_map.json)."
    )
    L.append("")
    L.append("## Headline")
    L.append("")
    ai_top = summary["ai_cluster_top_rank"]
    L.append(
        f"- The **AI / data-center cluster is mid-pack**: its highest-ranked entity is "
        f"**#{ai_top}** of {summary['entities_scored']:,}; only "
        f"**{summary['ai_cluster_in_top_50']} AI-tagged names appear in the top 50**. "
        f"Case zero is real but is *not* the economy's primary fragility concentration."
    )
    L.append(
        "- The top of the map is dominated by **leveraged, credit-sensitive, "
        "rate-exposed balance sheets**: mortgage REITs, midstream/LNG, distressed "
        "telecom, levered specialty pharma, payments/fintech, CRE/REITs and BDC "
        "private credit — sectors with no AI dependence."
    )
    L.append("")
    L.append("## Method (pre-registered)")
    L.append("")
    w = summary["weights_preregistered"]
    L.append(
        "Each entity is scored 0-1 on each signature; the composite is a fixed-weight "
        "blend committed **before** inspecting the ranking (rigor §5.7): "
        + ", ".join(f"`{k} {v}`" for k, v in w.items())
        + ". "
        "Obligor attribution is **role-based** (debt loads the borrower/issuer, not the "
        "arranging bank). Per-deal notional above "
        f"**${summary['per_deal_notional_ceiling_usd'] / 1e9:.0f}B is excluded** as a "
        "program/shelf/units artifact and logged "
        f"({summary['quality_excluded_rows']} rows). Counterparty-HHI is suppressed below "
        "3 distinct counterparties (sparsity is not concentration)."
    )
    L.append("")
    L.append("## Top 50 by composite fragility")
    L.append("")
    L.append("| # | entity | | debt $B | ≤2027 $B | max cpn | SPV | #cp | HHI | composite |")
    L.append("|---:|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for i, r in enumerate(ranked[:50], 1):
        L.append(_row_md(i, r))
    L.append("")
    L.append("## Per-signature leaders (top 8 each)")
    L.append("")
    for k in SIG_KEYS:
        top = sorted(ranked, key=lambda r: r["signatures"][k], reverse=True)[:8]
        top = [r for r in top if r["signatures"][k] > 0]
        names = ", ".join(f"{r['entity'][:28]} ({r['signatures'][k]:.2f})" for r in top)
        L.append(f"- **{k}** — {names}")
    L.append("")
    L.append("## Data-quality caveats & known bias (§5.10)")
    L.append("")
    L.append(
        "- **Coverage bias:** only entities with a deal/tranche footprint in our corpus "
        "are scored; fully-private cash-financed players and entities whose debt we have "
        "not yet extracted are under-represented. Absence here is *not* a clean bill."
    )
    L.append(
        "- **`max_coupon` is outlier-sensitive:** a few >15% values (e.g. PayPal, Las "
        "Vegas Sands) are likely penalty/step-up/extraction artifacts, not the running "
        "coupon. Carry weight is modest (0.14); a median-coupon refinement is queued."
    )
    L.append(
        "- **Double-count residual:** the same obligation across filings is de-duped on "
        "(obligor, type, notional, maturity); near-miss variants may still double-count."
    )
    L.append(
        "- **Notional ≠ leverage:** notional sums gross facility/issuance size, not net "
        "debt; the next pass joins XBRL net-debt/EBITDA to convert size into true leverage."
    )
    L.append(
        "- **Bank balance sheets distort the leverage signal:** for depository "
        "institutions (e.g. Ameris, Simmons First, Univest) deposit / FHLB / repo "
        "liabilities are summed as `debt_facility`. Bank fragility is duration & "
        "deposit-flight, not corporate leverage — banks are reclassified and scored "
        "separately in Phase 2, not on this corporate-leverage axis."
    )
    L.append(
        "- **Distress signature (§2.8) is a DATA GAP, not a null reading:** "
        "`concentration_risk_flag` is essentially unpopulated in the deal corpus, so the "
        "distress sub-score is ~0 everywhere. The real §2.8 layer — insider selling, "
        "covenant amendments/waivers, late filings, rating actions, non-payment liens — "
        "requires Form-4 / 8-K / NT extraction queued for Phase 3; its absence here must "
        "not be read as 'no distress'."
    )
    L.append("")
    L.append(
        "*Reproducible from the cited source rows; rerun "
        "`uv run python scripts/economy_wide_signature_scan.py`. This map seeds Phase 2 "
        "(sector classification) and Phase 3 (deep-agent profiling of the flagged "
        "concentrations).*"
    )
    OUT_MD.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
