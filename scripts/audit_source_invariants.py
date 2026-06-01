#!/usr/bin/env python
"""Audit production CSV outputs for source/provenance invariant violations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bubble.quality.source_invariant_audit import (
    audit_source_invariants,
    write_source_invariant_audit,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        action="append",
        default=None,
        help="Data directory to audit. Repeatable; defaults to data.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/reports/source_invariant_audit.json"),
    )
    parser.add_argument("--max-findings", type=int, default=500)
    parser.add_argument(
        "--fail-on-violation",
        action="store_true",
        help="Exit nonzero when hard invariant violations are found.",
    )
    args = parser.parse_args()

    audit = audit_source_invariants(
        args.data_dir or ["data"],
        max_findings=args.max_findings,
    )
    output = write_source_invariant_audit(audit, args.output)
    print(json.dumps(audit.to_dict(), indent=2, sort_keys=True))
    print(f"\nSource invariant audit: {output}")
    if args.fail_on_violation and not audit.passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
