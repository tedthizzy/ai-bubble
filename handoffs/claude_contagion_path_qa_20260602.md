# Contagion-Path QA — 2026-06-02 (lane 8)

- **From:** Claude (worker) · **For:** Codex · **Branch:** `claude/report-qa`
- Read-only analysis of `data/reports/contract_contagion_paths.csv` (**8,749 paths**).
- **Impact: triage-ranking + contagion-conclusion validity** (the contagion layer is pending adjudication — NOT final metric support).

## Findings

**1. Self-loop paths (~1,183, 13.5%) — entity → its OWN tranche/exhibit label, not a distinct counterparty.**
The path builder treats `"<ENTITY> - 424B5 - Notes"` / `"<ENTITY> - SEC exhibit …"` / `"… - Principal tranche"` as a
*counterparty node*, so an entity's own tranches become "contagion counterparties." These are **degenerate** — no
inter-party risk transfer — and inflate the path count. Examples (verbatim):
- `PFIZER INC` → `PFIZER INC - 424B5 - Notes` (`OBLIGOR_TO_TRANCHE`, ownership_expanded)
- `DIGITAL REALTY TRUST, INC.` → `DIGITAL REALTY TRUST, INC.` (24×)
- `GEORGIA POWER CO` → `GEORGIA POWER CO - 424B5` (`OBLIGATED_UNDER_…`)
Split: **1,136 `ownership_expanded`**, **47 `contract_only`**. (Same exhibit-label-naming root cause as findings A/B.)

**2. Duplicate paths (~1,991, 22%) — same `(start_entity, counterparty, relationship_type)` repeated**, not deduped by
deal/tranche. **Heavily overlaps #1** (the same self-loop repeated N times). Top clusters: Digital Realty 24×, Akamai 18×,
Georgia Power 9× (each pointing at its own tranche label).

**3. path_type mix:** 1,976 `ownership_expanded`, 6,773 `contract_only`. **0 exact self-joins** (start==counterparty exact) — improved from the earlier baseline.

## Root cause
Tranche/exhibit-label entity naming — `contract_contagion_paths` builds counterparty nodes from labels like
`"<ENTITY> - <FORM> - Notes"`, so an issuer's own tranches look like external counterparties.

## Proposed fix (`src/bubble/analysis/contract_contagion_paths.py`) — observations vs fixes separated
- (a) **normalize counterparty names**: strip ` - <FORM>` / ` - SEC exhibit …` / ` - Notes` / ` - Principal tranche` suffixes before joining.
- (b) **drop self-loops**: where `normalized(counterparty) == normalized(start_entity)`.
- (c) **dedupe** paths by `(norm_entity, norm_counterparty, relationship_type, deal_id|content_hash)`.
- **Effect:** removes ~1,183 self-loops + ~1,991 duplicates (with overlap) → contagion layer drops from 8,749 toward
  ~5k *real inter-party* paths, sharpening any contagion conclusion.

## Proposed regression-test names
`test_contagion_drops_entity_to_own_tranche_self_loop`, `test_contagion_dedupes_repeated_entity_counterparty_paths`,
`test_contagion_counterparty_name_normalized_strips_form_suffix`.

## Verification
```python
import csv, re
rows=list(csv.DictReader(open("data/reports/contract_contagion_paths.csv")))
norm=lambda s: re.sub(r'[^a-z0-9]','',(s or '').lower())
sub=lambda a,b:(norm(a) in norm(b) or norm(b) in norm(a)) and norm(a)!=norm(b) and norm(a)
print(sum(1 for r in rows if sub(r['start_entity_name'],r['contract_counterparty_name'])))  # ~1183
```
