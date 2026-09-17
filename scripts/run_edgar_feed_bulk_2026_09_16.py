#!/usr/bin/env python3
"""Stream every available June 1-September 15, 2026 SEC Feed archive.

The official saved Q2/Q3 master indexes supply the dated filing denominator.
Each worker verifies the full archive and writes to its own new day directory.
This driver preserves partial days and never silently retries an uncertain run.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

if __package__:
    from scripts.stream_edgar_feed_day import ACCESSION_RE
else:
    from stream_edgar_feed_day import ACCESSION_RE

BASE = Path(__file__).resolve().parents[1]
MASTER_DIR = BASE / "data/sec_master_index_2026-09-16"
MANIFEST = BASE / "data/manifests/edgar_filing_manifest_20260917-020227.csv"
EXACT_CIKS = MASTER_DIR / "exact_nonsec_missing_cik_filings.csv"
DAY_SCRIPT = BASE / "scripts/stream_edgar_feed_day.py"
DEFAULT_OUTPUT = BASE / "data/edgar_feed_bulk_2026-09-16"
START = date(2026, 6, 1)
END = date(2026, 9, 15)


def index_rows() -> list[dict[str, str]]:
    rows = []
    for quarter in (2, 3):
        path = MASTER_DIR / f"2026-QTR{quarter}-master.gz"
        with gzip.open(path, "rt", errors="replace") as stream:
            in_rows = False
            for line in stream:
                if not in_rows:
                    in_rows = line.startswith("CIK|Company Name|Form Type|Date Filed|Filename")
                    continue
                fields = line.rstrip("\r\n").split("|", 4)
                if len(fields) != 5 or not START.isoformat() <= fields[3] <= END.isoformat():
                    continue
                match = ACCESSION_RE.search(fields[4])
                if match:
                    accession = match.group(1)
                    rows.append({
                        "accession_number": accession,
                        "cik": fields[0].zfill(10),
                        "company_name": fields[1],
                        "form": fields[2],
                        "filing_date": fields[3],
                        "complete_submission_url": "https://www.sec.gov/Archives/" + fields[4].lstrip("/"),
                    })
    return rows


def archive_url(day: str) -> str:
    quarter = (int(day[5:7]) - 1) // 3 + 1
    return f"https://www.sec.gov/Archives/edgar/Feed/2026/QTR{quarter}/{day.replace('-', '')}.nc.tar.gz"


def free_gib(path: Path) -> float:
    stat = os.statvfs(path)
    return stat.f_bavail * stat.f_frsize / 1024**3


def retained_gib(path: Path) -> float:
    total = 0
    if path.exists():
        for root, _, files in os.walk(path):
            for name in files:
                total += (Path(root) / name).stat().st_size
    return total / 1024**3


def audit(output: Path, *, allow_partial: bool = False) -> dict:
    master_rows = index_rows()
    master_accessions = {row["accession_number"] for row in master_rows}
    days = sorted({row["filing_date"] for row in master_rows})
    member_by_accession: dict[str, list[dict[str, str]]] = {}
    completed = []
    incomplete = []
    for day in days:
        day_dir = output / day
        summary_file = day_dir / "feed_stream_summary.json"
        inventory_file = day_dir / "feed_member_inventory.csv"
        if not summary_file.exists() or not inventory_file.exists():
            incomplete.append(day)
            continue
        summary = json.loads(summary_file.read_text())
        if not summary.get("archive_integrity_complete"):
            incomplete.append(day)
            continue
        completed.append(day)
        with inventory_file.open(newline="") as stream:
            for row in csv.DictReader(stream):
                member_by_accession.setdefault(row["accession_number"], []).append(row)
    if incomplete and not allow_partial:
        raise RuntimeError(f"Refusing final census while {len(incomplete)} days are incomplete")
    output.mkdir(parents=True, exist_ok=True)
    ledger_file = output / ("master_accession_ledger_partial.csv" if incomplete else "master_accession_ledger.csv")
    with ledger_file.open("x", newline="") as stream:
        fields = [
            "accession_number", "cik", "company_name", "form", "filing_date",
            "complete_submission_url", "feed_member_count", "feed_days",
            "feed_member_sha256", "source_archive_url", "feed_status",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in master_rows:
            accession = row["accession_number"]
            members = member_by_accession.get(accession, [])
            indexed_day_complete = row["filing_date"] in completed
            writer.writerow({
                **row,
                "feed_member_count": len(members),
                "feed_days": "|".join(sorted({m["archive_url"][-18:-10] for m in members})),
                "feed_member_sha256": "|".join(m["member_sha256"] for m in members),
                "source_archive_url": "|".join(sorted({m["archive_url"] for m in members})),
                "feed_status": "found" if members else ("unresolved" if indexed_day_complete else "day_pending"),
            })
    extras_file = output / ("feed_only_accessions_partial.csv" if incomplete else "feed_only_accessions.csv")
    with extras_file.open("x", newline="") as stream:
        fields = [
            "accession_number", "tar_member", "member_bytes", "member_sha256", "archive_url",
            "cik", "company_name", "form", "submission_form", "submission_filing_date", "submission_ciks",
            "content_selected", "selection_reason",
            "signature_hits", "document_headers", "signature_screened",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for accession, members in member_by_accession.items():
            if accession not in master_accessions:
                writer.writerows(members)
    missing_rows = [row for row in master_rows if row["accession_number"] not in member_by_accession and row["filing_date"] in completed]
    pending_rows = [row for row in master_rows if row["accession_number"] not in member_by_accession and row["filing_date"] in incomplete]
    summary = {
        "official_master_raw_rows": len(master_rows),
        "official_master_unique_cik_accession_pairs": len({(row["cik"], row["accession_number"]) for row in master_rows}),
        "official_master_unique_accessions": len(master_accessions),
        "expected_days": len(days),
        "archive_integrity_complete_days": len(completed),
        "incomplete_days": incomplete,
        "master_raw_rows_found_in_feed_union": len(master_rows) - len(missing_rows) - len(pending_rows),
        "master_unique_accessions_found_in_feed_union": len(master_accessions & member_by_accession.keys()),
        "unresolved_master_raw_rows_on_completed_days": len(missing_rows),
        "unresolved_master_unique_accessions_on_completed_days": len({row["accession_number"] for row in missing_rows}),
        "unresolved_master_forms": dict(Counter(row["form"] for row in missing_rows)),
        "feed_only_accessions": sum(a not in master_accessions for a in member_by_accession),
        "total_unique_feed_accessions": len(member_by_accession),
        "master_ledger": str(ledger_file),
        "feed_only_ledger": str(extras_file),
    }
    summary_file = output / ("global_reconciliation_partial.json" if incomplete else "global_reconciliation.json")
    summary_file.write_text(json.dumps(summary, indent=2))
    return summary


def run(args: argparse.Namespace) -> int:
    master_rows = index_rows()
    days = sorted({row["filing_date"] for row in master_rows})
    accessions = {row["accession_number"] for row in master_rows}
    pairs = {(row["cik"], row["accession_number"]) for row in master_rows}
    if len(days) != 74 or len(master_rows) != 367387 or len(pairs) != 367371 or len(accessions) != 257675:
        raise RuntimeError(
            f"Official dated master index changed: {len(days)} days, {len(master_rows)} raw rows, "
            f"{len(pairs)} CIK-accession pairs, {len(accessions)} unique accessions"
        )
    args.output.mkdir(parents=True, exist_ok=True)
    queue = []
    for day in days:
        day_dir = args.output / day
        summary_file = day_dir / "feed_stream_summary.json"
        if summary_file.exists():
            summary = json.loads(summary_file.read_text())
            if summary.get("archive_integrity_complete"):
                continue
            raise RuntimeError(f"Existing incomplete day requires inspection: {day_dir}")
        if day_dir.exists():
            files = list(day_dir.iterdir())
            known_429_logs = bool(files) and all(
                file.is_file() and file.name.startswith("worker") and file.name.endswith(".log")
                and "HTTP Error 429" in file.read_text(errors="replace")
                for file in files
            )
            if not (args.resume_http_429 and known_429_logs):
                raise RuntimeError(f"Existing partial day requires inspection: {day_dir}")
        queue.append(day)
    active: dict[str, tuple[subprocess.Popen, object]] = {}
    failed = []
    throttled = False
    next_start = 0.0
    try:
        while queue or active:
            for day, (proc, log) in list(active.items()):
                code = proc.poll()
                if code is None:
                    continue
                log_path = Path(log.name)
                log.close()
                del active[day]
                summary_file = args.output / day / "feed_stream_summary.json"
                if code or not summary_file.exists():
                    failed.append({"day": day, "exit_code": code, "log": str(log_path)})
                    print(json.dumps({"event": "feed_day_failed", **failed[-1]}), flush=True)
                    if "HTTP Error 429" in log_path.read_text(errors="replace"):
                        throttled = True
                        print(json.dumps({"event": "sec_rate_limited_stop", "day": day}), flush=True)
                else:
                    summary = json.loads(summary_file.read_text())
                    print(json.dumps({
                        "event": "feed_day_complete", "day": day,
                        "compressed_bytes": summary["compressed_bytes"],
                        "feed_accessions": summary["feed_accessions"],
                        "master_missing_same_day": len(summary["missing_from_feed"]),
                        "documents_saved": summary["selected_documents_extracted"],
                        "seconds": summary["elapsed_seconds"],
                    }), flush=True)
            if throttled and not active:
                break
            if queue and not throttled and len(active) < args.max_workers and time.monotonic() >= next_start:
                if free_gib(args.output) < args.min_free_gib or retained_gib(args.output) > args.max_retained_gib:
                    print(json.dumps({"event": "disk_guard", "free_gib": round(free_gib(args.output), 2), "retained_gib": round(retained_gib(args.output), 2)}), flush=True)
                    break
                day = queue.pop(0)
                day_dir = args.output / day
                day_dir.mkdir(exist_ok=True)
                previous_logs = list(day_dir.glob("worker*.log"))
                log_name = "worker.log" if not previous_logs else f"worker_attempt_{len(previous_logs) + 1}.log"
                log = (day_dir / log_name).open("x")
                quarter = (int(day[5:7]) - 1) // 3 + 1
                command = [
                    sys.executable, str(DAY_SCRIPT),
                    "--day", day,
                    "--manifest", str(MANIFEST),
                    "--master-index", str(MASTER_DIR / f"2026-QTR{quarter}-master.gz"),
                    "--extra-cik-csv", str(EXACT_CIKS),
                    "--min-score", str(args.min_score),
                    "--output-dir", str(day_dir),
                    "--archive-url", archive_url(day),
                    "--user-agent", args.user_agent,
                ]
                proc = subprocess.Popen(command, cwd=BASE, stdout=log, stderr=subprocess.STDOUT)
                active[day] = (proc, log)
                next_start = time.monotonic() + args.start_spacing_seconds
                print(json.dumps({"event": "feed_day_started", "day": day, "pid": proc.pid, "active": len(active)}), flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        print(json.dumps({"event": "driver_interrupted", "active_days": list(active), "queued_days": len(queue)}), flush=True)
        for proc, log in active.values():
            proc.wait()
            log.close()
        raise
    if queue or failed:
        print(json.dumps({"event": "bulk_incomplete", "queued_days": queue, "failed_days": failed}), flush=True)
        return 2
    summary = audit(args.output)
    print(json.dumps({"event": "global_reconciliation", **summary}), flush=True)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--user-agent", default="ai-bubble research ted1508@gmail.com")
    parser.add_argument("--min-score", type=int, default=75)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--start-spacing-seconds", type=float, default=2.0)
    parser.add_argument("--min-free-gib", type=float, default=50.0)
    parser.add_argument("--max-retained-gib", type=float, default=120.0)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--allow-partial-audit", action="store_true")
    parser.add_argument("--resume-http-429", action="store_true")
    args = parser.parse_args()
    if args.audit_only:
        print(json.dumps(audit(args.output, allow_partial=args.allow_partial_audit), indent=2))
    else:
        raise SystemExit(run(args))


if __name__ == "__main__":
    main()
