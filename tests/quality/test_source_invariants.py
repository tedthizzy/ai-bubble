from __future__ import annotations

import pytest

from bubble.models.base import Provenance, SourceType
from bubble.quality.source_invariants import (
    SourceDataInvariantError,
    assert_production_provenance,
    assert_source_row,
    is_source_backed_row,
)


def test_source_invariant_rejects_inferred_provenance():
    provenance = Provenance(
        source_uri="model:inferred_estimate:test",
        source_type=SourceType.INFERRED,
        confidence=0.5,
        content_hash=Provenance.compute_content_hash("inferred"),
    )

    with pytest.raises(SourceDataInvariantError):
        assert_production_provenance(provenance, context="Deal")


def test_source_invariant_rejects_blocked_source_rows():
    with pytest.raises(SourceDataInvariantError):
        assert_source_row(
            {"source_uri": "model:inferred_estimate:old-path", "source_type": "sec_edgar"},
            context="deal:old",
        )


def test_source_invariant_allows_source_backed_rows():
    assert_source_row(
        {
            "source_uri": "https://www.sec.gov/Archives/edgar/data/x/y.htm",
            "source_type": "sec_edgar",
        },
        context="deal:source-backed",
    )


def test_source_invariant_rejects_missing_source_uri():
    with pytest.raises(SourceDataInvariantError):
        assert_source_row({"source_type": "sec_edgar"}, context="deal:missing-source")


def test_source_invariant_rejects_seed_rows():
    with pytest.raises(SourceDataInvariantError):
        assert_source_row(
            {"source_uri": "seed:private-priority-list", "source_type": "manual_curated"},
            context="deal:seed",
        )


def test_source_backed_row_helper_returns_false_for_blocked_rows():
    assert not is_source_backed_row({"source_uri": "demo:old-path", "source_type": "sec_edgar"})


def test_production_provenance_requires_sha256_content_hash():
    provenance = Provenance(
        source_uri="https://www.sec.gov/Archives/edgar/data/x/y.htm",
        source_type=SourceType.SEC_EDGAR,
        confidence=0.9,
        content_hash="capex-fact",
    )

    with pytest.raises(SourceDataInvariantError):
        assert_production_provenance(provenance, context="Deal")
