"""Dated valuation inputs, with source receipts bundled beside the module."""

from __future__ import annotations

import json
from pathlib import Path

from bubble.expectations.inversion import NameInputs

SOURCE_PATH = Path(__file__).with_name("inputs_2026-10-17.json")
INPUT_RECORD = json.loads(SOURCE_PATH.read_text())
AS_OF: str = INPUT_RECORD["as_of"]
NAMES: list[NameInputs] = [NameInputs(**row) for row in INPUT_RECORD["inputs"]]
