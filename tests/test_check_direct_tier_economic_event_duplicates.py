import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "check_direct_tier_economic_event_duplicates.py"
)
SPEC = importlib.util.spec_from_file_location(
    "check_direct_tier_economic_event_duplicates",
    SCRIPT_PATH,
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load direct-tier economic-event duplicate checker")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

build_event_clusters = MODULE.build_event_clusters


class _Decision:
    metric_use_status = "approved_for_metric_use"
    metric_aggregation_policy = "max_amount_per_source_instrument"
    metric_group_id = ""
    metric_snapshot_date = ""
    rank = 1
    source_uri = ""
    content_hashes: tuple[str, ...] = ()
    content_hash = ""
    metric_dedupe_quote = ""
    packet_reason = ""

    def __init__(
        self,
        *,
        packet_id: str,
        entity: str,
        amount: float,
        accession: str,
        quote: str,
    ) -> None:
        self.packet_id = packet_id
        self.entity = entity
        self.supported_amount_usd = amount
        self.source_uri = f"https://www.sec.gov/Archives/edgar/data/1/{accession}/doc.htm"
        self.evidence_quote = quote


def test_same_direct_tier_amount_with_single_maturity_is_review_candidate(monkeypatch) -> None:
    decisions = [
        _Decision(
            packet_id="a",
            entity="TERAWULF INC.",
            amount=3_200_000_000,
            accession="000110465925100142",
            quote="TeraWulf priced 7.750% senior secured notes due 2030.",
        ),
        _Decision(
            packet_id="b",
            entity="TERAWULF INC.",
            amount=3_200_000_000,
            accession="000110465925101866",
            quote="Indenture for 7.750% senior secured notes due 2030.",
        ),
    ]
    monkeypatch.setattr(MODULE, "_final_metric_representative_decisions", lambda rows: rows)

    rows = build_event_clusters(decisions)  # type: ignore[arg-type]

    assert len(rows) == 1
    assert rows[0].classification == "probable_same_instrument_review"
    assert rows[0].possible_duplicate_excess_usd == 3_200_000_000
    assert rows[0].years == "2030"


def test_conflicting_maturities_are_negative_controls(monkeypatch) -> None:
    decisions = [
        _Decision(
            packet_id="a",
            entity="IREN Ltd",
            amount=1_000_000_000,
            accession="000114036125037488",
            quote="private offering of notes due 2031",
        ),
        _Decision(
            packet_id="b",
            entity="IREN Ltd",
            amount=1_000_000_000,
            accession="000114036125043803",
            quote="private offering of 2033 notes and 2032 notes",
        ),
    ]
    monkeypatch.setattr(MODULE, "_final_metric_representative_decisions", lambda rows: rows)

    rows = build_event_clusters(decisions)  # type: ignore[arg-type]

    assert len(rows) == 1
    assert rows[0].classification == "distinct_facility_negative_control"
    assert rows[0].years == "2031;2032;2033"
