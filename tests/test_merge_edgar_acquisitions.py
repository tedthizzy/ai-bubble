"""A merged acquisition must retain usable document provenance and unique keys."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from pathlib import Path

import pytest
from scripts.merge_edgar_acquisitions import merge_acquisitions


def _write_csv(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def _batch(root: Path, label: str, *, compressed: bool = False) -> dict[str, str]:
    root.mkdir()
    url = f"https://www.sec.gov/Archives/edgar/data/1/{label}.htm"
    raw = f"{label} senior secured notes due 2031".encode()
    document = root / (f"{label}.htm.gz" if compressed else f"{label}.htm")
    document.write_bytes(gzip.compress(raw) if compressed else raw)
    digest = hashlib.sha256(raw).hexdigest()
    inventory = {
        "filing_url": url,
        "local_path": str(document),
        "content_hash": digest,
        "downloaded_at": "2026-09-16T00:00:00Z",
    }
    deal = {
        "deal_id": f"deal-{label}",
        "source_uri": url,
        "content_hash": digest,
        "key_terms": json.dumps({"document_local_path": str(document), "term": "secured"}),
    }
    tranche = {
        "deal_id": f"deal-{label}",
        "tranche_id": "senior",
        "source_uri": url,
        "content_hash": digest,
        "name": "Senior notes",
    }
    _write_csv(root / "edgar_document_inventory.csv", list(inventory), [inventory])
    _write_csv(root / "deals.csv", list(deal), [deal])
    _write_csv(root / "tranches.csv", list(tranche), [tranche])
    return {"url": url, "document": str(document), "digest": digest}


def test_merge_disjoint_batches_keeps_paths_and_verifies_raw_gzip_bytes(tmp_path: Path) -> None:
    first = _batch(tmp_path / "a", "first")
    second = _batch(tmp_path / "b", "second", compressed=True)
    output = tmp_path / "merged"
    report = merge_acquisitions([tmp_path / "b", tmp_path / "a"], output, verify_bytes=True)
    with (output / "edgar_document_inventory.csv").open(newline="") as stream:
        inventory = list(csv.DictReader(stream))
    with (output / "deals.csv").open(newline="") as stream:
        deals = list(csv.DictReader(stream))
    with (output / "tranches.csv").open(newline="") as stream:
        tranches = list(csv.DictReader(stream))
    assert {row["filing_url"] for row in inventory} == {first["url"], second["url"]}
    assert {row["local_path"] for row in inventory} == {
        first["document"],
        second["document"],
    }
    assert len(deals) == len(tranches) == 2
    assert report["counts"]["edgar_document_inventory.csv"]["unique_keys"] == 2
    assert report["counts"]["edgar_document_inventory.csv"]["identical_duplicate_keys"] == 0
    assert report["verification"] == "raw_document_sha256"
    assert json.loads((output / "merge_manifest.json").read_text()) == report


def test_identical_url_from_separate_local_paths_deduplicates_without_rewriting(
    tmp_path: Path,
) -> None:
    first = _batch(tmp_path / "a", "same")
    _batch(tmp_path / "b", "same")
    output = tmp_path / "merged"
    report = merge_acquisitions([tmp_path / "a", tmp_path / "b"], output)
    with (output / "edgar_document_inventory.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1
    assert rows[0]["local_path"] == first["document"]
    assert report["counts"]["edgar_document_inventory.csv"]["identical_duplicate_keys"] == 1
    assert report["counts"]["deals.csv"]["identical_duplicate_keys"] == 1
    assert report["counts"]["tranches.csv"]["identical_duplicate_keys"] == 1


def test_candidate_from_second_copy_keeps_its_document_path(tmp_path: Path) -> None:
    _batch(tmp_path / "a", "same")
    second = _batch(tmp_path / "b", "same")
    _write_csv(
        tmp_path / "a" / "deals.csv",
        ["deal_id", "source_uri", "content_hash", "key_terms"],
        [],
    )
    _write_csv(
        tmp_path / "a" / "tranches.csv",
        ["deal_id", "tranche_id", "source_uri", "content_hash", "name"],
        [],
    )
    output = tmp_path / "merged"
    merge_acquisitions([tmp_path / "a", tmp_path / "b"], output)
    with (output / "deals.csv").open(newline="") as stream:
        deal = next(csv.DictReader(stream))
    assert json.loads(deal["key_terms"])["document_local_path"] == second["document"]


def test_conflicting_duplicate_url_rejected_before_output(tmp_path: Path) -> None:
    _batch(tmp_path / "a", "same")
    _batch(tmp_path / "b", "same")
    path = tmp_path / "b" / "edgar_document_inventory.csv"
    with path.open(newline="") as stream:
        row = next(csv.DictReader(stream))
    row["content_hash"] = "0" * 64
    _write_csv(path, list(row), [row])
    output = tmp_path / "merged"
    with pytest.raises(ValueError, match="Conflicting duplicate"):
        merge_acquisitions([tmp_path / "a", tmp_path / "b"], output)
    assert not output.exists()


def test_conflicting_duplicate_deal_rejected_before_output(tmp_path: Path) -> None:
    _batch(tmp_path / "a", "same")
    _batch(tmp_path / "b", "same")
    path = tmp_path / "b" / "deals.csv"
    with path.open(newline="") as stream:
        row = next(csv.DictReader(stream))
    row["key_terms"] = json.dumps({"document_local_path": row["source_uri"], "term": "different"})
    _write_csv(path, list(row), [row])
    output = tmp_path / "merged"
    with pytest.raises(ValueError, match=r"Conflicting duplicate deals\.csv"):
        merge_acquisitions([tmp_path / "a", tmp_path / "b"], output)
    assert not output.exists()


def test_missing_or_modified_raw_document_blocks_verified_merge(tmp_path: Path) -> None:
    batch = _batch(tmp_path / "source", "test")
    document = Path(batch["document"])
    document.write_bytes(b"different document")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        merge_acquisitions([tmp_path / "source"], tmp_path / "bad", verify_bytes=True)
    assert not (tmp_path / "bad").exists()
    inventory_path = tmp_path / "source" / "edgar_document_inventory.csv"
    with inventory_path.open(newline="") as stream:
        row = next(csv.DictReader(stream))
    row["local_path"] = str(tmp_path / "source" / "not-acquired.htm")
    _write_csv(inventory_path, list(row), [row])
    with pytest.raises(FileNotFoundError, match="local_path is missing"):
        merge_acquisitions([tmp_path / "source"], tmp_path / "missing")
    assert not (tmp_path / "missing").exists()


def test_existing_output_is_never_replaced(tmp_path: Path) -> None:
    _batch(tmp_path / "source", "test")
    output = tmp_path / "merged"
    output.mkdir()
    marker = output / "keep.txt"
    marker.write_text("original")
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        merge_acquisitions([tmp_path / "source"], output)
    assert marker.read_text() == "original"
