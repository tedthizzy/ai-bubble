"""Build a source-backed entity universe and map entities to SEC CIKs."""

from __future__ import annotations

import csv
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import httpx

from bubble.models.base import HumanReviewStatus, Provenance, SourceType

SEC_COMPANY_TICKERS_EXCHANGE_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
DEFAULT_USER_AGENT = "bubble-forensic-entity-universe/0.1"
ENTITY_EVIDENCE_LIMIT = 8
SEC_MATCH_MIN_SCORE = 0.92
SEC_FUZZY_MIN_SCORE = 0.965

LEGAL_SUFFIXES = {
    "CO",
    "COMPANY",
    "CORP",
    "CORPORATION",
    "INC",
    "INCORPORATED",
    "LLC",
    "L.L.C",
    "LTD",
    "LIMITED",
    "LP",
    "L.P",
    "LLP",
    "L.L.P",
    "PLC",
    "SA",
    "S.A",
    "AG",
    "NV",
    "N.V",
    "SE",
    "HOLDING",
    "HOLDINGS",
    "GROUP",
}
NOISE_ENTITY_NAMES = {
    "NONE",
    "N/A",
    "NA",
    "UNKNOWN",
    "NOT AVAILABLE",
    "VARIOUS",
    "MULTIPLE",
    "TOTAL",
    "LENDERS PARTY THERETO",
    "NOTEHOLDERS",
    "LENDERS",
}
NOISE_ENTITY_PHRASES = (
    "PARTY THERETO",
    "PARTIES THERETO",
)
GENERIC_MATCH_TOKENS = {
    "AND",
    "THE",
    "DATA",
    "CENTER",
    "CENTERS",
    "ENERGY",
    "POWER",
    "TECHNOLOGY",
    "TECHNOLOGIES",
    "SYSTEMS",
    "SERVICES",
    "INFRASTRUCTURE",
}
SOURCE_FIELD_BLOCKLIST = {
    "source_uri",
    "source_type",
    "retrieved_at",
    "content_hash",
    "local_path",
    "metadata",
    "record_index",
}


@dataclass(frozen=True)
class EntitySourceSpec:
    """Entity-bearing fields in one source-backed CSV."""

    relative_path: str
    source_table: str
    fields: tuple[tuple[str, str], ...]


@dataclass
class EntityAggregate:
    """Aggregated source-backed mentions for one normalized entity name."""

    canonical_name: str
    normalized_name: str
    mention_count: int = 0
    roles: Counter[str] = field(default_factory=Counter)
    source_tables: Counter[str] = field(default_factory=Counter)
    source_uris: set[str] = field(default_factory=set)
    evidence: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class EntityUniverseSummary:
    """Summary for one entity universe build."""

    data_dir: str
    output_dir: str
    source_rows_scanned: int
    mentions_extracted: int
    distinct_entities: int
    sec_reference_entities: int
    cik_matches: int
    high_confidence_cik_matches: int
    expanded_ciks: int
    outputs: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _SecReference:
    cik: str
    ticker: str
    company_name: str
    exchange: str
    normalized_name: str


@dataclass(frozen=True)
class _SecReferenceBatch:
    rows: list[_SecReference]
    source_uri: str
    retrieved_at: str
    content_hash: str
    local_path: str


@dataclass(frozen=True)
class _SecNameIndex:
    by_name: dict[str, list[_SecReference]]
    by_token: dict[str, set[str]]


