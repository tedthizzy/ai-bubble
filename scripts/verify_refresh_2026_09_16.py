#!/usr/bin/env python3
"""Reproduce the dated research calculations without network calls or writes."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    evidence = root / "analysis/refresh_2026-09-16.json"
    notebook = root / "analysis/refresh_2026-09-16.ipynb"
    data = json.loads(evidence.read_text())
    document = json.loads(notebook.read_text())
    assert document["nbformat"] == 4 and document["nbformat_minor"] == 5
    assert document["metadata"]["validation"]["input_sha256"] == hashlib.sha256(
        evidence.read_bytes()
    ).hexdigest(), "Frozen evidence changed; review and rerun the notebook."

    identifiers = [cell["id"] for cell in document["cells"]]
    assert len(identifiers) == len(set(identifiers)), "Duplicate notebook cell IDs."
    namespace: dict = {}
    executed = 0
    previous_directory = Path.cwd()
    try:
        os.chdir(root)
        for cell in document["cells"]:
            assert cell["cell_type"] in {"code", "markdown"}
            assert isinstance(cell["source"], list)
            if cell["cell_type"] != "code":
                continue
            executed += 1
            assert cell["execution_count"] == executed
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                exec(
                    compile("".join(cell["source"]), str(notebook), "exec"),
                    namespace,
                )
            assert all(
                output["output_type"] == "stream" and output["name"] == "stdout"
                for output in cell["outputs"]
            )
            expected = "".join(
                "".join(output["text"]) for output in cell["outputs"]
            )
            assert captured.getvalue() == expected, f"Output changed: {cell['id']}"
    finally:
        os.chdir(previous_directory)

    series = data["market"]["fred_evidence"]
    print(f"PASS: {executed} notebook code cells reproduced saved outputs.")
    print(
        f"PASS: {sum(len(item['observations']) for item in series.values())} "
        "FRED observations across 3 series; 6 BDC prices/NAVs; 5 EDGAR search hits."
    )
    print("S2: confirming +2.04pp. S3: contra +1.5pp. CONFIRM-2: false.")
    print("40 GW at $20M/MW-year: $800B annual rate; uniform H2 arrivals: $200B.")
    print("Jupyter kernel/rendering, live graph and deployment were not verified.")


if __name__ == "__main__":
    main()
