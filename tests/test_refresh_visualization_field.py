import csv
import hashlib
import json

import pytest
from scripts.refresh_visualization_field import build_field


def write(path, fields, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fixture(tmp_path):
    nodes = [
        {
            "node_id": f"entity:{i}",
            "node_type": "entity",
            "name": f"Party {i}",
            "deal_id": "",
            "notional_usd": "0",
        }
        for i in range(10)
    ]
    nodes.append(
        {
            "node_id": "contract:one",
            "node_type": "deal",
            "name": "One instrument",
            "deal_id": "one",
            "notional_usd": "100",
        }
    )
    edges = [
        {
            "relationship_type": "OBLIGATED_UNDER_DEAL" if i < 5 else "DEAL_RISK_BEARER",
            "deal_id": "one",
            "source_id": f"entity:{i}" if i < 5 else "contract:one",
            "target_id": "contract:one" if i < 5 else f"entity:{i}",
        }
        for i in range(10)
    ]
    records = {}
    for kind, rows in (("nodes", nodes), ("edges", edges + edges)):
        path = tmp_path / f"contract_{kind}.csv"
        write(path, list(rows[0]), rows)
        records[f"contract_{kind}_csv"] = {
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    (tmp_path / "input_manifest.json").write_text(
        json.dumps({"as_of": "2026-10-17", "mode": "complete", "outputs": records})
    )


def test_all_parties_survive_without_the_old_four_party_cap(tmp_path):
    fixture(tmp_path)
    field, layout = build_field(tmp_path, {"nodes": []}, "2026-10-17")
    assert field["entities"] == 10
    assert field["deals"] == 1
    assert len(field["links"]) == 25
    assert all(row[2:] == [100, 1] for row in field["links"])
    assert len(layout["field"]) == 10
    assert all(row[1:3] == [100, 1] for row in field["nodes"])


def test_old_positions_remain_and_changed_primary_graph_bytes_stop(tmp_path):
    fixture(tmp_path)
    graph = {
        "nodes": [],
        "field": {"nodes": [["Party 0", 0, 0, 0]]},
        "layout": {"field": [[1, 2, 3]]},
    }
    _, layout = build_field(tmp_path, graph, "2026-10-17")
    assert layout["field"][0] == [1, 2, 3]
    (tmp_path / "contract_nodes.csv").write_text("Changed graph input")
    with pytest.raises(ValueError, match="Changed capital graph input"):
        build_field(tmp_path, graph, "2026-10-17")
