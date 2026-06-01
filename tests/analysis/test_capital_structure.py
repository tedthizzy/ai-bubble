from datetime import date

from bubble.analysis.capital_structure import CapitalStructureAnalyzer
from bubble.models.base import DealType, HumanReviewStatus, Provenance, SourceType
from bubble.models.deal import Deal, DebtTranche


def _prov(
    source_uri: str,
    source_type: SourceType = SourceType.SEC_EDGAR,
    status: HumanReviewStatus = HumanReviewStatus.APPROVED,
) -> Provenance:
    return Provenance(
        source_uri=source_uri,
        source_type=source_type,
        confidence=0.9,
        human_review_status=status,
        content_hash=Provenance.compute_content_hash(source_uri),
    )


def _deals() -> list[Deal]:
    debt_prov = _prov("sec:coreweave-credit-agreement")
    tranche_a = DebtTranche(
        name="Term Loan A",
        seniority=1,
        notional_usd=1_000_000_000,
        maturity=date(2026, 12, 15),
        guarantors=["athene-wrapper"],
        provenance=debt_prov,
    )
    tranche_b = DebtTranche(
        name="Term Loan B",
        seniority=2,
        notional_usd=500_000_000,
        maturity=date(2027, 6, 30),
        provenance=debt_prov,
    )
    debt = Deal(
        deal_type=DealType.DEBT_FACILITY,
        title="CoreWeave SPV GPU collateral credit facility",
        parties=["coreweave-spv", "apollo-credit"],
        counterparty_roles={
            "borrower": ["coreweave-spv"],
            "lender": ["apollo-credit"],
            "insurer": ["athene-wrapper"],
        },
        debt_tranches=[tranche_a, tranche_b],
        bankruptcy_remote_spv=True,
        guarantees=["athene-wrapper"],
        provenance=debt_prov,
    )
    lease = Deal(
        deal_type=DealType.LEASE,
        title="Synthetic lease for AI campus",
        parties=["developer-spv", "hyperscaler-anchor"],
        counterparty_roles={
            "lessor": ["developer-spv"],
            "lessee": ["hyperscaler-anchor"],
        },
        notional_amount_usd=800_000_000,
        maturity_date=date(2028, 3, 31),
        is_non_recourse=True,
        key_terms={"synthetic_lease": True},
        provenance=_prov("sec:synthetic-lease"),
    )
    bond = Deal(
        deal_type=DealType.BOND,
        title="Data center secured notes",
        parties=["reit-issuer", "bondholders"],
        counterparty_roles={
            "borrower": ["reit-issuer"],
            "bondholder": ["insurance-general-account"],
        },
        notional_amount_usd=700_000_000,
        maturity_date=date(2030, 1, 15),
        provenance=_prov("company-ir:bond-pricing", SourceType.COMPANY_IR),
    )
    ppa = Deal(
        deal_type=DealType.PPA,
        title="Power purchase agreement",
        parties=["developer-spv", "utility"],
        notional_amount_usd=600_000_000,
        maturity_date=date(2035, 1, 1),
        provenance=_prov("state-puc:ppa", SourceType.STATE_PUC),
    )
    return [debt, lease, bond, ppa]


def test_capital_structure_metrics_quantify_leverage_refi_and_off_balance_sheet() -> None:
    metrics = CapitalStructureAnalyzer().analyze(_deals(), as_of=date(2026, 1, 1))

    assert metrics.deal_count == 4
    assert metrics.debt_like_deal_count == 3
    assert metrics.total_notional_usd == 3_600_000_000
    assert metrics.debt_like_notional_usd == 3_000_000_000
    assert metrics.distinct_deal_count == 4
    assert metrics.distinct_total_notional_usd == 3_600_000_000
    assert metrics.distinct_debt_like_deal_count == 3
    assert metrics.distinct_debt_like_notional_usd == 3_000_000_000
    assert metrics.duplicate_candidate_deal_count == 0
    assert metrics.duplicate_candidate_notional_usd == 0
    assert metrics.aggregate_obligation_deal_count == 0
    assert metrics.aggregate_obligation_notional_usd == 0
    assert metrics.aggregate_obligation_distinct_deal_count == 0
    assert metrics.aggregate_obligation_distinct_notional_usd == 0
    assert metrics.off_balance_sheet_usd == 2_300_000_000
    assert metrics.off_balance_sheet_pct == 0.7667
    assert metrics.guarantee_linked_deal_count == 1
    assert metrics.guarantee_linked_usd == 1_500_000_000
    assert metrics.spv_or_non_recourse_deal_count == 2
    assert metrics.spv_or_non_recourse_usd == 2_300_000_000
    assert metrics.reviewed_deal_count == 4
    assert metrics.reviewed_total_notional_usd == 3_600_000_000
    assert metrics.reviewed_debt_like_deal_count == 3
    assert metrics.reviewed_debt_like_notional_usd == 3_000_000_000
    assert metrics.pending_review_debt_like_deal_count == 0
    assert metrics.pending_review_debt_like_notional_usd == 0
    assert metrics.notional_review_required_deal_count == 0
    assert metrics.notional_review_required_usd == 0
    assert metrics.notional_review_required_distinct_deal_count == 0
    assert metrics.notional_review_required_distinct_usd == 0
    assert metrics.top_notional_review_items == []
    assert metrics.top_notional_review_distinct_items == []
    assert metrics.refinancing_wall_by_quarter == {
        "2026-Q4": 1_000_000_000,
        "2027-Q2": 500_000_000,
        "2028-Q1": 800_000_000,
        "2030-Q1": 700_000_000,
    }
    assert metrics.near_term_refinancing_usd == 2_300_000_000
    assert metrics.evidence_summary["audited_claims"] == 14
    assert metrics.evidence_summary["high_confidence_eligible_claims"] == 14


