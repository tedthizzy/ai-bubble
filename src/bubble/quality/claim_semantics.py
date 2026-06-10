"""Claim-semantics gate dimension (separate from provenance).

The EvidenceGate scores provenance (source-backed / quote-backed / corroborated), so
a webcast-boilerplate or balance-sheet figure can earn high (0.78) confidence merely
by appearing in a real filing. This module adds the orthogonal dimension: does the
quote *semantically* describe the issuer's committed debt obligation?

``classify_claim_semantics`` buckets a quote as ``committed_debt`` /
``asset_or_capacity`` / ``boilerplate_only`` / ``indeterminate``.
``semantic_gate_confidence`` combines a provenance confidence with that bucket so a
quote-backed-but-semantically-wrong figure is capped low instead of trusted. Pure
functions; wiring this into the production gate is Codex's.
"""

from __future__ import annotations

from typing import Any

from bubble.quality.asset_leakage import HIGH_CONFIDENCE_ASSET_MARKERS

# Affirmative committed-debt-obligation signals.
COMMITTED_DEBT_MARKERS = (
    "credit agreement",
    "term loan",
    "revolving credit",
    "revolving facility",
    "senior notes",
    "secured notes",
    "senior unsecured",
    "unsecured notes",
    "notes due",
    "indenture",
    "first mortgage bond",
    "aggregate principal amount",
    "principal amount of",
    "bridge facility",
    "bridge loan",
    "loan facility",
    "debt facility",
    "promissory note",
    "debentures",
    # Collateral / guarantee / lender / rate language — strong committed-debt-agreement
    # signals beyond instrument names. Verified to resolve indeterminate rows with no
    # asset/non-debt false positives (asset markers are checked first).
    "secured by",
    "guaranteed by",
    "the guarantors",
    "lenders",
    "borrowings",
    "outstanding under",
    "drawn under",
    "applicable margin",
    "sofr",
    "libor",
    "credit facility",
    "revolving facility",
    "term facility",
    "tranche",
    "commitment fee",
    "first lien",
    "second lien",
    "senior secured",
    # Convertibles are DEBT — listed before the equity markers so a convertible note
    # mentioning "shares"/"per share" is not mis-blocked as equity.
    "convertible notes",
    "convertible senior",
    "conversion price",
    "convertible debentures",
)

# Primary non-debt subjects: an equity offering/buyback/dividend or mortgage
# origination volume. Checked AFTER committed-debt, so a debt instrument wins.
EQUITY_OR_PRODUCTION_MARKERS = (
    # equity
    "shares of our common stock",
    "shares of series",
    "common stock dividends",
    "market stand-off",
    "ordinary shares",
    "repurchase program",
    "share repurchase",
    "stock purchase agreement",
    "into shares of",
    "class a common stock",
    "per share",
    "last reported sale price",
    # mortgage production / origination volume (not corporate debt)
    "loan production",
    "loans held for sale",
    "mortgage closed loan",
    "closed loan production",
    "origination volume",
)

# Boilerplate / non-substantive text that can carry a stray number.
BOILERPLATE_MARKERS = (
    "webcast",
    "forward-looking",
    "earnings report",
    "press release",
    "does not constitute part of this prospectus",
    "information contained on",
    "replay will be available",
    # Quarterly-earnings / results-announcement headers carry a balance-sheet or
    # production figure, not a debt instrument. These are checked AFTER committed-debt,
    # so a genuine notes snippet is never affected; verified to reclassify only
    # currently-indeterminate earnings headers (PennyMac/Carrier/Central Pacific), with
    # zero overlap against any quote carrying a debt clause.
    "results of operations and financial condition",
    "reports first quarter",
    "reports second quarter",
    "reports third quarter",
    "reports fourth quarter",
    "net income attributable to",
)

