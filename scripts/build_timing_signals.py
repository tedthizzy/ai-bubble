#!/usr/bin/env python
"""Build source-backed timing signal artifacts for crack-window triage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.analysis.timing_signals import (
    build_timing_signal_batch,
    write_timing_signal_batch,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        action="append",
        type=Path,
        default=None,
        help="Data root to scan; may be supplied more than once.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/reports"))
    args = parser.parse_args()

    data_dirs = args.data_dir or [Path("data")]
    batch = build_timing_signal_batch(data_dirs)
    outputs = write_timing_signal_batch(batch, args.output_dir)
    print(json.dumps({**batch.summary.to_dict(), "outputs": outputs}, indent=2))


if __name__ == "__main__":
    main()
