#!/usr/bin/env python3
"""Render the current source-carded valuation sensitivities without network calls."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bubble.expectations.inversion import (  # noqa: E402
    DISCOUNT_RATES,
    FCF_MARGINS,
    TERMINAL_GROWTH,
    invert_all,
)
from bubble.expectations.names import AS_OF, INPUT_RECORD, NAMES, SOURCE_PATH  # noqa: E402

DOC = ROOT / "analysis" / "expectations_inversion.md"
JSON_OUT = ROOT / "viz" / "expectations.json"
LIMITS = (
    "The implied revenue multiple uses a Gordon-growth perpetuity with immediate steady-state cash flows. It does not model the ramp or near-term funding needs.",
    "Renewal-dependent share of EV is the share beyond modeled contracted cash-flow PV. New customers, expansion or other businesses can supply that value. This calculation cannot identify actual renewal dependence.",
    "Revenue uses consolidated reported trailing 12 months for every issuer. Contract measures differ between GAAP RPO, combined lease value and gross base-term rent. These measures are not directly interchangeable.",
    "Backlog is recognized uniformly over the stated assumed horizon. Construction delays, default losses and incremental capex funding are not separately modeled. The same hypothetical FCF margin grid applies to clouds and the landlord.",
    "EV and net debt use the market provider's definitions, including its lease treatment. They differ from the issuer borrowing and note carrying amounts in the financial review.",
    "These sensitivities do not measure GPU economic life, default probabilities or a calibrated bubble probability.",
)


def render_markdown(results: list[dict[str, Any]]) -> str:
    rates = ", ".join(f"{r:.0%}" for r in DISCOUNT_RATES)
    margins = ", ".join(f"{m:.0%}" for m in FCF_MARGINS)
    lines = [
        "# Expectations inversion",
        "",
        f"Reviewed through {AS_OF}. Enterprise values use the October 16 market close. Revenue and contract balances retain their stated observation dates.",
        "",
        f"The model uses discount rates {rates}, hypothetical FCF margins {margins}, and {TERMINAL_GROWTH:.0%} perpetual growth for the implied revenue multiple. The math and scenario grid are unchanged. Revenue bases now use reported consolidated trailing 12 months for all four issuers.",
        "",
        "The original June inputs remain in git and the retained refresh snapshot. The current card file is src/bubble/expectations/inputs_2026-10-17.json. It records source hashes, the exact prior-year revenue periods and the market quote comparison. scripts/review_expectations_inputs.py verifies retained source bytes before re-carding. scripts/build_expectations_inversion.py regenerates this report and viz/expectations.json.",
        "",
    ]
    for row in results:
        multiple, share = row["implied_revenue_multiple"], row["renewal_dependent_share"]
        lines += [
            f"## {row['ticker']} / {row['name']}",
            "",
            f"EV ${row['ev_usd_b']:.2f}B. Provider net debt ${row['net_debt_usd_b']:.2f}B. Reported trailing revenue ${row['current_annualized_revenue_usd_b']:.6f}B through {row['revenue_period_end']}.",
            "",
            f"Implied revenue multiple: {multiple['low']:.2f}x to {multiple['high']:.2f}x; grid median {multiple['median']:.2f}x.",
            "",
            f"Renewal-dependent share of EV: {share['low']:.1%} to {share['high']:.1%}; grid median {share['median']:.1%}.",
            "",
            row["backlog_basis"],
            "",
            row["notes"],
            "",
            "Sources: "
            + "; ".join(f"[{key}]({value})" for key, value in row["sources"].items())
            + ".",
            "",
        ]
    lines += ["## Model limits", "", *[f"- {item}" for item in LIMITS], ""]
    return "\n".join(lines)


def main() -> int:
    results = invert_all(NAMES)
    for row in results:
        source = INPUT_RECORD["evidence"][row["ticker"]]
        row["market_date"] = source["market"]["market_date"]
        row["revenue_period_end"] = source["revenue_period_end"]
        row["backlog_observed_as_of"] = "2026-10-07" if row["ticker"] == "APLD" else "2026-06-30"
    record = {
        "as_of": AS_OF,
        "market_close": INPUT_RECORD["market_close"],
        "revenue_basis": INPUT_RECORD["revenue_basis"],
        "input_record": {
            "path": str(SOURCE_PATH.relative_to(ROOT)),
            "sha256": hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest(),
        },
        "scenario_grid": {
            "discount_rates": list(DISCOUNT_RATES),
            "fcf_margins": list(FCF_MARGINS),
            "terminal_growth": TERMINAL_GROWTH,
        },
        "limits": list(LIMITS),
        "results": results,
    }
    backup = ROOT / ".codex/refresh-2026-10-17" / f"expectations-output-{time.time_ns()}"
    backup.mkdir(parents=True)
    for target in (DOC, JSON_OUT):
        if target.exists():
            shutil.copy2(target, backup / target.name)
    DOC.write_text(render_markdown(results))
    JSON_OUT.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    print(
        f"wrote {DOC.relative_to(ROOT)} + {JSON_OUT.relative_to(ROOT)}: {len(results)} names, cutoff {AS_OF}"
    )
    return 0


if __name__ == "__main__":
    from run_with_memory_budget import ensure_memory_budget

    ensure_memory_budget(512)
    sys.exit(main())
