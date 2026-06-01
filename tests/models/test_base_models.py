"""
Tests for the unbreakable core: Provenance + domain models.

These must never be allowed to regress.
"""

from bubble.models.base import (
    DealType,
    HumanReviewStatus,
    Provenance,
    SourceType,
)
from bubble.models.deal import Deal
from bubble.models.entity import Entity, EntityType


def test_provenance_content_hash():
    h1 = Provenance.compute_content_hash("hello world")
    h2 = Provenance.compute_content_hash(b"hello world")
    assert h1 == h2
    assert len(h1) == 64


def test_provenance_validation():
    prov = Provenance(
        source_uri="https://sec.gov/...",
        source_type=SourceType.SEC_EDGAR,
        confidence=0.92,
        content_hash="a" * 64,
    )
    assert prov.human_review_status == HumanReviewStatus.PENDING


def test_entity_roundtrip():
    prov = Provenance(
        source_uri="seed",
        source_type=SourceType.MANUAL_CURATED,
        confidence=1.0,
        content_hash="b" * 64,
    )
    e = Entity(
        name="Test Hyperscaler",
        cik="0000123456",
        entity_type=EntityType.HYPERSCALER,
        provenance=prov,
        confidence=0.99,
    )
    assert e.display_name() == "Test Hyperscaler"
    assert e.cik == "0000123456"


def test_deal_with_tranches():
    prov = Provenance(
        source_uri="test",
        source_type=SourceType.SEC_EDGAR,
        confidence=0.88,
        content_hash="c" * 64,
    )
    deal = Deal(
        deal_type=DealType.DEBT_FACILITY,
        parties=["ent-1", "ent-2"],
        notional_amount_usd=1_250_000_000,
        is_non_recourse=True,
        bankruptcy_remote_spv=True,
        provenance=prov,
        confidence=0.88,
    )
    assert deal.deal_type == DealType.DEBT_FACILITY
    assert deal.is_non_recourse is True
