#!/usr/bin/env python
"""Compatibility wrapper that builds the real-source acquisition catalog.

Graph nodes should enter production only through source-backed ingestion. This
wrapper keeps the old `just seed` command usable without inserting manual graph
entities.
"""

from __future__ import annotations

import json
from pathlib import Path

from bubble.ingestion.sources import build_seed_source_catalog


def main() -> None:
    output = Path("data/source_catalogs/source_catalog.csv")
    summary = build_seed_source_catalog(
        output,
        include_public_sources=True,
        include_dynamic_public_sources=False,
    )
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    print(f"\nSource catalog: {output}")
    print("No graph nodes were inserted. Run source acquisition and extraction next.")


if __name__ == "__main__":
    main()
