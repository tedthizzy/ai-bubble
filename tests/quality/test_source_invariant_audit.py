from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from bubble.quality.source_invariant_audit import audit_source_invariants

if TYPE_CHECKING:
    from pathlib import Path


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_source_invariant_audit_passes_real_acquisition_rows(tmp_path: Path):
    _write_csv(
        tmp_path / "source_acquisition" / "source_rows" / "queue_records.csv",
        [
            {
                "queue_id": "Q-1",
                "source_id": "queue-source",
                "source_uri": "https://example.com/queue.csv",
                "source_type": "grid_interconnection_queue",
                "retrieved_at": "2026-06-01T00:00:00+00:00",
                "content_hash": "a" * 64,
                "local_path": "data/source_acquisition/raw/queue.csv",
                "record_index": "0",
            }
        ],
    )

    audit = audit_source_invariants([tmp_path])

    assert audit.passed is True
    assert audit.violations == []
    assert audit.rows_with_source_uri == 1
    assert audit.source_uri_values_checked == 1


def test_source_invariant_audit_rejects_seed_rows(tmp_path: Path):
    _write_csv(
        tmp_path / "capital" / "deals.csv",
        [
            {
                "deal_id": "seed-deal",
                "source_uri": "seed:priority-list",
                "source_type": "manual_curated",
                "content_hash": "a" * 64,
            }
        ],
    )

    audit = audit_source_invariants([tmp_path])

    assert audit.passed is False
    assert audit.violations
    assert "source_uri is not allowed" in audit.violations[0].message


def test_source_invariant_audit_requires_direct_acquisition_hash_and_timestamp(
    tmp_path: Path,
):
    _write_csv(
        tmp_path / "source_acquisition" / "source_rows" / "ppas.csv",
        [
            {
                "ID": "1",
                "source_uri": "https://data.ferc.gov/table.csv",
                "source_type": "ferc",
                "retrieved_at": "",
                "content_hash": "",
            }
        ],
    )

    audit = audit_source_invariants([tmp_path])

    assert audit.passed is False
    messages = {finding.message for finding in audit.violations}
    assert "Row has source URI evidence but no content hash field/value." in messages
    assert "Direct acquisition row has no retrieval/download timestamp." in messages


def test_source_invariant_audit_warns_on_derived_missing_hash(tmp_path: Path):
    _write_csv(
        tmp_path / "reports" / "weak_link_candidates.csv",
        [
            {
                "weak_link_id": "weak-link:1",
                "source_uris": '["https://example.com/source.csv"]',
                "content_hashes": "",
            }
        ],
    )

    audit = audit_source_invariants([tmp_path])

    assert audit.passed is True
    assert audit.violations == []
    assert audit.warnings
    assert audit.warnings[0].field == "content_hash"
