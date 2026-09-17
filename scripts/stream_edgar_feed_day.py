#!/usr/bin/env python3
"""Stream one SEC Feed day, retaining selected public documents and exhibits.

Requires an already saved official SEC master index. The archive is read from
SEC over HTTPS and never stored locally. A failed or mismatched day is reported
as incomplete; the acquired document bytes remain available for inspection.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import re
import tarfile
import tempfile
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlparse

ACCESSION_RE = re.compile(r"(?<!\d)(\d{10}-\d{2}-\d{6})(?!\d)")
DOCUMENT_RE = re.compile(rb"<DOCUMENT>(.*?)</DOCUMENT>", re.I | re.S)
TEXT_RE = re.compile(rb"<TEXT>(.*?)</TEXT>", re.I | re.S)
TYPE_RE = re.compile(rb"(?:^|[\r\n])<TYPE>[ \t]*([^\r\n]+)", re.I)
FILENAME_RE = re.compile(rb"(?:^|[\r\n])<FILENAME>[ \t]*([^\r\n]+)", re.I)
FILING_DATE_RE = re.compile(rb"(?:^|[\r\n])<FILING-DATE>[ \t]*([^\r\n]+)", re.I)
HEADER_CIK_RE = re.compile(rb"(?:^|[\r\n])<CIK>[ \t]*(\d+)", re.I)
DOCUMENT_HEADER_RE = re.compile(
    rb"<DOCUMENT>[\r\n]*<TYPE>[ \t]*([^\r\n]+)[\s\S]{0,512}?<FILENAME>[ \t]*([^\r\n]+)",
    re.I,
)
EXHIBIT_RE = re.compile(r"^EX-(?:2|4|10|21|22|99)(?:\.|$)", re.I)
PRIORITY_FORMS = {"D", "D/A", "10-K", "10-K/A", "10-Q", "10-Q/A", "10-D", "10-D/A", "8-K", "8-K/A", "6-K", "20-F", "40-F", "S-1", "S-1/A", "FWP"}
SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "ai_compute": (b"artificial intelligence", b"ai infrastructure", b"gpu", b"hbm", b"high bandwidth memory"),
    "data_center": (b"data center", b"data centre", b"datacenter", b"colocation", b"hyperscal"),
    "frontier_lab": (b"anthropic", b"openai", b"xai", b"deepseek"),
    "chip_supplier": (b"nvidia", b"advanced micro devices", b"broadcom", b"tsmc"),
    "credit_stress": (b"going concern", b"covenant", b"default under", b"liquidity shortfall"),
    "asset_value": (b"impairment", b"write-down", b"depreciation", b"useful life"),
    "financing_structure": (b"non-recourse", b"guarantee", b"sale-leaseback", b"prepayment", b"securitization"),
    "capital_spend": (b"capital expenditures", b"capital expenditure", b"construction in progress"),
}


class HashingReader:
    def __init__(self, stream: BinaryIO):
        self.stream = stream
        self.digest = hashlib.sha256()
        self.bytes_read = 0

    def read(self, size: int = -1) -> bytes:
        data = self.stream.read(size)
        self.digest.update(data)
        self.bytes_read += len(data)
        return data


def master_day_all_rows(path: Path, day: date) -> list[dict[str, str]]:
    """Preserve every official index CIK-accession row for one filed date."""
    opener = gzip.open if path.suffix == ".gz" else open
    result: list[dict[str, str]] = []
    with opener(path, "rt", errors="replace") as stream:
        in_rows = False
        for line in stream:
            if not in_rows:
                in_rows = line.startswith("CIK|Company Name|Form Type|Date Filed|Filename")
                continue
            fields = line.rstrip("\r\n").split("|", 4)
            if len(fields) != 5 or fields[3] != day.isoformat():
                continue
            match = ACCESSION_RE.search(fields[4])
            if match:
                accession = match.group(1)
                result.append({
                    "accession_number": accession,
                    "cik": fields[0].zfill(10),
                    "company_name": fields[1],
                    "form": fields[2],
                    "filing_date": fields[3],
                    "complete_submission_url": "https://www.sec.gov/Archives/" + fields[4].lstrip("/"),
                })
    return result


def master_day_rows(path: Path, day: date) -> dict[str, dict[str, str]]:
    """Return one representative index row per accession for content selection."""
    return {row["accession_number"]: row for row in master_day_all_rows(path, day)}


def master_accessions(path: Path, day: date) -> set[str]:
    return set(master_day_rows(path, day))


def _priority_form(form: str) -> bool:
    return form.upper() in PRIORITY_FORMS or form.upper().startswith(("424B", "ABS-", "SF-"))


def _extra_ciks(path: Path | None) -> set[str]:
    if path is None:
        return set()
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        if "cik" not in (reader.fieldnames or []):
            raise ValueError(f"Extra CIK file lacks cik column: {path}")
        return {(row.get("cik") or "").strip().zfill(10) for row in reader if (row.get("cik") or "").strip()}


def _index_candidate_row(index_row: dict[str, str], reason: str) -> dict[str, str]:
    return {
        "cik": index_row["cik"],
        "company_name": index_row["company_name"],
        "form": index_row["form"],
        "accession_number": index_row["accession_number"],
        "filing_date": index_row["filing_date"],
        "primary_document": "",
        "filing_url": "",
        "source_uri": index_row["complete_submission_url"],
        "document_type": "primary",
        "relevance_score": "75",
        "relevance_reasons": reason,
    }


def load_manifest(path: Path, day: date, min_score: int) -> tuple[list[str], dict[str, list[dict[str, str]]]]:
    selected: dict[str, list[dict[str, str]]] = defaultdict(list)
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError("Empty manifest header")
        fieldnames = list(reader.fieldnames)
        for row in reader:
            if row.get("filing_date") != day.isoformat():
                continue
            if int(row.get("relevance_score") or 0) < min_score:
                continue
            accession = row.get("accession_number") or ""
            if not ACCESSION_RE.fullmatch(accession):
                continue
            selected[accession].append(row)
    return fieldnames, selected


def submission_documents(raw: bytes):
    """Yield public documents from the SEC PDS SGML submission body."""
    for match in DOCUMENT_RE.finditer(raw):
        block = match.group(1)
        type_match = TYPE_RE.search(block)
        name_match = FILENAME_RE.search(block)
        text_match = TEXT_RE.search(block)
        if not (type_match and name_match and text_match):
            continue
        document_type = type_match.group(1).decode("utf-8", "replace").strip()
        filename = name_match.group(1).decode("utf-8", "replace").strip()
        if not filename or filename != Path(filename).name or filename in {".", ".."}:
            continue
        yield document_type, filename, text_match.group(1)


def _store_document(path: Path, content: bytes) -> None:
    """Write a new compressed source; never replace a previous source."""
    if path.exists():
        with gzip.open(path, "rb") as stream:
            previous = stream.read()
        if previous != content:
            raise ValueError(f"Existing document differs: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", suffix=".part", delete=False) as staged:
        staged.write(gzip.compress(content, compresslevel=3, mtime=0))
        staged.flush()
        os.fsync(staged.fileno())
        staged_path = Path(staged.name)
    try:
        if path.exists():
            raise FileExistsError(path)
        os.replace(staged_path, path)
    finally:
        if staged_path.exists():
            staged_path.unlink()


def _filing_row(base: dict[str, str], filename: str, doc_type: str) -> dict[str, str]:
    row = dict(base)
    row["primary_document"] = filename
    row["primary_document_description"] = f"SEC Feed document {doc_type}"
    row["document_type"] = "exhibit" if EXHIBIT_RE.match(doc_type) else "primary"
    row["parent_primary_document"] = base.get("primary_document") or ""
    cik = str(int(base["cik"]))
    accession = base["accession_number"].replace("-", "")
    row["filing_url"] = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{filename}"
    row["relevance_reasons"] = (row.get("relevance_reasons") or "") + "|feed_embedded_document"
    return row


def _direct_document_name(row: dict[str, str]) -> str | None:
    """A display/XSL route is not equivalent to an embedded source document."""
    parts = urlparse(row.get("filing_url") or "").path.split("/")
    accession = (row.get("accession_number") or "").replace("-", "")
    if len(parts) < 2 or parts[-2] != accession:
        return None
    return parts[-1].lower()


def _scan_member_stream(member_stream: BinaryIO, *, retain_raw: bool) -> tuple[bytes | None, str, int, set[str], list[tuple[str, str]], dict[str, str]]:
    """Hash and screen every byte while buffering only selected submissions."""
    digest = hashlib.sha256()
    raw_parts: list[bytes] | None = [] if retain_raw else None
    hits: set[str] = set()
    headers: list[tuple[str, str]] = []
    tail = b""
    head = b""
    total = 0
    while block := member_stream.read(1024 * 1024):
        digest.update(block)
        total += len(block)
        if raw_parts is not None:
            raw_parts.append(block)
        if len(head) < 65536:
            head += block[:65536 - len(head)]
        window = tail + block
        for match in DOCUMENT_HEADER_RE.finditer(window):
            if match.end() <= len(tail):
                continue
            doc_type = match.group(1).decode("utf-8", "replace").strip()
            filename = match.group(2).decode("utf-8", "replace").strip()
            if filename and filename == Path(filename).name:
                headers.append((doc_type, filename))
        lower = window.lower()
        for label, needles in SIGNATURES.items():
            if label not in hits and any(needle in lower for needle in needles):
                hits.add(label)
        tail = window[-1024:]
    sgml_header = head.split(b"<DOCUMENT>", 1)[0]
    type_match = TYPE_RE.search(sgml_header)
    date_match = FILING_DATE_RE.search(sgml_header)
    header = {
        "submission_form": type_match.group(1).decode("utf-8", "replace").strip() if type_match else "",
        "submission_filing_date": date_match.group(1).decode("utf-8", "replace").strip() if date_match else "",
        "submission_ciks": "|".join(dict.fromkeys(
            match.decode("ascii").zfill(10) for match in HEADER_CIK_RE.findall(sgml_header)
        )),
    }
    return (b"".join(raw_parts) if raw_parts is not None else None, digest.hexdigest(), total, hits, headers, header)


def stream_day(
    archive_stream: BinaryIO,
    *,
    archive_url: str,
    manifest_csv: Path,
    master_index: Path,
    day: date,
    output_dir: Path,
    min_score: int = 0,
    max_member_bytes: int = 512 * 1024 * 1024,
    expected_compressed_bytes: int | None = None,
    extra_cik_csv: Path | None = None,
) -> dict:
    fieldnames, selected = load_manifest(manifest_csv, day, min_score)
    master_all = master_day_all_rows(master_index, day)
    master = {row["accession_number"]: row for row in master_all}
    if not master:
        raise ValueError(f"No master-index accessions for {day}; check index freshness")
    exact_ciks = _extra_ciks(extra_cik_csv)
    candidate_reasons: dict[str, str] = {accession: "selected_manifest" for accession in selected}
    index_only: set[str] = set()
    for index_row in master_all:
        accession = index_row["accession_number"]
        if accession in selected:
            continue
        reasons = []
        if _priority_form(index_row["form"]):
            reasons.append("priority_form")
        if index_row["cik"] in exact_ciks:
            reasons.append("exact_nonsec_entity_cik")
        if reasons:
            reason = "|".join(reasons)
            selected[accession] = [_index_candidate_row(index_row, reason)]
            candidate_reasons[accession] = reason
            index_only.add(accession)
    if output_dir.joinpath("feed_stream_summary.json").exists():
        raise FileExistsError(output_dir / "feed_stream_summary.json")
    output_dir.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    unknown_members: list[str] = []
    oversized_members: list[dict[str, object]] = []
    found_urls: set[str] = set()
    document_rows: list[dict[str, str]] = []
    provenance: list[dict[str, object]] = []
    member_inventory: list[dict[str, object]] = []
    document_metadata: list[dict[str, object]] = []
    index_primary_found: set[str] = set()
    started = time.monotonic()
    reader = HashingReader(archive_stream)
    with gzip.GzipFile(fileobj=reader, mode="rb") as decompressed:
        with tarfile.open(fileobj=decompressed, mode="r|") as archive:
            for member in archive:
                if not member.isfile():
                    continue
                accession_match = ACCESSION_RE.search(member.name)
                if not accession_match:
                    unknown_members.append(member.name)
                    continue
                accession = accession_match.group(1)
                seen.add(accession)
                if accession in selected and member.size > max_member_bytes:
                    oversized_members.append({"accession": accession, "bytes": member.size})
                member_stream = archive.extractfile(member)
                if member_stream is None:
                    unknown_members.append(member.name)
                    continue
                raw, member_hash, bytes_read, signature_hits, headers, submission_header = _scan_member_stream(
                    member_stream,
                    retain_raw=accession in selected and member.size <= max_member_bytes,
                )
                if bytes_read != member.size:
                    raise EOFError(f"Truncated tar member: {member.name}")
                indexed = master.get(accession, {})
                member_inventory.append({
                    "accession_number": accession,
                    "tar_member": member.name,
                    "member_bytes": member.size,
                    "member_sha256": member_hash,
                    "archive_url": archive_url,
                    "cik": indexed.get("cik", ""),
                    "company_name": indexed.get("company_name", ""),
                    "form": indexed.get("form", ""),
                    **submission_header,
                    "content_selected": accession in selected,
                    "selection_reason": candidate_reasons.get(accession, "content_pending_unselected"),
                    "signature_hits": "|".join(sorted(signature_hits)),
                    "document_headers": len(headers),
                    "signature_screened": True,
                })
                cik = indexed.get("cik", "")
                direct_base = (
                    f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/"
                    if cik else ""
                )
                for doc_type, filename in headers:
                    document_metadata.append({
                        "accession_number": accession,
                        "document_type": doc_type,
                        "filename": filename,
                        "direct_source_uri": direct_base + filename if direct_base else "",
                        "archive_url": archive_url,
                        "tar_member": member.name,
                        "member_sha256": member_hash,
                        "retained": False,
                    })
                if len(member_inventory) % 500 == 0:
                    print(json.dumps({
                        "event": "feed_day_progress", "day": day.isoformat(),
                        "members": len(member_inventory),
                        "compressed_bytes_read": reader.bytes_read,
                        "documents_saved": len(document_rows),
                    }), flush=True)
                if raw is None:
                    continue
                parent_rows = selected[accession]
                by_filename = {
                    name: row
                    for row in parent_rows
                    if (name := _direct_document_name(row)) is not None
                }
                parent = parent_rows[0]
                for doc_type, filename, content in submission_documents(raw):
                    direct = by_filename.get(filename.lower())
                    is_exhibit = bool(EXHIBIT_RE.match(doc_type)) and Path(filename).suffix.lower() in {".htm", ".html", ".txt", ".xml"}
                    is_index_primary = accession in index_only and doc_type.upper() == parent.get("form", "").upper()
                    if direct is None and not is_exhibit and not is_index_primary:
                        continue
                    row = dict(direct) if direct is not None else _filing_row(parent, filename, doc_type)
                    if is_index_primary:
                        index_primary_found.add(accession)
                    if direct is None:
                        row["source_uri"] = archive_url
                        row["provenance_source_uri"] = archive_url + "#" + member.name
                        row["provenance_confidence"] = "1.0"
                        row["provenance_content_hash"] = hashlib.sha256(content).hexdigest()
                    cik = row["cik"].zfill(10)
                    local = output_dir / "documents" / cik / accession.replace("-", "") / (filename + ".gz")
                    _store_document(local, content)
                    row["primary_document"] = filename
                    row["size_bytes"] = str(len(content))
                    document_rows.append(row)
                    found_urls.add(row["filing_url"])
                    provenance.append({
                        "filing_url": row["filing_url"],
                        "archive_url": archive_url,
                        "tar_member": member.name,
                        "accession_number": accession,
                        "document_type": doc_type,
                        "member_sha256": member_hash,
                        "document_sha256": hashlib.sha256(content).hexdigest(),
                        "document_bytes": len(content),
                        "local_path": str(local),
                    })
        # Consume the gzip trailer to verify CRC and source length, even when tar ends first.
        while decompressed.read(1024 * 1024):
            pass
    requested_urls = {row["filing_url"] for rows in selected.values() for row in rows if row.get("filing_url")}
    missing_master = sorted(set(master) - seen)
    extra_feed = sorted(seen - set(master))
    missing_selected = sorted(set(selected) - seen)
    missing_documents = sorted(requested_urls - found_urls)
    missing_index_primary = sorted(index_only - index_primary_found)
    byte_mismatch = expected_compressed_bytes is not None and reader.bytes_read != expected_compressed_bytes
    archive_integrity_complete = not byte_mismatch
    date_index_reconciled = not (missing_master or extra_feed)
    content_retention_complete = not (
        missing_selected or missing_documents or missing_index_primary or oversized_members
    )
    complete = archive_integrity_complete and date_index_reconciled and content_retention_complete
    summary = {
        "day": day.isoformat(),
        "archive_url": archive_url,
        "master_index": str(master_index),
        "manifest_csv": str(manifest_csv),
        "compressed_bytes": reader.bytes_read,
        "compressed_sha256": reader.digest.hexdigest(),
        "expected_compressed_bytes": expected_compressed_bytes,
        "master_accessions": len(master),
        "master_filing_rows": len(master_all),
        "feed_accessions": len(seen),
        "member_hashes_recorded": len(member_inventory),
        "document_headers_screened": len(document_metadata),
        "member_bytes_screened": sum(int(item["member_bytes"]) for item in member_inventory),
        "scanner_version_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "members_screened_by_form": dict(Counter(str(item["form"] or item["submission_form"]) for item in member_inventory)),
        "members_content_selected_by_form": dict(Counter(
            str(item["form"] or item["submission_form"]) for item in member_inventory if item["content_selected"]
        )),
        "documents_retained_by_form": dict(Counter(str(row.get("form") or "") for row in document_rows)),
        "signature_hits_by_label": {
            label: sum(label in str(item["signature_hits"]).split("|") for item in member_inventory)
            for label in SIGNATURES
        },
        "selected_accessions": len(selected),
        "index_only_candidate_accessions": len(index_only),
        "exact_nonsec_ciks_input": len(exact_ciks),
        "other_form_content_pending_accessions": len(set(master) - set(selected)),
        "selected_documents_requested": len(requested_urls),
        "selected_documents_extracted": len(found_urls),
        "exhibit_documents_extracted": sum(row.get("document_type") == "exhibit" for row in document_rows),
        "missing_from_feed": missing_master,
        "feed_not_in_master": extra_feed,
        "selected_accessions_missing": missing_selected,
        "selected_document_urls_missing": missing_documents,
        "index_candidate_primary_missing": missing_index_primary,
        "oversized_selected_members": oversized_members,
        "unidentified_tar_members": unknown_members,
        "byte_count_mismatch": byte_mismatch,
        "archive_integrity_complete": archive_integrity_complete,
        "date_index_reconciled": date_index_reconciled,
        "content_retention_complete": content_retention_complete,
        "reconciled": complete,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    with (output_dir / "master_day_rows.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(next(iter(master.values()))))
        writer.writeheader()
        writer.writerows(master_all)
    with (output_dir / "feed_member_inventory.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "accession_number", "tar_member", "member_bytes", "member_sha256", "archive_url",
            "cik", "company_name", "form", "submission_form", "submission_filing_date", "submission_ciks",
            "content_selected", "selection_reason",
            "signature_hits", "document_headers", "signature_screened",
        ])
        writer.writeheader()
        writer.writerows(member_inventory)
    retained_urls = set(found_urls)
    for row in document_metadata:
        row["retained"] = row["direct_source_uri"] in retained_urls
    with (output_dir / "feed_document_metadata.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "accession_number", "document_type", "filename", "direct_source_uri",
            "archive_url", "tar_member", "member_sha256", "retained",
        ])
        writer.writeheader()
        writer.writerows(document_metadata)
    candidate_queue = [
        {**row, "review_state": "content_pending"}
        for row in member_inventory
        if not row["content_selected"] and (
            str(row["form"]).upper().startswith(("NPORT", "13F")) or row["signature_hits"]
        )
    ]
    with (output_dir / "feed_content_candidate_queue.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "accession_number", "tar_member", "member_bytes", "member_sha256", "archive_url",
            "cik", "company_name", "form", "submission_form", "submission_filing_date", "submission_ciks",
            "content_selected", "selection_reason",
            "signature_hits", "document_headers", "signature_screened", "review_state",
        ])
        writer.writeheader()
        writer.writerows(candidate_queue)
    fields = list(dict.fromkeys([*fieldnames, *(k for row in document_rows for k in row)]))
    with (output_dir / "feed_document_manifest.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(document_rows)
    with (output_dir / "feed_document_provenance.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(provenance[0]) if provenance else [
            "filing_url", "archive_url", "tar_member", "accession_number", "document_type",
            "member_sha256", "document_sha256", "document_bytes", "local_path",
        ])
        writer.writeheader()
        writer.writerows(provenance)
    (output_dir / "feed_stream_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--day", type=date.fromisoformat, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--master-index", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--archive-url", required=True)
    parser.add_argument("--user-agent", required=True)
    parser.add_argument("--extra-cik-csv", type=Path)
    parser.add_argument("--min-score", type=int, default=0)
    parser.add_argument("--max-member-bytes", type=int, default=512 * 1024 * 1024)
    args = parser.parse_args()
    request = urllib.request.Request(args.archive_url, headers={"User-Agent": args.user_agent})
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise ValueError(f"Expected HTTP 200 for complete archive; got {response.status}")
        length = response.headers.get("Content-Length")
        summary = stream_day(
            response,
            archive_url=args.archive_url,
            manifest_csv=args.manifest,
            master_index=args.master_index,
            day=args.day,
            output_dir=args.output_dir,
            min_score=args.min_score,
            max_member_bytes=args.max_member_bytes,
            expected_compressed_bytes=int(length) if length else None,
            extra_cik_csv=args.extra_cik_csv,
        )
    print(json.dumps({key: summary[key] for key in (
        "day", "compressed_bytes", "master_accessions", "feed_accessions",
        "selected_accessions", "selected_documents_extracted", "exhibit_documents_extracted",
        "archive_integrity_complete", "date_index_reconciled", "content_retention_complete",
    )}, indent=2))
    if not summary["archive_integrity_complete"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
