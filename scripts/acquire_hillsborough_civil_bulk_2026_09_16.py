"""Acquire the Hillsborough County Clerk's published monthly civil case and event CSVs.

The Clerk retains one year of monthly files. Raw case styles can contain personal
names, so the downloaded records belong in gitignored data/ and the manifest
records only file-level counts, hashes, and coverage dates.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html.parser
import json
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


INDEX_URL = "https://publicrec.hillsclerk.com/Civil/bulkdata/"
PATTERN = re.compile(r"^Bulk Data (Case|Event) File_ (\d{2})-10-(\d{4})\.csv$")


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
                    raise RuntimeError(f"HTTP {response.status}: {url}")
                content = response.read()
                declared = response.headers.get("Content-Length")
                if declared and len(content) != int(declared):
                    raise RuntimeError(f"short response: {len(content)} != {declared}")
                return content
        except Exception as exc:
            errors.append(f"attempt {attempt + 1}: {type(exc).__name__}: {exc}")
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"{url}: {'; '.join(errors)}")


def discover(index_html: bytes, first_month: str, last_month: str) -> list[tuple[str, str]]:
    parser = Links()
    parser.feed(index_html.decode("utf-8", errors="replace"))
    found = []
    for href in parser.hrefs:
        name = urllib.parse.unquote(urllib.parse.urlparse(href).path.rsplit("/", 1)[-1])
        match = PATTERN.fullmatch(name)
        if not match:
            continue
        month = f"{match.group(3)}-{match.group(2)}"
        if first_month <= month <= last_month:
            found.append((name, urllib.parse.urljoin(INDEX_URL, href)))
    return sorted(set(found))


def parse_csv(path: Path) -> tuple[int, list[str], str | None, str | None]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames or []
        rows = 0
        dates: list[str] = []
        for row in reader:
            rows += 1
            date = row.get("DtFile") or row.get("EventDate") or row.get("DtEvent")
            if date:
                dates.append(date)
    return rows, header, min(dates, default=None), max(dates, default=None)


def acquire_one(name: str, url: str, output_dir: Path) -> dict[str, object]:
    final_path = output_dir / name
    if final_path.exists():
        content = final_path.read_bytes()
        reused = True
    else:
        content = fetch(url)
        if not content or b"<html" in content[:200].lower():
            raise RuntimeError(f"invalid CSV response: {url}")
        final_path.write_bytes(content)
        reused = False
    rows, header, earliest, latest = parse_csv(final_path)
    if not header or rows == 0:
        raise RuntimeError(f"empty or malformed CSV: {final_path}")
    return {
        "file": name,
        "source_url": url,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "parsed_rows": rows,
        "header": header,
        "earliest_date_string": earliest,
        "latest_date_string": latest,
        "reused_existing_file": reused,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("data/off_edgar_expansion_2026-09-16/hillsborough_civil"),
    )
    parser.add_argument("--first-month", default="2025-10")
    parser.add_argument("--last-month", default="2026-09")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    index_html = fetch(INDEX_URL)
    index_path = args.output_dir / "directory_index_2026-09-16.html"
    if not index_path.exists():
        index_path.write_bytes(index_html)
    targets = discover(index_html, args.first_month, args.last_month)
    kinds = {"Case": 0, "Event": 0}
    for name, _ in targets:
        kinds[PATTERN.fullmatch(name).group(1)] += 1
    if kinds != {"Case": 12, "Event": 12}:
        raise RuntimeError(f"expected twelve monthly files of each kind: {kinds}")
    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(acquire_one, name, url, args.output_dir): name
            for name, url in targets
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"{result['file']}: {result['parsed_rows']:,} rows", flush=True)
    manifest = {
        "source_index_url": INDEX_URL,
        "source_readme_url": urllib.parse.urljoin(INDEX_URL, "Readme.pdf"),
        "index_sha256": hashlib.sha256(index_html).hexdigest(),
        "acquired_at_utc": datetime.now(timezone.utc).isoformat(),
        "month_bounds": [args.first_month, args.last_month],
        "files": sorted(results, key=lambda row: row["file"]),
        "caveat": (
            "The monthly civil case and event files cover one county and are not "
            "a national court docket census. Case types and party names alone do "
            "not prove financial distress or an AI-related cause."
        ),
    }
    manifest_path = args.output_dir / "acquisition_manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"refusing to overwrite manifest: {manifest_path}")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"manifest: {manifest_path}", flush=True)


if __name__ == "__main__":
    main()