# Subcategories that are debt obligations by adjudication (resolve a terse-quote
# indeterminate to committed_debt) vs non-debt categories that should not be in the
# debt-like metric at all.
DEBT_SUBCATEGORIES = (
    "contract_tranche_terms",
    "high_notional_debt_like_candidate",
    "note_offering",
    "credit_facility",
    "ownership_expanded",
)
NON_DEBT_SUBCATEGORIES = (
    "queue_project_match",
    "chip_supply_observation",
    "eps_depreciation_impact",
    "physical",
    "compute",
)

# Semantic cap applied when a quote does not affirm committed debt.
ASSET_OR_CAPACITY_CAP = 0.3
BOILERPLATE_CAP = 0.25
INDETERMINATE_CAP = 0.5


def _contains(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def classify_claim_semantics(quote: str) -> dict[str, Any]:
    """Bucket a quote by what its figure semantically represents.

    Asset/capacity wins over a co-occurring debt marker (a servicing-UPB deck may
    also say "notes"); committed-debt requires an affirmative debt marker and no
    asset/capacity marker.
    """

    text = quote or ""
    if _contains(text, HIGH_CONFIDENCE_ASSET_MARKERS):
        return {"bucket": "asset_or_capacity", "is_committed_debt": False}
    if _contains(text, COMMITTED_DEBT_MARKERS):
        return {"bucket": "committed_debt", "is_committed_debt": True}
    if _contains(text, EQUITY_OR_PRODUCTION_MARKERS):
        return {"bucket": "equity_or_production", "is_committed_debt": False}
    if _contains(text, BOILERPLATE_MARKERS):
        return {"bucket": "boilerplate_only", "is_committed_debt": False}
    return {"bucket": "indeterminate", "is_committed_debt": False}


def classify_claim_with_context(
    quote: str,
    *,
    subcategory: str = "",
    counterparty: str = "",
) -> dict[str, Any]:
    """Enrich the quote-only classification with subcategory / counterparty context.

    A terse quote that affirms neither debt nor asset (``indeterminate``) is resolved
    to ``committed_debt`` when the adjudicated subcategory is a debt type or the
    counterparty is a lender/agent, and to ``non_debt_miscategorized`` when the
    subcategory is a non-debt (physical/compute) type that should not be in the
    debt-like metric. Asset/boilerplate/committed verdicts from the quote are kept.
    """

    base = classify_claim_semantics(quote)
    if base["bucket"] != "indeterminate":
        return base

    sub = (subcategory or "").strip().lower()
    cp = (counterparty or "").strip().lower()
    if any(marker in sub for marker in NON_DEBT_SUBCATEGORIES):
        return {"bucket": "non_debt_miscategorized", "is_committed_debt": False}
    debt_cp = any(
        role in cp for role in ("lender", "agent", "bank", "trustee", "noteholder", "n.a")
    )
    if any(marker in sub for marker in DEBT_SUBCATEGORIES) or debt_cp:
        return {"bucket": "committed_debt", "is_committed_debt": True}
    return base


def semantic_gate_confidence(provenance_confidence: float, quote: str) -> dict[str, Any]:
    """Combine provenance confidence with the semantic bucket.

    Committed-debt keeps the provenance confidence; otherwise the confidence is
    capped so quote-backing alone cannot certify a semantically-wrong figure.
    """

    result = classify_claim_semantics(quote)
    bucket = result["bucket"]
    cap = {
        "committed_debt": 1.0,
        "asset_or_capacity": ASSET_OR_CAPACITY_CAP,
        "boilerplate_only": BOILERPLATE_CAP,
        "equity_or_production": ASSET_OR_CAPACITY_CAP,
        "indeterminate": INDETERMINATE_CAP,
    }[bucket]
    effective = min(provenance_confidence, cap)
    return {
        "semantic_bucket": bucket,
        "is_committed_debt": result["is_committed_debt"],
        "provenance_confidence": provenance_confidence,
        "semantic_cap": cap,
        "effective_confidence": round(effective, 4),
        "high_confidence_eligible": effective >= 0.75,
    }
