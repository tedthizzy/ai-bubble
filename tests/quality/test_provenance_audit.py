"""Tests for the branch-local provenance-integrity audit.

Fixture-based only: every test builds synthetic rows / tmp dirs. Nothing reads
the live data/ corpus, so checks stay stable as the corpus is rebuilt.
"""

from __future__ import annotations

from bubble.quality.provenance_audit import (
    check_divergent_document_hashes,
    check_hash_conflicting_document_ids,
    check_invalid_hashes,
)

HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


def test_flags_same_document_id_with_divergent_content_hash() -> None:
    rows = [
        {"document_id": "acc-1/doc.htm", "content_hash": HASH_A},
        {"document_id": "acc-1/doc.htm", "content_hash": HASH_B},
        {"document_id": "acc-2/doc.htm", "content_hash": HASH_C},
    ]

    findings = check_divergent_document_hashes(rows, source_label="deals.csv")

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "divergent_document_hash"
    assert finding.severity == "error"
    assert finding.source == "deals.csv"
    assert "acc-1/doc.htm" in finding.message


def test_flags_non_hex_and_blank_content_hash() -> None:
    rows = [
        {"content_hash": HASH_A, "source_uri": "https://x/1"},
        {"content_hash": "5e6f7g8h", "source_uri": "https://x/2"},  # non-hex / short
        {"content_hash": "", "source_uri": "https://x/3"},  # blank but has source_uri
    ]

    findings = check_invalid_hashes(rows, source_label="deals.csv")

    checks = sorted(f.check for f in findings)
    assert checks == ["invalid_content_hash", "missing_content_hash"]
    assert all(f.severity == "error" for f in findings)


def test_flags_same_hash_with_conflicting_document_ids() -> None:
    rows = [
        {"content_hash": HASH_A, "document_id": "doc-1"},
        {"content_hash": HASH_A, "document_id": "doc-2"},
        {"content_hash": HASH_B, "document_id": "doc-3"},
    ]

    findings = check_hash_conflicting_document_ids(rows, source_label="inv.csv")

    assert len(findings) == 1
    assert findings[0].check == "hash_conflicting_document_ids"
    assert findings[0].severity == "warning"
