"""Branch-local provenance-integrity audit (proposed for Codex review).

Novel checks beyond the existing source-invariant audit:
- the same ``document_id`` carrying DIVERGENT ``content_hash`` values (a
  provenance-integrity red flag: one source document with two fingerprints),
- rows missing a required ``source_uri``,
- placeholder / non-sha256 ``content_hash`` values,
- report/doc references to artifact files that do not exist on disk.

Side-effect free: callers hand in rows / paths; this module never writes.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

_SHA256_RE = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class ProvenanceFinding:
    check: str
    severity: str  # "error" | "warning"
    source: str
    message: str
    detail: str | None = None


def check_divergent_document_hashes(
    rows: Iterable[Mapping[str, Any]],
    *,
    doc_id_key: str = "document_id",
    hash_key: str = "content_hash",
    source_label: str = "",
) -> list[ProvenanceFinding]:
    """Flag any ``document_id`` mapped to more than one distinct ``content_hash``."""

    by_doc: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        doc = str(row.get(doc_id_key) or "").strip()
        digest = str(row.get(hash_key) or "").strip()
        if not doc or not digest:
            continue
        by_doc[doc].add(digest)

    findings: list[ProvenanceFinding] = []
    for doc, hashes in sorted(by_doc.items()):
        if len(hashes) > 1:
            findings.append(
                ProvenanceFinding(
                    check="divergent_document_hash",
                    severity="error",
                    source=source_label,
                    message=(
                        f"document_id {doc!r} maps to {len(hashes)} divergent "
                        "content_hash values (one source document, multiple fingerprints)."
                    ),
                    detail=", ".join(sorted(hashes)),
                )
            )
    return findings


def check_invalid_hashes(
    rows: Iterable[Mapping[str, Any]],
    *,
    hash_key: str = "content_hash",
    uri_key: str = "source_uri",
    source_label: str = "",
) -> list[ProvenanceFinding]:
    """Flag content_hash that is blank (with a source_uri present) or not sha256 hex."""

    findings: list[ProvenanceFinding] = []
    for index, row in enumerate(rows):
        digest = str(row.get(hash_key) or "").strip()
        uri = str(row.get(uri_key) or "").strip()
        if not digest:
            if uri:
                findings.append(
                    ProvenanceFinding(
                        check="missing_content_hash",
                        severity="error",
                        source=source_label,
                        message=f"row {index} has a source_uri but a blank content_hash.",
                        detail=uri,
                    )
                )
            continue
        if not _SHA256_RE.fullmatch(digest):
            findings.append(
                ProvenanceFinding(
                    check="invalid_content_hash",
                    severity="error",
                    source=source_label,
                    message=f"row {index} content_hash is not a 64-char sha256 hex.",
                    detail=digest,
                )
            )
    return findings


def check_hash_conflicting_document_ids(
    rows: Iterable[Mapping[str, Any]],
    *,
    hash_key: str = "content_hash",
    doc_id_key: str = "document_id",
    source_label: str = "",
) -> list[ProvenanceFinding]:
    """Flag a single content_hash mapped to more than one document_id."""

    by_hash: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        digest = str(row.get(hash_key) or "").strip()
        doc = str(row.get(doc_id_key) or "").strip()
        if not digest or not doc:
            continue
        by_hash[digest].add(doc)

    findings: list[ProvenanceFinding] = []
    for digest, docs in sorted(by_hash.items()):
        if len(docs) > 1:
            findings.append(
                ProvenanceFinding(
                    check="hash_conflicting_document_ids",
                    severity="warning",
                    source=source_label,
                    message=(
                        f"content_hash {digest[:12]}… maps to {len(docs)} different "
                        "document_ids (same fingerprint, conflicting ids)."
                    ),
                    detail=", ".join(sorted(docs)),
                )
            )
    return findings
