"""CLI wrapper: print the residual collateral-scope gap coverage summary.

Read-only progression metric for the collateral-scope remediation. Loads the latest
live materiality decisions and prints the root-cause breakdown (snippet-selection
misses vs first-lien detection misses). See
``bubble.quality.collateral_scope_coverage`` for the pure, unit-tested logic.
"""

from __future__ import annotations

import csv
import glob
import json
from pathlib import Path

from bubble.quality.collateral_scope_coverage import summarize_collateral_scope_coverage


def _load_decisions(reports_dir: Path) -> list[dict[str, str]]:
    matches = glob.glob(str(reports_dir / "materiality_adjudication_decisions.csv"))
    if not matches:
        raise FileNotFoundError(f"no materiality_adjudication_decisions.csv under {reports_dir}")
    with open(matches[0], newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    summary = summarize_collateral_scope_coverage(_load_decisions(Path("data/reports")))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