def test_capital_structure_counts_guarantor_role_as_guarantee_linked_exposure() -> None:
    deal = Deal(
        deal_type=DealType.BOND,
        title="Parent guaranteed senior notes",
        parties=["reit-issuer", "parent-guarantor"],
        counterparty_roles={
            "issuer": ["reit-issuer"],
            "guarantor": ["parent-guarantor"],
        },
        notional_amount_usd=400_000_000,
        maturity_date=date(2031, 5, 1),
        provenance=_prov("sec:guaranteed-notes"),
    )

    metrics = CapitalStructureAnalyzer().analyze([deal], as_of=date(2026, 1, 1))

    assert metrics.debt_like_notional_usd == 400_000_000
    assert metrics.off_balance_sheet_usd == 400_000_000
    assert metrics.guarantee_linked_deal_count == 1
    assert metrics.guarantee_linked_usd == 400_000_000
    assert metrics.spv_or_non_recourse_deal_count == 0
    assert metrics.spv_or_non_recourse_usd == 0
    assert metrics.downside_bearers[0].entity_ref == "parent-guarantor"


def test_capital_structure_surfaces_high_notional_pending_review_candidates() -> None:
    deal = Deal(
        deal_type=DealType.DEBT_FACILITY,
        title="Deterministic extraction candidate facility",
        parties=["issuer", "lenders"],
        counterparty_roles={"borrower": ["issuer"], "lender": ["lenders"]},
        notional_amount_usd=75_000_000_000,
        maturity_date=date(2028, 12, 15),
        key_terms={
            "requires_human_review": True,
            "extraction_method": "deterministic_edgar_agreement_v1",
        },
        provenance=_prov("sec:outlier-facility", status=HumanReviewStatus.PENDING),
    )

    metrics = CapitalStructureAnalyzer().analyze([deal], as_of=date(2026, 1, 1))

    assert metrics.debt_like_notional_usd == 75_000_000_000
    assert metrics.reviewed_debt_like_notional_usd == 0
    assert metrics.pending_review_debt_like_notional_usd == 75_000_000_000
    assert metrics.notional_review_required_deal_count == 1
    assert metrics.notional_review_required_usd == 75_000_000_000
    assert metrics.notional_review_required_distinct_deal_count == 1
    assert metrics.notional_review_required_distinct_usd == 75_000_000_000
    assert metrics.top_notional_review_items[0].source_uri == "sec:outlier-facility"
    assert metrics.top_notional_review_distinct_items[0].source_uri == "sec:outlier-facility"
    assert metrics.top_notional_review_items[0].reasons == [
        "adjudication_status:pending",
        "notional_usd_above_25,000,000,000_threshold",
        "source_extraction_marked_requires_llm_adjudication",
        "deterministic_sec_extraction_candidate",
    ]


