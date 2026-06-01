"""
Simple but powerful CLI for bubble.

Usage examples:
    uv run bubble ingest 0000789019
    uv run bubble report 0000789019
    uv run bubble ui
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Callable

import typer

from bubble.graph.client import get_graph_client
from bubble.ingestion.edgar.extractor import EdgarExtractor

_report_path = Path(__file__).parent.parent.parent / "scripts" / "run_burry_report.py"
_spec = importlib.util.spec_from_file_location("run_burry_report", _report_path)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Could not load report script from {_report_path}")
_run_burry_report = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_run_burry_report)
_report_module = _run_burry_report

app = typer.Typer(help="bubble — Michael Burry-style AI infrastructure forensic mapper")


@app.command()
def ingest(cik: str = "0000789019") -> None:
    """Ingest a public filer and run the full extraction pipeline into the graph."""
    extractor = EdgarExtractor()
    result = extractor.extract_from_cik(cik)
    ent = result["entity"]
    graph = get_graph_client()
    graph.merge_entity(ent)
    for d in result.get("deals", []):
        graph.merge_deal(d)
    typer.echo(f"Ingested {ent.name} with {len(result.get('risks', []))} risks.")


@app.command()
def report(cik: str = "0000789019") -> None:
    """Generate and print a full Burry-style forensic report."""
    module = _report_module
    main_func = cast("Any", module).main
    if not callable(main_func):
        raise RuntimeError("run_burry_report.py does not expose a callable main")
    typed_main = cast("Callable[[str], None]", main_func)
    typed_main(cik)


@app.command()
def ui() -> None:
    """Launch the Streamlit forensic cockpit."""
    subprocess.run(["streamlit", "run", "src/bubble/ui/streamlit_app.py"], check=False)


@app.command()
def demo() -> None:
    """Run the complete local demo (no Docker/LLM keys required)."""
    report("0000789019")


if __name__ == "__main__":
    app()
