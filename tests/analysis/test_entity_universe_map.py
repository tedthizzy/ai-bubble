"""Empirical entity-universe composition map."""

from __future__ import annotations

from bubble.analysis.entity_universe_map import aggregate_entity_universe


def _e(name, bucket, filer="yes_sec", debt="some"):
    return {"name": name, "bucket": bucket, "public_filer": filer, "has_ai_infra_debt": debt}


def test_blocks_empty() -> None:
    assert aggregate_entity_universe({})["status"] == "blocked_no_classified_entities"
    assert (
        aggregate_entity_universe({"all_entities": []})["status"]
        == "blocked_no_classified_entities"
    )


def test_composition_and_confirmed() -> None:
    payload = {
        "all_entities": [
            _e("CoreWeave", "financed_ai_infra_leveraged"),
            _e("Applied Digital", "financed_ai_infra_leveraged"),
            _e("Microsoft", "hyperscaler_demand", debt="no"),
            _e("Amazon", "hyperscaler_demand", debt="no"),
            _e("Equinix", "investment_grade_datacenter"),
            _e("PG&E", "utility_or_power", filer="yes_sec", debt="no"),
            _e("NVIDIA", "chip_or_equipment_supplier"),
            _e("Riot", "crypto_primary_marginal_ai"),
            _e("CoreWeave Financing DDTL V", "financing_spv", filer="private"),
            _e("junk row", "not_relevant_or_unknown", filer="unknown", debt="unknown"),
        ],
        "confirmed_financed": [
            {"name": "CoreWeave", "ticker": "CRWV", "debt": 25e9},
        ],
    }
    out = aggregate_entity_universe(payload)
    assert out["status"] == "source_backed"
    assert out["entity_count"] == 10
    assert out["by_bucket"]["financed_ai_infra_leveraged"] == 2
    assert out["by_bucket"]["hyperscaler_demand"] == 2
    assert out["provisional_financed_leveraged"] == 2
    assert out["confirmed_financed_leveraged_count"] == 1
    assert out["public_filer_entities"] == 8  # 8 yes_sec (all but the SPV + junk)
    assert "universe_composition" in out["composition_read"]
    # by_bucket is sorted descending
    counts = list(out["by_bucket"].values())
    assert counts == sorted(counts, reverse=True)
