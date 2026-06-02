"""Strict indirect-supplier linkage rule (relevance scope, indirect tier).

Utilities / telecom / midstream are INDIRECT AI/data-center suppliers: their debt is
general-purpose unless the filing ties it to data-center demand. Sector membership alone
is not evidence (a blanket include adds hundreds of $B of unlinked utility debt). This
rule admits an indirect supplier to `watchlist` only when its debt quote *names* a data
center / hyperscale / colocation facility, or a hyperscaler in a power/capacity context.

Pure predicate; intended as the gate behind an indirect-supplier retag, not an auto-retag.
"""

from __future__ import annotations

import re

# Explicit data-center infrastructure language -> qualifies on its own.
_DC_INFRA = re.compile(r"data ?cent(er|re)|hyperscal|colocation|colo facilit|gpu cluster", re.I)

# A named hyperscaler...
_HYPERSCALER = re.compile(
    r"\b(microsoft|amazon|aws|amazon web services|google|alphabet|meta|oracle|openai"
    r"|anthropic|nvidia|coreweave)\b",
    re.I,
)
# ...in a power / capacity / offtake context (so a back-office vendor mention does not count).
_POWER_CONTEXT = re.compile(
    r"power purchase agreement|\bppa\b|offtake|gigawatt|\bgw\b|megawatt|\bmw\b"
    r"|capacity (segment|agreement|commitment)|load growth|behind-the-meter",
    re.I,
)


def is_quote_evidenced_dc_linkage(quote: str) -> bool:
    """True if the quote evidences a data-center / hyperscaler linkage (not sector alone)."""

    text = quote or ""
    if _DC_INFRA.search(text):
        return True
    return bool(_HYPERSCALER.search(text) and _POWER_CONTEXT.search(text))
