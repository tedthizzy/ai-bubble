"""Entity-name quality filters used by source-backed analysis outputs."""

from __future__ import annotations

import re

GENERIC_ENTITY_PATTERNS = (
    re.compile(r"^lenders?( party thereto)?$", re.I),
    re.compile(r"^noteholders?$", re.I),
    re.compile(r"^bondholders?$", re.I),
    re.compile(r"^holders?( of .*)?$", re.I),
    re.compile(r"^purchasers?$", re.I),
    re.compile(r"^initial purchasers?$", re.I),
    re.compile(r"^several purchasers?$", re.I),
    re.compile(r"^counterpart(y|ies)$", re.I),
    re.compile(r"^agents?$", re.I),
    re.compile(r"^trustees?$", re.I),
    re.compile(r"^guarantors?$", re.I),
    re.compile(r"^borrowers?$", re.I),
    re.compile(r"^lessees?$", re.I),
    re.compile(r"^lessors?$", re.I),
    re.compile(r"^seller$", re.I),
    re.compile(r"^buyer$", re.I),
    re.compile(r"^company$", re.I),
    re.compile(r"^inc\.?$", re.I),
    re.compile(r"^ltd\.?$", re.I),
    re.compile(r"^llc\.?$", re.I),
    re.compile(r"^corp\.?$", re.I),
    re.compile(r"^co\.?$", re.I),
    re.compile(r"^n\.?a\.?$", re.I),
    re.compile(r"^association$", re.I),
    re.compile(r"^corporation$", re.I),
    re.compile(r"^parent$", re.I),
    re.compile(r"^the company$", re.I),
    re.compile(r"^form t-1\b", re.I),
    re.compile(r"\bsignature pages\b", re.I),
    re.compile(r"\beligibility of\b", re.I),
    re.compile(r"\balso acts\b", re.I),
    re.compile(r"\bmay act\b", re.I),
    re.compile(r"\bin addition to acting\b", re.I),
    re.compile(r"\bacting$", re.I),
    re.compile(r"^the banks?, financial institutions\b", re.I),
    re.compile(r"^banks? named therein\b", re.I),
    re.compile(r"^lenders? (parties )?thereto and\b", re.I),
    re.compile(r"^lenders? and\b", re.I),
    re.compile(r"^us and\b", re.I),
    re.compile(r"\bcertain lenders\b", re.I),
    re.compile(r"\bas successor to\b", re.I),
    re.compile(r"\bas lenders?, and (the )?agent\b", re.I),
    re.compile(r"\band the bank of\b", re.I),
    re.compile(r"\band bank of new york mellon trust\b", re.I),
    re.compile(
        r"^.+,\s*(citibank|bank of america|jpmorgan|wells fargo|mizuho|mufg|"
        r"hsbc|barclays|pnc bank|u\.?s\.? bank)\b",
        re.I,
    ),
    re.compile(r"\band solely\b", re.I),
    re.compile(r"\blenders named therein\b", re.I),
    re.compile(r"\bcompany and\b", re.I),
    re.compile(r"\band u\.?s\.? bank\b", re.I),
    re.compile(r"\band wilmington trust\b", re.I),
    re.compile(r"\bguarantors? party thereto\b", re.I),
    re.compile(r"\bother borrowers\b", re.I),
    re.compile(r"\bparty thereto\b", re.I),
    re.compile(r"\bis engaged\b", re.I),
    re.compile(r"\bmade by a guarantor under a guarantee\b", re.I),
)

ENTITY_SUFFIX_TOKENS = {
    "co",
    "company",
    "corp",
    "corporation",
    "inc",
    "incorporated",
    "llc",
    "ltd",
    "limited",
    "plc",
}


def is_generic_entity_name(name: str) -> bool:
    """Return True when a string is not a usable named entity."""

    normalized = " ".join(name.strip().split())
    if len(normalized) <= 2:
        return True
    if len(normalized) > 100 or len(normalized.split()) > 14:
        return True
    if normalized.count(",") >= 3:
        return True
    return any(pattern.search(normalized) for pattern in GENERIC_ENTITY_PATTERNS)


def canonical_entity_key(name: str) -> str:
    """Return a stable comparison key for the same legal name across variants."""

    tokens = re.sub(r"[^a-z0-9]+", " ", name.lower()).split()
    if len(tokens) >= 2 and tokens[-2:] == ["n", "a"]:
        tokens = tokens[:-2]
    while tokens and tokens[-1] in ENTITY_SUFFIX_TOKENS:
        tokens = tokens[:-1]
    return " ".join(tokens) or "unknown"
