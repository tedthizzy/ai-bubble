"""Graph name-sanity gate (RC4): reject role-leak / covenant-phrase node names.

The capital-exposure graph occasionally turns a covenant clause or a bare role word
("Subsidiary Guarantor", "the Existing Borrower", "Company as obligor or any guarantor")
into a counterparty node, and leaked test ids ("test1") slip in. This gate flags those
exact malformed strings while preserving genuine named SPV / financing LLCs that happen
to contain a role word ("Boost Newco Borrower, LLC", "SABRE FINANCIAL BORROWER, LLC").

Discriminator: a name is a REAL entity if it ends in a corporate suffix (LLC / Inc / LP /
N.A. / ...) AND carries at least one distinguishing token that is not a generic role /
article / connective word. A bare role word, a covenant phrase, a truncated fragment, or a
test id is malformed. Pure function; intended as a parity check on graph rebuild.
"""

from __future__ import annotations

import re

_ROLE = re.compile(
    r"\bnoteholders?\b|\blenders?\b|\bborrowers?\b|\bguarantors?\b|party thereto|as agent"
    r"|as trustee|obligor|resigning|subsidiary guarantor|existing borrower|swingline|l/c issuer",
    re.I,
)
# A corporate token ANYWHERE in the string marks a real entity (a trailing descriptive
# clause -- "..., a Delaware limited liability company" / "(as Agent)" -- must not hide it).
# Letter-lookarounds (not \b) so dot-ending suffixes like "B.V." / "N.A." still match.
_CORP_TOKEN = re.compile(
    r"(?<![A-Za-z])(?:LLC|L\.L\.C\.|Inc\.?|Incorporated|L\.?P\.?|Ltd\.?|Limited|PLC|Corp\.?"
    r"|Corporation|N\.A\.|N\.V\.|GmbH|S\.A\.|AG|Company|Bank|Trust|Association|Partnership"
    # International corporate suffixes (ownership / non-US SPVs).
    r"|B\.V\.|SCSp|S\.C\.A\.|S\.A\.S\.|S\.p\.A\.|S\.r\.l\.|ULC|Pty"
    r"|S\.?\s?[aà]\s?r\.?\s?l)(?![A-Za-z])",  # incl. Luxembourg S.a r.l. / S.A R.L.
    re.I,
)
# Generic vocabulary that does NOT distinguish a real entity name.
_GENERIC = {
    "borrower",
    "borrowers",
    "guarantor",
    "guarantors",
    "lender",
    "lenders",
    "the",
    "company",
    "as",
    "obligor",
    "or",
    "any",
    "to",
    "subsidiary",
    "initial",
    "resigning",
    "additional",
    "replacing",
    "bank",
    "agent",
    "and",
    "existing",
    "party",
    "thereto",
    "newco",
    "financial",
    "service",
    "provider",
    "by",
    "tenant",
    "royal",
    "mezz",
    "llc",
    "inc",
    "lp",
    "ltd",
    "plc",
    "corp",
    "co",
    "n.a.",
    "of",
    "from",
    "trustee",
    "swingline",
}
# Obvious leaked test ids.
_TEST = re.compile(r"^test\d*$", re.I)


def _distinguishing_tokens(name: str) -> bool:
    """True if the name has a token that is not a generic role/article/connective word."""

    tokens = re.findall(r"[A-Za-z0-9.&]+", name.lower())
    return any(token not in _GENERIC for token in tokens)


def is_real_named_entity(name: str) -> bool:
    """A real entity: a corporate token plus at least one distinguishing (non-generic) token."""

    return bool(_CORP_TOKEN.search(name or "")) and _distinguishing_tokens(name or "")


def is_malformed_entity_name(name: str) -> bool:
    """True if the graph node name is a role-leak / covenant fragment / test id."""

    text = (name or "").strip()
    if not text:
        return True
    if _TEST.match(text):
        return True
    if not _ROLE.search(text):
        return False
    # A role word is present: malformed unless it is a genuine named entity.
    return not is_real_named_entity(text)
