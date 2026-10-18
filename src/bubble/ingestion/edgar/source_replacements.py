"""Verify explicitly reviewed copies of filings whose selected URLs no longer work."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from collections.abc import Callable

MANIFEST_NAME = "source_document_replacements.json"


def verified_source_replacements(
    directory: Path,
    document: Callable[[str], dict[str, str] | None],
) -> list[dict[str, Any]]:
    """Require acquired bytes, the same accession and explicit identity evidence.

    The inventory retains the actual retrieval URL. This manifest never changes
    the original selection or asserts that its failed HTTP request succeeded.
    """
    manifest = directory / MANIFEST_NAME
    if not manifest.is_file():
        return []
    value = json.loads(manifest.read_text())
    if value.get("version") != 1:
        raise ValueError("Unknown source replacement manifest version")
    verified = []
    seen = set()
    for row in value["replacements"]:
        original, replacement = row["original_url"], row["replacement_url"]
        if original in seen or original == replacement or row["original_http_status"] != 404:
            raise ValueError("Invalid or duplicate source replacement selection")
        seen.add(original)
        accession = row["accession_number"]
        if (
            urlsplit(original).hostname != "www.sec.gov"
            or accession.replace("-", "") not in urlsplit(original).path.split("/")
            or urlsplit(replacement).scheme != "https"
        ):
            raise ValueError("Source replacement does not identify its selected SEC accession")
        acquired = document(replacement)
        if (
            acquired is None
            or acquired.get("accession_number") != accession
            or acquired.get("content_hash") != row["content_hash"]
        ):
            raise ValueError("Replacement has no matching acquired document")
        path = Path(acquired["local_path"])
        opener = gzip.open if path.suffix == ".gz" else Path.open
        with opener(path, "rb") as stream:
            raw = stream.read(2 * 1024**2 + 1)
        if len(raw) > 2 * 1024**2 or hashlib.sha256(raw).hexdigest() != row["content_hash"]:
            raise ValueError("Changed or oversized source replacement bytes")
        text = raw.decode("utf-8")
        markers = row["identity_markers"]
        if not markers or any(not marker or marker not in text for marker in markers):
            raise ValueError("Replacement filing identity evidence does not match its bytes")
        kind = row["representation"]
        if kind == "sec_complete_submission":
            valid = (
                urlsplit(replacement).hostname == "www.sec.gov"
                and accession in text
                and "<SEC-DOCUMENT>" in text
                and "<FILENAME>primary_doc.xml" in text
            )
        elif kind == "issuer_filing_mirror":
            valid = (
                urlsplit(replacement).hostname == row["issuer_domain"]
                and accession in text
                and row["form"] in text
            )
        else:
            valid = False
        if not valid:
            raise ValueError("Unverified replacement representation or origin")
        verified.append(row)
    return verified
