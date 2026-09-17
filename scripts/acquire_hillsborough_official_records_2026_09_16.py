"""Acquire every D/P/M file in Hillsborough County's current official-record index.

The Clerk's D files include recorded document types, dates, and a consideration
field; P files contain party names. Raw files stay in gitignored data/.
"""

from __future__ import annotations

import argparse
import hashlib
import html.parser
import json
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path


INDEX_URL = "https://publicrec.hillsclerk.com/OfficialRecords/DailyIndexes/"
PATTERN = re.compile(r"^([DPM])(\d{8})(\d{2})(id|d)\.29$")
FIELD_COUNTS = {"D": 14, "P": 6, "M": 2}


class Links(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            href = dict(attrs).get("href")
            if href:
                self.hrefs.append(href)


def fetch(url: str) -> bytes:
    errors: list[str] = []
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=90) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status}")
                content = response.read()
                declared = response.headers.get("Content-Length")
                if declared and len(content) != int(declared):
                    raise RuntimeError(f"short response: {len(content)} != {declared}")
                return content
        except Exception as exc:
            errors.append(f"attempt {attempt + 1}: {type(exc).__name__}: {exc}")
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"{url}: {'; '.join(errors)}")


def discover(index_html: bytes) -> list[tuple[str, str]]:
    parser = Links()
    parser.feed(index_html.decode("utf-8", errors="replace"))
    found = []
    for href in parser.hrefs:
        name = urllib.parse.unquote(urllib.parse.urlparse(href).path.rsplit("/", 1)[-1])
        match = PATTERN.fullmatch(name)
        if not match:
            continue
        if (match.group(1) == "M") != (match.group(4) == "d"):
            raise RuntimeError(f"unexpected official-record suffix: {name}")
        found.append((name, urllib.parse.urljoin(INDEX_URL, href)))
    by_date: dict[str, set[str]] = {}
    for name, _ in found:
        match = PATTERN.fullmatch(name)
        by_date.setdefault(match.group(2), set()).add(match.group(1))
    incomplete = {date: kinds for date, kinds in by_date.items() if kinds != {"D", "P", "M"}}
    if incomplete:
        raise RuntimeError(f"incomplete D/P/M daily index: {incomplete}")
    return sorted(set(found))


def parse_file(content: bytes, kind: str) -> dict[str, object]:
    counts: Counter[str] = Counter()
    large_consideration_types: Counter[str] = Counter()
    record_dates: list[str] = []
    record_count = 0
    eof_count = None
    for line in content.splitlines():
        if not line.strip():
            continue
        parts = line.split(b"|")
        if parts[0] == b"EOF":
            eof_count = int(parts[1])
            continue
        if len(parts) == FIELD_COUNTS[kind] + 1 and parts[-1] == b"":
            parts.pop()
        if len(parts) != FIELD_COUNTS[kind]:
            raise RuntimeError(f"{kind} file record has {len(parts)} fields")
        record_count += 1
        if kind == "D":
            document_type = parts[3].decode("cp1252", errors="replace")
            counts[document_type] += 1
            record_dates.append(parts[11].decode("ascii", errors="replace"))
            amount_text = parts[13].decode("ascii", errors="replace").replace(",", "").strip()
            try:
                if amount_text and Decimal(amount_text) >= Decimal(1_000_000):
                    large_consideration_types[document_type] += 1
            except InvalidOperation:
                raise RuntimeError(f"unparseable consideration amount in {kind} file") from None
    if eof_count is None or eof_count != record_count:
        raise RuntimeError(f"EOF count {eof_count} differs from parsed {record_count}")
    return {
        "parsed_records": record_count,
        "eof_declared_records": eof_count,
        "document_type_counts": dict(counts) if kind == "D" else None,
        "consideration_ge_1m_type_counts": dict(large_consideration_types) if kind == "D" else None,
        "earliest_recorded_date_string": min(record_dates, default=None),
        "latest_recorded_date_string": max(record_dates, default=None),
    }


def acquire_one(name: str, url: str, output_dir: Path) -> dict[str, object]:
    kind = name[0]
    final_path = output_dir / name
    if final_path.exists():
        content = final_path.read_bytes()
        reused = True
    else:
        content = fetch(url)
        if not content:
            raise RuntimeError(f"empty official-record file: {url}")
        final_path.write_bytes(content)
        reused = False
    return {
        "file": name,
        "kind": kind,
        "source_url": url,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "reused_existing_file": reused,
        **parse_file(content, kind),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("data/off_edgar_expansion_2026-09-16/hillsborough_official_records"),
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    index_html = fetch(INDEX_URL)
    targets = discover(index_html)
    if not targets:
        raise RuntimeError("no official-record files discovered")
    index_path = args.output_dir / "directory_index_2026-09-16.html"
    if not index_path.exists():
        index_path.write_bytes(index_html)
    readme_path = args.output_dir / "readme.txt"
    if not readme_path.exists():
        readme_path.write_bytes(fetch(urllib.parse.urljoin(INDEX_URL, "readme.txt")))
    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(acquire_one, name, url, args.output_dir): name
            for name, url in targets
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"{result['file']}: {result['parsed_records']:,} records", flush=True)
    manifest = {
        "source_index_url": INDEX_URL,
        "source_readme_url": urllib.parse.urljoin(INDEX_URL, "readme.txt"),
        "index_sha256": hashlib.sha256(index_html).hexdigest(),
        "readme_sha256": hashlib.sha256(readme_path.read_bytes()).hexdigest(),
        "acquired_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": sorted(results, key=lambda row: row["file"]),
        "caveat": (
            "D files cover recorded or modified documents by export date. "
            "A consideration field is not an AI investment or current loan balance. "
            "P files contain personal names; raw data is not published in git."
        ),
    }
    manifest_path = args.output_dir / "acquisition_manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"refusing to overwrite manifest: {manifest_path}")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"manifest: {manifest_path}", flush=True)


if __name__ == "__main__":
    main()