SOURCE_SPECS = (
    EntitySourceSpec(
        relative_path="source_acquisition/source_rows/ppas.csv",
        source_table="ppas",
        fields=(
            ("Reporting_Entity_Name", "reporting_entity"),
            ("Entity_Name", "seller_or_entity"),
            ("Counterparty_Name", "counterparty"),
        ),
    ),
    EntitySourceSpec(
        relative_path="physical/projects.csv",
        source_table="projects",
        fields=(
            ("name", "project"),
            ("owner", "owner"),
            ("operator", "operator"),
            ("tenants", "tenant"),
        ),
    ),
    EntitySourceSpec(
        relative_path="edgar_acquisition/deals.csv",
        source_table="edgar_deals",
        fields=(
            ("primary_party", "primary_party"),
            ("parties", "party"),
            ("counterparty_roles", "counterparty_role"),
        ),
    ),
    EntitySourceSpec(
        relative_path="capital/deals.csv",
        source_table="capital_deals",
        fields=(
            ("primary_party", "primary_party"),
            ("parties", "party"),
            ("counterparty_roles", "counterparty_role"),
        ),
    ),
    EntitySourceSpec(
        relative_path="physical/permits.csv",
        source_table="permits",
        fields=(
            ("FACILITY_NAME", "facility"),
            ("FAC_NAME", "facility"),
            ("OWNER_NAME", "owner"),
            ("PERMITTEE", "permittee"),
        ),
    ),
    EntitySourceSpec(
        relative_path="physical/equipment.csv",
        source_table="equipment",
        fields=(
            ("Utility name", "utility"),
            ("Plant transmission or distribution system owner name", "grid_owner"),
            ("Balancing Authority Name", "balancing_authority"),
            ("Plant name", "plant"),
        ),
    ),
)


