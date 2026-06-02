# Physical-terms extractor test fixtures — directly for the parser Codex is building now

**Base:** main `0d85bce`. READ-ONLY; no prod writes. **Timed for Codex's active work:** he is adding a source-text
extractor producing `onsite_generation_mw`, `air_permit_id`, `queue_bypass_or_no_queue`, `permit_litigation_risk`,
`ratepayer_stranded_asset_transfer`. This pack is the **verified test data** for that extractor — I provide the
fixtures; Codex owns the parser. Mirrors how I provided parser-fix specs / ratepayer fixtures earlier.
**Deliverable:** `handoffs/fixtures/physical_terms_extractor_fixtures_20260602.csv` (14 cases: field, case_type,
source_text_snippet, expected_value, source_citation, proposed_test_name, note). Impact: **acquisition scope /
docs-QA (extractor correctness).**

## Coverage (9 positive + 5 negative across all 5 fields)
- **`onsite_generation_mw`** — POS: Stargate "5×38 MW Titan 350 + 5×34.1 MW GE LM2500 … onsite use only" → **360.5**;
  Adams Fork "off grid … 117 engines … >2,400 MW" → **2400/plant**. NEG: Entergy's grid-connected 2,260 MW CCGT with
  transmission → **null** (that's the ratepayer-transfer field, not onsite).
- **`air_permit_id`** — POS: WV DEP "R13-3714 and R13-3715"; TCEQ "Standard Permit Registration 177263 … RN112029079".
  NEG: an ERCOT GIS INR / Large-Load study handle must **not** parse as a permit.
- **`queue_bypass_or_no_queue`** — POS: "off grid … microgrid"; "sidestep PJM's interconnection queue" (HB 2014). NEG:
  "interconnection agreement executed … in-service" → **False** (real grid connection).
- **`permit_litigation_risk`** — POS: "ran gas turbines WITHOUT an air permit … Clean Air Act lawsuit" → **HIGH**;
  "federal lawsuit … challenging the air permits" → **MED-HIGH**. NEG: "routine … no comments received" → **LOW**.
- **`ratepayer_stranded_asset_transfer`** — POS: "Entergy … LPSC approval … 2,260 MW … to support Meta's data center"
  → **True** (rate-base → ratepayer). NEG: "off grid … TransGas … project-financed microgrid" → **False** (developer/
  JV equity bears it, not ratepayers).

## The key discriminators the parser must get right (negative controls)
1. **Onsite vs grid generation:** an `onsite_generation_mw` value requires a behind-the-meter / "onsite use only" /
   "off grid" marker. A utility CCGT *with transmission* is GRID gen → it populates `ratepayer_stranded_asset_transfer`,
   NOT `onsite_generation_mw`. (Adams Fork = onsite; Meta/Richland = grid/ratepayer. Don't conflate.)
2. **Permit ID vs ISO queue ID:** `air_permit_id` (R13-####, TCEQ Reg #, RN#) is categorically distinct from an ISO
   interconnection-queue ID (ERCOT INR, PJM #, MISO ERAS). The whole physical reframe is that off-grid projects have
   the former and not the latter — the parser must not cross-match.
3. **Litigation tiering:** "ran without a permit" (xAI) is HIGHER risk than "permit issued but challenged" (Adams Fork),
   which is higher than a routine uncontested permit (Stargate). Three-level, not binary.
4. **Stranded-asset bearer:** off-grid → developer/JV/lenders; grid/utility → ratepayers. The parser's
   `ratepayer_stranded_asset_transfer` must be True ONLY for utility-rate-base-recovered DC-load generation.

## Verified vs proposed
- VERIFIED: every source_text_snippet is from the cited primary sources in my physical-execution-cards research
  (TCEQ Reg 177263, WV DEP R13-3714/3715, Entergy/LPSC, Earthjustice/NAACP v. xAI) — 3-vote adversarially verified.
- PROPOSED: the expected normalized values + the 4 discriminator rules + the 14 test names. Codex owns the parser;
  these are the positive/negative fixtures + guardrails to prove it correct. Run them as `tests/ingestion/
  test_physical_terms_extractor.py`.
