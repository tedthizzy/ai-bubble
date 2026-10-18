from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from scripts.build_public_refresh_report import relationship_summary

ROOT = Path(__file__).resolve().parents[1]


def saved_review(tmp_path):
    path = tmp_path / "analysis/core_relationship_review_2026-10-17.json"
    path.parent.mkdir()
    review = json.loads((ROOT / path.relative_to(tmp_path)).read_text())
    manifest = tmp_path / review["private_capital_source_manifest"]
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"as_of": "2026-10-17", "sources": []}))
    review["private_capital_source_manifest_sha256"] = hashlib.sha256(
        manifest.read_bytes()
    ).hexdigest()
    path.write_text(json.dumps(review))
    return path, manifest, review


def test_report_retains_overlapping_rounds_and_undrawn_facilities_as_separate_measures(tmp_path):
    saved_review(tmp_path)
    summary, inputs = relationship_summary(tmp_path, "2026-10-17")
    assert len(inputs) == 2
    assert summary["reviewed_relationships"] == 148
    assert summary["capital_rounds"][0]["basis"] == "committed capital"
    assert summary["credit_facilities"][0]["drawn_at_close_usd"] == 0
    assert summary["credit_facilities"][0]["subsequent_draws_usd"] is None


def test_report_rejects_a_source_manifest_changed_after_review(tmp_path):
    _, manifest, _ = saved_review(tmp_path)
    manifest.write_text("{}")
    with pytest.raises(ValueError, match="manifest changed"):
        relationship_summary(tmp_path, "2026-10-17")


def test_report_rejects_sources_after_the_explicit_cutoff(tmp_path):
    path, manifest, review = saved_review(tmp_path)
    manifest.write_text(
        json.dumps({"as_of": "2026-10-17", "sources": [{"published": "2026-10-18"}]})
    )
    review["private_capital_source_manifest_sha256"] = hashlib.sha256(
        manifest.read_bytes()
    ).hexdigest()
    path.write_text(json.dumps(review))
    with pytest.raises(ValueError, match="postdates"):
        relationship_summary(tmp_path, "2026-10-17")