def build_entity_universe(
    data_dir: str | Path = "data",
    *,
    output_dir: str | Path = "data/entity_universe",
    sec_reference_json: str | Path | None = None,
    fetch_sec_reference: bool = True,
    identity: str | None = None,
    min_mentions_for_expanded_cik: int = 1,
    max_expanded_ciks: int | None = None,
) -> EntityUniverseSummary:
    """Extract source-backed entity names and map high-confidence public-company CIKs."""

    base = Path(data_dir)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sec_reference = _load_sec_reference(
        output,
        sec_reference_json=sec_reference_json,
        fetch_sec_reference=fetch_sec_reference,
        identity=identity,
    )
    sec_index = _sec_name_index(sec_reference.rows)

    aggregates: dict[str, EntityAggregate] = {}
    mention_rows: list[dict[str, str]] = []
    source_rows_scanned = 0
    mentions_extracted = 0

    for spec in SOURCE_SPECS:
        path = base / spec.relative_path
        if not path.exists():
            continue
        with path.open(newline="", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                source_rows_scanned += 1
                for field_name, role in spec.fields:
                    for name in _entity_names_from_cell(row.get(field_name, "")):
                        normalized = normalize_entity_name(name)
                        if not _is_valid_entity_name(name, normalized):
                            continue
                        mentions_extracted += 1
                        evidence = _evidence_row(
                            row,
                            name=name,
                            normalized=normalized,
                            role=role,
                            source_table=spec.source_table,
                            source_field=field_name,
                        )
                        mention_rows.append(evidence)
                        aggregate = aggregates.get(normalized)
                        if aggregate is None:
                            aggregate = EntityAggregate(
                                canonical_name=_canonical_display_name(name),
                                normalized_name=normalized,
                            )
                            aggregates[normalized] = aggregate
                        aggregate.mention_count += 1
                        aggregate.roles[role] += 1
                        aggregate.source_tables[spec.source_table] += 1
                        source_uri = row.get("source_uri", "").strip()
                        if source_uri:
                            aggregate.source_uris.add(source_uri)
                        if len(aggregate.evidence) < ENTITY_EVIDENCE_LIMIT:
                            aggregate.evidence.append(evidence)

    entity_rows = _entity_rows(
        aggregates,
        sec_index=sec_index,
        sec_reference=sec_reference,
    )
    expanded_rows = _expanded_cik_rows(
        entity_rows,
        min_mentions=min_mentions_for_expanded_cik,
        max_rows=max_expanded_ciks,
    )

    outputs = {
        "entity_mentions_csv": str(output / "entity_mentions.csv"),
        "entities_csv": str(output / "entities.csv"),
        "expanded_edgar_ciks_csv": str(output / "expanded_edgar_ciks.csv"),
        "sec_reference_json": sec_reference.local_path,
        "summary_json": str(output / "entity_universe.summary.json"),
    }
    _write_csv(output / "entity_mentions.csv", mention_rows)
    _write_csv(output / "entities.csv", entity_rows)
    _write_csv(output / "expanded_edgar_ciks.csv", expanded_rows)

    summary = EntityUniverseSummary(
        data_dir=str(base),
        output_dir=str(output),
        source_rows_scanned=source_rows_scanned,
        mentions_extracted=mentions_extracted,
        distinct_entities=len(entity_rows),
        sec_reference_entities=len(sec_reference.rows),
        cik_matches=sum(1 for row in entity_rows if row["matched_cik"]),
        high_confidence_cik_matches=sum(
            1
            for row in entity_rows
            if row["matched_cik"] and float(row["cik_match_score"] or 0) >= SEC_MATCH_MIN_SCORE
        ),
        expanded_ciks=len(expanded_rows),
        outputs=outputs,
    )
    (output / "entity_universe.summary.json").write_text(
        json.dumps(summary.to_dict(), indent=2, sort_keys=True)
    )
    return summary


def normalize_entity_name(name: str) -> str:
    """Normalize entity names for deterministic matching."""

    cleaned = _canonical_display_name(name).upper()
    cleaned = re.sub(r"&", " AND ", cleaned)
    cleaned = re.sub(r"[^A-Z0-9 ]+", " ", cleaned)
    tokens = [token for token in cleaned.split() if token]
    while tokens and tokens[-1] in LEGAL_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def _load_sec_reference(
    output_dir: Path,
    *,
    sec_reference_json: str | Path | None,
    fetch_sec_reference: bool,
    identity: str | None,
) -> _SecReferenceBatch:
    if sec_reference_json is not None:
        path = Path(sec_reference_json)
        raw = path.read_bytes()
        retrieved_at = datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()
    else:
        raw_path = output_dir / "raw" / "sec_company_tickers_exchange.json"
        if raw_path.exists():
            path = raw_path
            raw = path.read_bytes()
            retrieved_at = datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()
        elif fetch_sec_reference:
            raw = _fetch_sec_company_reference(identity=identity)
            retrieved_at = datetime.now(UTC).isoformat()
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(raw)
            path = raw_path
        else:
            raise ValueError("SEC reference JSON is required when fetch_sec_reference=False.")

    content_hash = Provenance.compute_content_hash(raw)
    return _SecReferenceBatch(
        rows=_parse_sec_reference(raw),
        source_uri=SEC_COMPANY_TICKERS_EXCHANGE_URL,
        retrieved_at=retrieved_at,
        content_hash=content_hash,
        local_path=str(path),
    )


def _fetch_sec_company_reference(*, identity: str | None) -> bytes:
    user_agent = identity or os.getenv("EDGAR_IDENTITY")
    if not user_agent:
        raise ValueError(
            "SEC company reference acquisition requires EDGAR_IDENTITY, "
            "for example 'Name email@example.com'."
        )
    headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
    with httpx.Client(headers=headers, timeout=45.0, follow_redirects=True) as client:
        response = client.get(SEC_COMPANY_TICKERS_EXCHANGE_URL)
        response.raise_for_status()
        return bytes(response.content)


def _parse_sec_reference(raw: bytes) -> list[_SecReference]:
    parsed = json.loads(raw.decode("utf-8"))
    rows: list[_SecReference] = []
    if isinstance(parsed, dict) and "fields" in parsed and "data" in parsed:
        fields = [str(field).lower() for field in parsed["fields"]]
        for item in parsed["data"]:
            values = dict(zip(fields, item, strict=False))
            rows.append(_sec_reference_from_mapping(values))
    elif isinstance(parsed, dict):
        rows.extend(
            _sec_reference_from_mapping(value)
            for value in parsed.values()
            if isinstance(value, dict)
        )
    return [row for row in rows if row.cik and row.company_name]


def _sec_reference_from_mapping(value: dict[str, Any]) -> _SecReference:
    cik_raw = str(value.get("cik") or value.get("cik_str") or "").strip()
    company_name = str(value.get("name") or value.get("title") or "").strip()
    ticker = str(value.get("ticker") or "").strip().upper()
    exchange = str(value.get("exchange") or "").strip()
    return _SecReference(
        cik="".join(ch for ch in cik_raw if ch.isdigit()).zfill(10),
        ticker=ticker,
        company_name=company_name,
        exchange=exchange,
        normalized_name=normalize_entity_name(company_name),
    )


def _sec_name_index(rows: list[_SecReference]) -> _SecNameIndex:
    by_name: dict[str, list[_SecReference]] = defaultdict(list)
    by_token: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if row.normalized_name:
            by_name[row.normalized_name].append(row)
            for token in _match_tokens(row.normalized_name):
                by_token[token].add(row.normalized_name)
    return _SecNameIndex(by_name=dict(by_name), by_token=dict(by_token))


def _entity_rows(
    aggregates: dict[str, EntityAggregate],
    *,
    sec_index: _SecNameIndex,
    sec_reference: _SecReferenceBatch,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for aggregate in sorted(
        aggregates.values(),
        key=lambda item: (-item.mention_count, item.canonical_name.lower()),
    ):
        sec_match, method, score = _match_sec_reference(
            aggregate.normalized_name,
            sec_index=sec_index,
        )
        evidence_json = json.dumps(aggregate.evidence, sort_keys=True)
        rows.append(
            {
                "entity_key": Provenance.compute_content_hash(aggregate.normalized_name)[:16],
                "canonical_name": aggregate.canonical_name,
                "normalized_name": aggregate.normalized_name,
                "mention_count": str(aggregate.mention_count),
                "roles": json.dumps(dict(sorted(aggregate.roles.items())), sort_keys=True),
                "source_tables": json.dumps(
                    dict(sorted(aggregate.source_tables.items())), sort_keys=True
                ),
                "source_count": str(len(aggregate.source_uris)),
                "evidence_json": evidence_json,
                "matched_cik": sec_match.cik if sec_match else "",
                "matched_ticker": sec_match.ticker if sec_match else "",
                "matched_sec_name": sec_match.company_name if sec_match else "",
                "matched_exchange": sec_match.exchange if sec_match else "",
                "cik_match_method": method,
                "cik_match_score": f"{score:.4f}" if sec_match else "",
                "cik_match_source_uri": sec_reference.source_uri if sec_match else "",
                "cik_reference_retrieved_at": sec_reference.retrieved_at if sec_match else "",
                "cik_reference_content_hash": sec_reference.content_hash if sec_match else "",
                "source_confidence": "0.92"
                if sec_match and score >= SEC_MATCH_MIN_SCORE
                else "0.72",
                "human_review_status": HumanReviewStatus.PENDING.value,
            }
        )
    return rows


def _match_sec_reference(
    normalized: str,
    *,
    sec_index: _SecNameIndex,
) -> tuple[_SecReference | None, str, float]:
    exact = sec_index.by_name.get(normalized)
    if exact:
        return exact[0], "normalized_exact", 1.0

    best_name = ""
    best_score = 0.0
    for sec_name in _candidate_sec_names(normalized, sec_index):
        if not sec_name:
            continue
        score = _name_similarity(normalized, sec_name)
        if score > best_score:
            best_name = sec_name
            best_score = score
    if best_name and best_score >= SEC_FUZZY_MIN_SCORE:
        return sec_index.by_name[best_name][0], "normalized_fuzzy", best_score
    return None, "", 0.0


def _candidate_sec_names(normalized: str, sec_index: _SecNameIndex) -> set[str]:
    token_sets = [
        sec_index.by_token[token]
        for token in _match_tokens(normalized)
        if token in sec_index.by_token
    ]
    if not token_sets:
        return set()
    token_sets.sort(key=len)
    candidates = set(token_sets[0])
    for token_set in token_sets[1:3]:
        intersection = candidates & token_set
        if intersection:
            candidates = intersection
    return candidates


def _match_tokens(normalized: str) -> list[str]:
    return [
        token
        for token in normalized.split()
        if len(token) >= 4 and token not in GENERIC_MATCH_TOKENS
    ]


def _name_similarity(left: str, right: str) -> float:
    if left == right:
        return 1.0
    if len(left) < 5 or len(right) < 5:
        return 0.0
    if left in right or right in left:
        shorter = min(len(left), len(right))
        longer = max(len(left), len(right))
        return shorter / longer
    return SequenceMatcher(None, left, right).ratio()


def _expanded_cik_rows(
    entity_rows: list[dict[str, str]],
    *,
    min_mentions: int,
    max_rows: int | None,
) -> list[dict[str, str]]:
    by_cik: dict[str, dict[str, str]] = {}
    for row in entity_rows:
        cik = row["matched_cik"]
        if not cik:
            continue
        if int(row["mention_count"]) < min_mentions:
            continue
        existing = by_cik.get(cik)
        if existing is None or int(row["mention_count"]) > int(existing["mention_count"]):
            by_cik[cik] = {
                "cik": cik,
                "ticker": row["matched_ticker"],
                "sec_company_name": row["matched_sec_name"],
                "source_entity_name": row["canonical_name"],
                "mention_count": row["mention_count"],
                "source_count": row["source_count"],
                "cik_match_method": row["cik_match_method"],
                "cik_match_score": row["cik_match_score"],
                "source_uri": row["cik_match_source_uri"],
                "retrieved_at": row["cik_reference_retrieved_at"],
                "content_hash": row["cik_reference_content_hash"],
                "human_review_status": row["human_review_status"],
            }
    rows = sorted(
        by_cik.values(),
        key=lambda item: (-int(item["mention_count"]), item["sec_company_name"]),
    )
    return rows[:max_rows] if max_rows is not None else rows


def _evidence_row(
    row: dict[str, str],
    *,
    name: str,
    normalized: str,
    role: str,
    source_table: str,
    source_field: str,
) -> dict[str, str]:
    return {
        "canonical_name": _canonical_display_name(name),
        "normalized_name": normalized,
        "role": role,
        "source_table": source_table,
        "source_field": source_field,
        "source_uri": row.get("source_uri", "").strip(),
        "source_type": row.get("source_type", "").strip() or SourceType.MANUAL_CURATED.value,
        "retrieved_at": row.get("retrieved_at", "").strip(),
        "content_hash": row.get("content_hash", "").strip(),
        "document_id": row.get("document_id", "").strip(),
        "filing_accession": row.get("filing_accession", "").strip(),
        "local_path": row.get("local_path", "").strip(),
        "record_index": row.get("record_index", "").strip(),
    }


def _entity_names_from_cell(value: str) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    parsed = _json_names(text)
    if parsed:
        return parsed
    if "|" in text:
        return [part.strip() for part in text.split("|") if part.strip()]
    return [text]


def _json_names(value: str) -> list[str]:
    if not value or value[0] not in "[{":
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    names: list[str] = []
    _collect_json_names(parsed, names)
    return names


def _collect_json_names(value: Any, names: list[str]) -> None:
    if isinstance(value, str):
        names.append(value)
    elif isinstance(value, list):
        for item in value:
            _collect_json_names(item, names)
    elif isinstance(value, dict):
        for key, item in value.items():
            if key in SOURCE_FIELD_BLOCKLIST:
                continue
            _collect_json_names(item, names)


def _canonical_display_name(name: str) -> str:
    cleaned = " ".join(str(name).replace("\n", " ").replace("\t", " ").split())
    cleaned = re.sub(r"\s*\([^)]{0,120}\)\s*$", "", cleaned).strip()
    return cleaned.strip(" ,.;:-")


def _is_valid_entity_name(name: str, normalized: str) -> bool:
    canonical = _canonical_display_name(name)
    if not canonical or normalized in NOISE_ENTITY_NAMES:
        return False
    if len(normalized) < 3 or len(canonical) > 180:
        return False
    if normalized.isdigit():
        return False
    if any(phrase in normalized for phrase in NOISE_ENTITY_PHRASES):
        return False
    if normalized.startswith(("HTTP ", "HTTPS ")):
        return False
    return bool(re.search(r"[A-Z]", normalized))


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        if not fieldnames:
            return
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
