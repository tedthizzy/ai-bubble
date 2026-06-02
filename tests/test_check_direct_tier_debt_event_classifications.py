import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "check_direct_tier_debt_event_classifications.py"
)
SPEC = importlib.util.spec_from_file_location(
    "check_direct_tier_debt_event_classifications",
    SCRIPT_PATH,
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load direct-tier debt-event classification validator")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

validate_classifications = MODULE.validate_classifications


class _Decision:
    def __init__(self) -> None:
        self.packet_id = "adjudication:abc"
        self.supported_amount_usd = 1_000_000_000
        self.source_uri = "https://www.sec.gov/Archives/edgar/data/1/doc.htm"


def _row(**overrides: str) -> dict[str, str]:
    row = {
        "entity": "Issuer",
        "packet_id": "adjudication:abc",
        "accession": "0001",
        "amount_usd": "1000000000",
        "ai_linked": "direct/watchlist",
        "instrument_offering": "Issuer:Notes",
        "classification": "same_event",
        "expected_behavior": "repeat -> COLLAPSE to representative",
        "source_uri": "https://www.sec.gov/Archives/edgar/data/1/doc.htm",
        "quote_excerpt": "priced notes",
    }
    row.update(overrides)
    return row


def test_validate_classification_rows_against_live_decisions(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(MODULE, "load_decisions", lambda _path: [_Decision()])

    errors, summary = validate_classifications([_row()], decisions_path=tmp_path / "decisions.csv")

    assert errors == []
    assert summary["row_count"] == 1
    assert summary["by_classification"] == {"same_event": 1}
    assert summary["same_event_amount_usd"] == 1_000_000_000


def test_truncated_packet_id_is_rejected(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(MODULE, "load_decisions", lambda _path: [_Decision()])

    errors, summary = validate_classifications(
        [_row(packet_id="ion:abc")],
        decisions_path=tmp_path / "decisions.csv",
    )

    assert summary["error_count"] == 1
    assert "packet_id 'ion:abc' not found" in errors[0]


def test_negative_control_keep_behavior_is_not_counted_as_collapse(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(MODULE, "load_decisions", lambda _path: [_Decision()])

    errors, summary = validate_classifications(
        [
            _row(
                classification="distinct_facility",
                expected_behavior="KEEP -- guard MUST NOT collapse these",
            )
        ],
        decisions_path=tmp_path / "decisions.csv",
    )

    assert errors == []
    assert summary["by_expected_behavior"] == {"keep": 1}
