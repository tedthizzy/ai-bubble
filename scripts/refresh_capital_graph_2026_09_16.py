#!/usr/bin/env python3
"""Build dated capital and GLEIF graphs from the September 16 acquired files.

This driver deliberately names its inputs. It does not scan historical data roots or
load the June handoff fixtures used by build_capital_exposure_graph.py.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

from bubble.analysis.capital_exposure_graph import (
    build_capital_exposure_graph,
    write_capital_exposure_graph,
)
from bubble.analysis.ownership_graph import (
    build_ownership_graph,
    load_lei_reference_rows,
    load_ownership_rows,
    write_ownership_graph,
)
from bubble.models.base import DealType, HumanReviewStatus, Provenance, SourceType
from bubble.models.deal import Deal
from bubble.quality.source_invariants import assert_source_row

DATE = "2026-09-16"
DEFAULT_FERC = Path(f"data/source_acquisition_{DATE}/derived/ppa_deals.csv")
DEFAULT_EDGAR = Path(f"data/edgar_acquisition_{DATE}/deals.csv")
DEFAULT_GLEIF = Path(f"data/source_acquisition_{DATE}/gleif/source_rows")
DEFAULT_OUTPUT = Path(f"data/capital_graph_refresh_{DATE}")
REVIEWED = {HumanReviewStatus.APPROVED, HumanReviewStatus.OVERRIDDEN}


def file_record(path: Path) -> dict[str, str | int]:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def _split(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").replace(";", "|").split("|") if item.strip()]


def _optional_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _optional_float(value: str | None) -> float | None:
    return float(value) if value else None


def _bool(value: str | None) -> bool:
    return (value or "").lower() in {"true", "1", "yes", "y"}


def _deal_from_row(row: dict[str, str]) -> Deal:
    deal_id = row.get("deal_id") or ""
    if not deal_id:
        raise ValueError("CSV row missing deal_id")
    assert_source_row(row, context=f"deal:{deal_id}")
    source_uri = row["source_uri"]
    source_type = SourceType(row.get("source_type") or SourceType.SEC_EDGAR)
    content_hash = row.get("content_hash") or Provenance.compute_content_hash(
        json.dumps(row, sort_keys=True)
    )
    roles = json.loads(row.get("counterparty_roles") or "{}")
    key_terms = json.loads(row.get("key_terms") or "{}")
    if not isinstance(roles, dict) or not isinstance(key_terms, dict):
        raise ValueError(f"Invalid roles or key terms for {deal_id}")
    parties = _split(row.get("parties")) or _split(row.get("primary_party"))
    if not parties:
        raise ValueError(f"CSV row missing parties: {deal_id}")
    return Deal(
        source_deal_id=deal_id,
        deal_type=DealType(row.get("deal_type") or DealType.OTHER),
        title=row.get("title") or None,
        parties=parties,
        counterparty_roles={
            str(role): _split(entities) if isinstance(entities, str) else [str(e) for e in entities]
            for role, entities in roles.items()
        },
        announced_date=_optional_date(row.get("announced_date")),
        effective_date=_optional_date(row.get("effective_date")),
        maturity_date=_optional_date(row.get("maturity_date")),
        notional_amount_usd=_optional_float(row.get("notional_amount_usd")),
        currency=row.get("currency") or "USD",
        is_non_recourse=_bool(row.get("is_non_recourse")) if row.get("is_non_recourse") else None,
        bankruptcy_remote_spv=(
            _bool(row.get("bankruptcy_remote_spv")) if row.get("bankruptcy_remote_spv") else None
        ),
        key_terms=key_terms,
        collateral=_split(row.get("collateral")),
        guarantees=_split(row.get("guarantees")),
        linked_projects=_split(row.get("linked_projects")),
        linked_assets=_split(row.get("linked_assets")),
        is_related_party=_bool(row.get("is_related_party")),
        concentration_risk_flag=_bool(row.get("concentration_risk_flag")),
        provenance=Provenance(
            source_uri=source_uri,
            source_type=source_type,
            page_or_section=row.get("page_or_section") or None,
            confidence=_optional_float(row.get("source_confidence")) or 0.85,
            human_review_status=HumanReviewStatus(
                row.get("human_review_status") or HumanReviewStatus.PENDING
            ),
            content_hash=content_hash,
        ),
        confidence=_optional_float(row.get("confidence")) or 0.85,
    )


def _load_deals(path: Path) -> list[Deal]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(newline="") as stream:
        return [_deal_from_row({key: (value or "").strip() for key, value in row.items()})
                for row in csv.DictReader(stream)]


def load_ferc_deals(path: Path) -> list[Deal]:
    deals = _load_deals(path)
    for deal in deals:
        if deal.deal_type.value != "ppa" or deal.provenance.source_type != SourceType.FERC:
            raise ValueError(f"Unexpected FERC row type: {deal.source_deal_id}")
    return deals


def load_edgar_deals(path: Path) -> list[Deal]:
    deals = _load_deals(path)
    for deal in deals:
        if deal.provenance.source_type != SourceType.SEC_EDGAR:
            raise ValueError(f"Unexpected EDGAR row type: {deal.source_deal_id}")
    return deals


def select_deals(sources: list[tuple[str, list[Deal]]]) -> tuple[list[Deal], dict]:
    """Reject conflicting source IDs; collapse exact row repeats only."""
    seen: dict[tuple[str, str], str] = {}
    source_by_id: dict[str, str] = {}
    selected: list[Deal] = []
    review = Counter()
    source_rows = Counter()
    duplicate_rows = 0
    for source_name, deals in sources:
        for deal in deals:
            source_rows[source_name] += 1
            if not deal.source_deal_id:
                raise ValueError(f"Missing source_deal_id in {source_name}")
            prior_source = source_by_id.setdefault(deal.source_deal_id, source_name)
            if prior_source != source_name:
                raise ValueError(f"Source deal ID collision: {deal.source_deal_id}")
            key = (deal.source_deal_id, deal.provenance.source_uri)
            old_hash = seen.get(key)
            if old_hash is not None:
                if old_hash != deal.provenance.content_hash:
                    raise ValueError(f"Conflicting duplicate source row: {key}")
                duplicate_rows += 1
                continue
            seen[key] = deal.provenance.content_hash
            review[deal.provenance.human_review_status.value] += 1
            if deal.provenance.human_review_status != HumanReviewStatus.REJECTED:
                selected.append(deal)
    return selected, {
        "source_rows": dict(sorted(source_rows.items())),
        "exact_duplicate_rows_removed": duplicate_rows,
        "review_status_before_rejection_filter": dict(sorted(review.items())),
        "graph_deals": len(selected),
        "reviewed_graph_deals": sum(
            deal.provenance.human_review_status in REVIEWED for deal in selected
        ),
        "pending_graph_deals": sum(
            deal.provenance.human_review_status == HumanReviewStatus.PENDING
            for deal in selected
        ),
    }


def ensure_new_output(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to replace existing graph output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)


def build_capital(
    *,
    mode: str,
    ferc_path: Path,
    edgar_path: Path,
    output_root: Path,
) -> dict:
    out = output_root / mode.replace("-", "_")
    ensure_new_output(out)
    inputs = {"ferc_ppa_deals": file_record(ferc_path)}
    sources = [("ferc", load_ferc_deals(ferc_path))]
    if mode == "complete":
        inputs["edgar_deals"] = file_record(edgar_path)
        sources.append(("edgar", load_edgar_deals(edgar_path)))
    deals, selection = select_deals(sources)
    graph = build_capital_exposure_graph(deals)
    paths = write_capital_exposure_graph(graph, out)
    manifest = {
        "as_of": DATE,
        "mode": mode,
        "inputs": inputs,
        "selection": selection,
        "graph_summary": graph.summary.to_dict(),
        "outputs": {name: file_record(Path(path)) for name, path in sorted(paths.items())},
        "warnings": [
            "Pending rows are mapped evidence, not human-reviewed obligations.",
            "FERC PPA capacity includes source statuses; it is not delivered AI data-center load.",
            "Contract edge notional repeats per relationship; graph totals are not deduplicated debt.",
            "Cross-source economic obligations with different IDs are not merged.",
        ],
    }
    (out / "input_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def build_ownership(*, gleif_dir: Path, output_root: Path) -> dict:
    out = output_root / "ownership_current"
    ensure_new_output(out)
    relationship_path = gleif_dir / "ownership_records.csv"
    lei_path = gleif_dir / "lei_records.csv"
    inputs = {
        "gleif_relationships": file_record(relationship_path),
        "gleif_lei_reference": file_record(lei_path),
    }
    graph = build_ownership_graph(
        load_ownership_rows([gleif_dir]),
        lei_rows=load_lei_reference_rows([gleif_dir]),
    )
    paths = write_ownership_graph(graph, out)
    manifest = {
        "as_of": DATE,
        "mode": "ownership_current",
        "inputs": inputs,
        "graph_summary": graph.summary.to_dict(),
        "outputs": {name: file_record(Path(path)) for name, path in sorted(paths.items())},
        "warning": "GLEIF consolidation relationships are a separate layer. No capital graph join is inferred.",
    }
    (out / "input_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("ferc-only", "complete"), default="ferc-only")
    parser.add_argument("--layer", choices=("capital", "ownership", "both"), default="both")
    parser.add_argument("--ferc-deals", type=Path, default=DEFAULT_FERC)
    parser.add_argument("--edgar-deals", type=Path, default=DEFAULT_EDGAR)
    parser.add_argument("--gleif-dir", type=Path, default=DEFAULT_GLEIF)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.layer in {"capital", "both"}:
        result = build_capital(
            mode=args.mode,
            ferc_path=args.ferc_deals,
            edgar_path=args.edgar_deals,
            output_root=args.output_root,
        )
        print(json.dumps({"capital": result["selection"], "mode": args.mode}, sort_keys=True))
    if args.layer in {"ownership", "both"}:
        result = build_ownership(gleif_dir=args.gleif_dir, output_root=args.output_root)
        print(json.dumps({"ownership": result["graph_summary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
