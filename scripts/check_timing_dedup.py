"""CLI: simulate the timing-wall economic-dedup fix (the ~$493B remaining lever).

The timing builder received the mega/asset guard but not economic-obligation dedup,
so the same obligation re-disclosed across filing periods still inflates the
whole-corpus wall. This prints the corrected wall + top collapsed clusters. See
``bubble.quality.timing_wall_integrity.simulate_timing_wall_fix`` for the logic.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from bubble.quality.timing_wall_integrity import simulate_timing_wall_fix


def main() -> None:
    path = Path("data/reports/timing_signals.csv")
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    print(json.dumps(simulate_timing_wall_fix(rows), indent=2))


if __name__ == "__main__":
    main()
