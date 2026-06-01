#!/usr/bin/env python
"""
Complete Burry-Style Forensic Report Generator

This produces the primary artifact of the system:
A deep, skeptical, evidence-based analysis of an entity's position in the AI/data center financing ecosystem.

Usage:
    uv run python scripts/run_burry_report.py 0000789019
    bubble report 0000789019
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from bubble.analysis.capital_structure import CapitalStructureAnalyzer
from bubble.analysis.red_flags import RedFlagEngine
from bubble.analysis.scenarios import ScenarioEngine
from bubble.graph.client import get_graph_client
from bubble.ingestion.edgar.extractor import EdgarExtractor

console = Console()


def generate_report(target_cik: str) -> dict[str, Any]:
    """Run the full forensic pipeline and return a rich report dict."""
    graph = get_graph_client()
    graph.bootstrap_schema()

    extractor = EdgarExtractor()
    extraction = extractor.extract_from_cik(target_cik)

    entity = extraction["entity"]
    graph.merge_entity(entity)
    for d in extraction.get("deals", []):
        graph.merge_deal(d)

    red_engine = RedFlagEngine(graph)
    flags = red_engine.analyze_entity(
        str(entity.id), extra_context={"capex_billion": 22, "power_secured": False}
    ) + extraction.get("risks", [])

    # Auto-queue high severity items
    for f in flags:
        if f.severity >= 0.85:
            graph.add_to_review_queue(
                "Risk", str(f.id), f.title, f.severity, priority=200 if f.severity >= 0.9 else 100
            )

    scenario_engine = ScenarioEngine(graph)
    scenarios = scenario_engine.run_full_suite(str(entity.id))
    capital_metrics = CapitalStructureAnalyzer().analyze(extraction.get("deals", []))

    contagion = graph.get_contagion_paths(str(entity.id), max_depth=5)

    report = {
        "metadata": {
            "target": entity.name,
            "cik": target_cik,
            "ticker": getattr(entity, "ticker", None),
            "generated_at": datetime.now(UTC).isoformat(),
            "system_version": "0.2-complete-pipeline",
            "data_sources": ["SEC EDGAR 10-K (structured + narrative)"],
        },
        "executive_summary": {
            "overall_risk_level": max((f.severity for f in flags), default=0.5),
            "key_themes": [f.title for f in flags[:3]],
            "stress_test_summary": {
                "adverse_dscr": scenarios["adverse"].stressed_dscr,
                "tail_dscr": scenarios["tail"].stressed_dscr,
                "refinancing_risk_tail": scenarios["tail"].refinancing_risk,
            },
            "capital_structure_summary": {
                "debt_like_notional_usd": capital_metrics.debt_like_notional_usd,
                "distinct_debt_like_notional_usd": (
                    capital_metrics.distinct_debt_like_notional_usd
                ),
                "duplicate_candidate_notional_usd": (
                    capital_metrics.duplicate_candidate_notional_usd
                ),
                "aggregate_obligation_distinct_notional_usd": (
                    capital_metrics.aggregate_obligation_distinct_notional_usd
                ),
                "off_balance_sheet_usd": capital_metrics.off_balance_sheet_usd,
                "guarantee_linked_usd": capital_metrics.guarantee_linked_usd,
                "spv_or_non_recourse_usd": capital_metrics.spv_or_non_recourse_usd,
                "reviewed_debt_like_notional_usd": (
                    capital_metrics.reviewed_debt_like_notional_usd
                ),
                "pending_review_debt_like_notional_usd": (
                    capital_metrics.pending_review_debt_like_notional_usd
                ),
                "notional_review_required_usd": capital_metrics.notional_review_required_usd,
                "near_term_refinancing_usd": capital_metrics.near_term_refinancing_usd,
                "top_10_concentration_pct": capital_metrics.top_10_concentration_pct,
                "evidence_gate": capital_metrics.evidence_summary,
            },
        },
        "red_flags": [
            {
                "title": f.title,
                "category": f.category.value,
                "severity": f.severity,
                "red_flag_score": f.red_flag_score,
                "description": f.description,
                "evidence": f.evidence_quotes,
            }
            for f in sorted(flags, key=lambda x: x.severity, reverse=True)
        ],
        "stress_scenarios": {
            name: {
                "base_dscr": res.base_dscr,
                "stressed_dscr": res.stressed_dscr,
                "refinancing_risk": res.refinancing_risk,
                "top_contagion_exposure": sum(
                    p.get("estimated_exposure_usd", 0) for p in res.top_contagion_paths[:3]
                ),
            }
            for name, res in scenarios.items()
        },
        "capital_structure": capital_metrics.to_dict(),
        "contagion_analysis": contagion[:8],
        "graph_state": {
            "total_nodes": len(graph.query_nodes())
            if hasattr(graph, "query_nodes")
            else "N/A (Neo4j mode)",
            "contagion_paths_found": len(contagion),
        },
        "raw_extraction": {
            "deals_found": len(extraction.get("deals", [])),
            "risks_found": len(extraction.get("risks", [])),
            "narrative_chars_used": extraction.get("narrative_chars", 0),
            "llm_used": extraction.get("llm_used", False),
        },
    }
    return report


def render_report(report: dict[str, Any]) -> None:
    meta = report["metadata"]
    console.print(
        Panel.fit(
            f"[bold red]BUBBLE — MICHAEL BURRY FORENSIC REPORT[/bold red]\n"
            f"{meta['target']} (CIK {meta['cik']}) | {meta['generated_at'][:19]}Z\n"
            f"Mode: Full pipeline — real SEC data + rules + graph + stress testing"
        )
    )

    exec_sum = report["executive_summary"]
    console.print(f"\n[bold]Overall Risk Level:[/bold] {exec_sum['overall_risk_level']:.2f}")
    console.print(f"[bold]Key Themes:[/bold] {', '.join(exec_sum['key_themes'])}")

    # Red Flags Table
    table = Table(title="Red Flags (sorted by severity)")
    table.add_column("Severity", justify="right", style="red")
    table.add_column("Score", justify="right")
    table.add_column("Category")
    table.add_column("Title")
    for f in report["red_flags"]:
        table.add_row(
            f"{f['severity']:.2f}",
            f"{f['red_flag_score']:.2f}",
            f["category"],
            f["title"][:70],
        )
    console.print(table)

    # Stress Scenarios
    console.print("\n[bold]Stress Test Results[/bold]")
    for name, data in report["stress_scenarios"].items():
        stressed = data["stressed_dscr"]
        color = "red" if stressed < 0.9 else "yellow" if stressed < 1.1 else "green"
        console.print(
            f"  {name.upper():8} | DSCR {data['base_dscr']:.2f} → [{color}]{stressed:.2f}[/] | Refi risk {data['refinancing_risk']:.0%}"
        )

    # Contagion
    if report["contagion_analysis"]:
        console.print("\n[bold]Top Contagion Exposure Paths[/bold]")
        for p in report["contagion_analysis"][:3]:
            console.print(
                f"  {p['length']} hops | ~${p.get('estimated_exposure_usd', 0) / 1e9:.1f}B exposure"
            )

    console.print("\n[dim]Full JSON written to data/reports/...[/dim]")


def main(target_cik: str = "0000789019") -> None:
    report = generate_report(target_cik)

    # Write artifacts
    out_dir = Path("data/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M")
    json_path = out_dir / f"burry_report_{target_cik}_{ts}.json"
    json_path.write_text(json.dumps(report, indent=2, default=str))

    # Also write a human-readable Markdown version
    md_path = out_dir / f"burry_report_{target_cik}_{ts}.md"
    md_content = f"""# Burry Report — {report["metadata"]["target"]}

**Generated:** {report["metadata"]["generated_at"]}

## Executive Summary
**Overall Risk:** {report["executive_summary"]["overall_risk_level"]:.2f}

### Red Flags
{chr(10).join(f"- **{f['title']}** (severity {f['severity']:.2f})" for f in report["red_flags"][:5])}

### Stress Test (Tail Case)
- Stressed DSCR: {report["stress_scenarios"]["tail"]["stressed_dscr"]:.2f}
- Refinancing Risk: {report["stress_scenarios"]["tail"]["refinancing_risk"]:.0%}

See the accompanying .json for full structured data, evidence, and graph analysis.
"""
    md_path.write_text(md_content)

    render_report(report)
    console.print(f"\n[green]Artifacts written:[/green]\n  {json_path}\n  {md_path}")


if __name__ == "__main__":
    cik = sys.argv[1] if len(sys.argv) > 1 else "0000789019"
    main(cik)
