import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "check_direct_tier_debt_card_alignment.py"
)
SPEC = importlib.util.spec_from_file_location("check_direct_tier_debt_card_alignment", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load direct-tier debt card alignment checker")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

DirectTierAlignment = MODULE.DirectTierAlignment
build_alignment_rows = MODULE.build_alignment_rows
_canonical_decision_entity = MODULE._canonical_decision_entity


class _Decision:
    metric_use_status = "approved_for_metric_use"
    supported_amount_usd = 0.0

    def __init__(self, entity: str, amount: float) -> None:
        self.entity = entity
        self.supported_amount_usd = amount


def test_direct_tier_alignment_flags_metric_above_carded_facilities(monkeypatch) -> None:
    decisions = [
        _Decision("IREN Ltd", 12_000_000_000),
        _Decision("IREN Ltd", 3_000_000_000),
    ]
    monkeypatch.setattr(MODULE, "_final_metric_representative_decisions", lambda rows: rows)

    rows = build_alignment_rows(
        decisions,  # type: ignore[arg-type]
        {"IREN": (9_000_000_000, 4_000_000_000, 5_000_000_000)},
    )

    assert rows == [
        DirectTierAlignment(
            entity="IREN",
            survivor_count=2,
            current_metric_usd=15_000_000_000,
            all_carded_facility_usd=9_000_000_000,
            primary_verified_carded_usd=4_000_000_000,
            unverified_carded_usd=5_000_000_000,
            metric_less_all_carded_usd=6_000_000_000,
            metric_less_primary_verified_usd=11_000_000_000,
            status="review_metric_exceeds_carded_facilities",
        )
    ]


def test_direct_tier_alignment_excludes_marathon_petroleum() -> None:
    assert _canonical_decision_entity("MARA Holdings, Inc.") == "MARA Holdings"
    assert _canonical_decision_entity("Marathon Petroleum Corp") == ""
