"""CLI: print broad approved-group metric-integrity signals (read-only QA).

Quantifies the three verified over-count root causes (mega mis-extraction,
cross-filing duplication, aggregate-snapshot duplication) against approved
materiality decision groups. This is not the authoritative final representative
metric; reproduce any candidate dollar impact against the production final-metric
pipeline before changing report totals. See ``bubble.quality.metric_integrity`` for
the pure, unit-tested logic.
"""

from __future__ import annotations

import csv
import glob
import json
from pathlib import Path

from bubble.quality.metric_integrity import summarize_metric_integrity


def _load_decisions(reports_dir: Path) -> list[dict[str, str]]:
    matches = glob.glob(str(reports_dir / "materiality_adjudication_decisions.csv"))
    if not matches:
        raise FileNotFoundError(f"no materiality_adjudication_decisions.csv under {reports_dir}")
    with open(matches[0], newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    summary = summarize_metric_integrity(_load_decisions(Path("data/reports")))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
