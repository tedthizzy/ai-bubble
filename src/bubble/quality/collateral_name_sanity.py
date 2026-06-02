"""Collateral-name-sanity gate for the contract-contagion graph collateral layer.

A collateral node should carry a short security identifier ("first priority lien on
substantially all assets", "pledged equity of the Borrower"). The contract graph instead
populates ~79% of collateral names with covenant / business-description PROSE -- a BDC's
strategy paragraph, a lien-covenant clause -- each then carrying a deal's notional. This gate
flags those so the rebuild can drop them or re-home the notional to the deal's real security.

``is_prose_collateral_name`` is the predicate; ``summarize_collateral_name_sanity`` aggregates
prose count + notional over a node set. Pure functions; the proposed rebuild gate for the
``SECURED_BY_COLLATERAL`` layer (the only relationship the prose defect contaminates).
"""

from __future__ import annotations

import re
from typing import Any

# Sentence-like covenant / business-description markers (a collateral id has none of these).
_PROSE = re.compile(
    r"\b(we |our |provided that|in connection with|shall (be|have)|pursuant to|from time to time"
    r"|we believe|we focus|rank (ahead|equally)|may (incur|be)|including any|in the form of"
    r"|for the benefit of|to the extent|with respect to the|as defined in|notwithstanding)\b",
    re.I,
)
_MAX_IDENTIFIER_LEN = 120
_MIN_PROSE_LEN = 40


def is_prose_collateral_name(name: str) -> bool:
    """True if the collateral node name is covenant/business prose, not a security identifier."""

    text = (name or "").strip()
    if not text:
        return False
    if len(text) > _MAX_IDENTIFIER_LEN:
        return True
    return bool(_PROSE.search(text)) and len(text) > _MIN_PROSE_LEN


def _amount(value: str) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def summarize_collateral_name_sanity(
    nodes: list[dict[str, str]],
    *,
    name_key: str = "name",
    amount_key: str = "notional_usd",
    type_key: str = "node_type",
    collateral_type: str = "collateral",
) -> dict[str, Any]:
    """Count prose collateral names + their notional over a contract-graph node set."""

    total = 0
    prose = 0
    prose_notional = 0.0
    total_notional = 0.0
    for node in nodes:
        if (node.get(type_key) or "") != collateral_type:
            continue
        total += 1
        amount = _amount(node.get(amount_key, ""))
        total_notional += amount
        if is_prose_collateral_name(node.get(name_key, "")):
            prose += 1
            prose_notional += amount
    return {
        "collateral_nodes": total,
        "prose_collateral_nodes": prose,
        "prose_pct": round(prose / total, 4) if total else 0.0,
        "prose_notional_usd": round(prose_notional, 2),
        "total_collateral_notional_usd": round(total_notional, 2),
    }