def test_capital_structure_dedupes_repeated_aggregate_obligation_candidates() -> None:
    def aggregate_deal(accession: str, source_uri: str) -> Deal:
        return Deal(
            deal_type=DealType.DEBT_FACILITY,
            title="Repeated aggregate lease obligation disclosure",
            parties=["hyperscaler"],
            counterparty_roles={"borrower": ["hyperscaler"]},
            notional_amount_usd=75_600_000_000,
            key_terms={
                "accession_number": accession,
                "notional_context_kind": "aggregate_lease_obligation",
                "requires_human_review": True,
                "extraction_method": "deterministic_edgar_agreement_v1",
            },
            provenance=_prov(source_uri, status=HumanReviewStatus.PENDING),
        )

    metrics = CapitalStructureAnalyzer().analyze(
        [
            aggregate_deal("0000000000-26-000001", "sec:prospectus-a"),
            aggregate_deal("0000000000-26-000002", "sec:prospectus-b"),
        ],
        as_of=date(2026, 1, 1),
    )

    assert metrics.debt_like_notional_usd == 151_200_000_000
    assert metrics.distinct_debt_like_notional_usd == 75_600_000_000
    assert metrics.duplicate_candidate_deal_count == 1
    assert metrics.duplicate_candidate_notional_usd == 75_600_000_000
    assert metrics.aggregate_obligation_deal_count == 2
    assert metrics.aggregate_obligation_notional_usd == 151_200_000_000
    assert metrics.aggregate_obligation_distinct_deal_count == 1
    assert metrics.aggregate_obligation_distinct_notional_usd == 75_600_000_000
    assert metrics.notional_review_required_deal_count == 2
    assert metrics.notional_review_required_usd == 151_200_000_000
    assert metrics.notional_review_required_distinct_deal_count == 1
    assert metrics.notional_review_required_distinct_usd == 75_600_000_000
    assert len(metrics.top_notional_review_items) == 2
    assert len(metrics.top_notional_review_distinct_items) == 1
    assert metrics.top_duplicate_candidate_groups[0].duplicate_deal_count == 1


def test_capital_structure_identifies_downside_bearers() -> None:
    metrics = CapitalStructureAnalyzer().analyze(_deals(), as_of=date(2026, 1, 1))
    bearers = {item.entity_ref: item for item in metrics.downside_bearers}

    assert "apollo-credit" in bearers
    assert "athene-wrapper" in bearers
    assert "insurance-general-account" in bearers
    assert bearers["athene-wrapper"].exposure_usd == 750_000_000
    assert bearers["apollo-credit"].roles == ["lender"]


def test_capital_structure_tracks_unmapped_downside_bearer_identity_gaps() -> None:
    deal = Deal(
        source_deal_id="identity-gap-deal",
        deal_type=DealType.DEBT_FACILITY,
        title="Credit agreement with generic lender wording",
        parties=["Example Borrower Inc.", "lenders party thereto"],
        counterparty_roles={
            "borrower": ["Example Borrower Inc."],
            "lender": ["lenders party thereto"],
            "financier": ["JPMorgan Chase Bank, N.A.", "N.A."],
        },
        notional_amount_usd=300_000_000,
        maturity_date=date(2028, 12, 31),
        provenance=_prov("sec:identity-gap"),
    )

    metrics = CapitalStructureAnalyzer().analyze([deal], as_of=date(2026, 1, 1))

    assert [bearer.entity_ref for bearer in metrics.downside_bearers] == [
        "JPMorgan Chase Bank, N.A."
    ]
    assert metrics.downside_bearers[0].exposure_usd == 100_000_000
    assert metrics.unmapped_downside_bearer_deal_count == 1
    assert metrics.unmapped_downside_bearer_mention_count == 2
    assert metrics.unmapped_downside_bearer_usd == 200_000_000
    assert metrics.claim_audits[-1]["value"]["unmapped_downside_bearer_mention_count"] == 2


def test_capital_structure_consolidates_downside_bearer_name_variants() -> None:
    deals = [
        Deal(
            source_deal_id="case-variant-a",
            deal_type=DealType.DEBT_FACILITY,
            title="Credit agreement A",
            parties=["Borrower A", "JPMorgan Chase Bank, N.A."],
            counterparty_roles={"financier": ["JPMorgan Chase Bank, N.A."]},
            notional_amount_usd=100_000_000,
            provenance=_prov("sec:case-variant-a"),
        ),
        Deal(
            source_deal_id="case-variant-b",
            deal_type=DealType.DEBT_FACILITY,
            title="Credit agreement B",
            parties=["Borrower B", "JPMORGAN CHASE BANK, N.A."],
            counterparty_roles={"lender": ["JPMORGAN CHASE BANK, N.A."]},
            notional_amount_usd=200_000_000,
            provenance=_prov("sec:case-variant-b"),
        ),
    ]

    metrics = CapitalStructureAnalyzer().analyze(deals, as_of=date(2026, 1, 1))

    assert len(metrics.downside_bearers) == 1
    assert metrics.downside_bearers[0].entity_ref == "JPMorgan Chase Bank, N.A."
    assert metrics.downside_bearers[0].exposure_usd == 300_000_000
    assert metrics.downside_bearers[0].roles == ["financier", "lender"]


def test_capital_structure_with_no_deals_is_evidence_blocked() -> None:
    metrics = CapitalStructureAnalyzer().analyze([], as_of=date(2026, 1, 1))

    assert metrics.deal_count == 0
    assert metrics.debt_like_notional_usd == 0
    assert metrics.evidence_summary["unsupported_claims"] == 14
    assert metrics.evidence_summary["high_confidence_eligible_claims"] == 0
