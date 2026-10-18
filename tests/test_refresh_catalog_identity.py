import csv
import json
from pathlib import Path

from scripts.refresh_public_sources import catalog_identity, missing_dynamic_sources


def source(start: int, revision: str = "current") -> dict[str, str]:
    return {
        "source_id": f"page-{start}", "source_uri": "https://example.test/api/dataset/17",
        "corpus": "ppas", "parser": "json",
        "meta_http_method": "POST", "meta_http_body": json.dumps({"startRow": start}),
        "meta_data_last_updated": revision, "meta_empty": "",
    }


def inventory(row: dict[str, str]) -> dict[str, str]:
    return {
        **{key: value for key, value in row.items() if not key.startswith("meta_")},
        "metadata": json.dumps({key[5:]: value for key, value in row.items()
                                if key.startswith("meta_") and value}),
    }


def write(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_post_pages_and_source_revisions_have_distinct_identities() -> None:
    assert catalog_identity(source(0)) == catalog_identity(inventory(source(0)), inventory=True)
    assert catalog_identity(source(0)) != catalog_identity(source(100))
    assert catalog_identity(source(0, "previous")) != catalog_identity(source(0))


def test_current_catalog_retains_new_pages_and_updated_existing_pages(tmp_path: Path) -> None:
    write(tmp_path / "dynamic_source_catalog.csv", [source(0), source(100), source(200)])
    write(tmp_path / "public/source_artifact_inventory.csv", [inventory(source(0, "previous"))])
    write(tmp_path / "dynamic/source_artifact_inventory.csv", [inventory(source(100))])
    selected = missing_dynamic_sources(tmp_path, ("public", "dynamic"))
    assert [row["source_id"] for row in selected] == ["page-0", "page-200"]
