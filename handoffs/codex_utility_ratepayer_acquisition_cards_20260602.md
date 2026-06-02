# Utility/ratepayer acquisition cards — 2026-06-02

**Base:** main `a0b7eca`. **Impact:** acquisition scope + downside-bearer
confidence. These cards turn the imported utility/ratepayer downside design pack
into exact source targets for the next acquisition pass. They are not metric
changes and do not assert quantified ratepayer exposure yet.

## Why This Matters

The current report can identify regulated utilities as financing nodes, but the
ultimate downside channel is still weak: rate-base recovery, large-load tariffs,
and stranded-cost protection sit in state PUC/IRP/rate-case records, not in SEC
debt tables. These targets are the first source-backed queue for proving or
disproving whether AI/data-center power infrastructure costs are insulated from
ordinary customers.

## Verified Acquisition Targets

| Utility family | Target | Why it belongs in acquisition |
|---|---|---|
| Southern / Georgia Power | Georgia PSC Docket `56002`, Georgia Power 2025 IRP | Official IRP and Georgia Power page identify Docket 56002 and load-growth planning. The IRP states Georgia Power tracks large-load customers and forecasts 8,200 MW of winter load growth through 2030/2031, with nearly 6,000 MW as early as winter 2028/2029. Extract load-growth, transmission, certification, cost-allocation, and large-load reporting fields. |
| Entergy Louisiana | LPSC Docket `U-37425`, Meta/Laidley Richland Parish project | LPSC order text ties Entergy Louisiana infrastructure to significant new load from a Meta/Laidley data center in Richland Parish. Entergy's own release says LPSC approved major infrastructure investments tied to Meta's data center. Extract customer-protection, cost-of-service, transmission/generation, and stranded-cost terms. |
| FPL / NextEra | FPSC Docket `20250011-EI`, FPL rate case / LLCS tariff | FPSC filings identify the rate case and large-load tariff terms. Testimony warns that customers can subsidize generation for large loads if not insulated; order text identifies FEIA data-center customers and the proposed Large Load Contract Service tariff. Extract threshold MW, take-or-pay, incremental generation charge, exit-fee, and separate-rate-class terms. |
| Xcel Colorado | Colorado PUC Proceeding `26AL-0137E`, Public Service Company of Colorado large-load tariff | Colorado PUC newsletter identifies Xcel's proceeding for high-demand projects such as data centers. Xcel's release says the proposal is intended to prevent existing customers from subsidizing new large-load infrastructure. Extract contract length, dedicated-upgrade cost recovery, interconnection, generation-capacity, and stranded-cost guardrails. |
| Xcel Minnesota | MPUC Docket `E022/M-25-289`, Xcel very-large-customer tariff | Minnesota PUC agenda identifies Xcel's tariff proceeding and issues including the 100 MW threshold, ESA term length, minimum billing demand, exit fee, and separate customer class. Extract final order, tariff sheets, class-cost allocation, clean-energy/capacity tariff directives, and data-center ESA requirements. |
| NextEra / NEER | NextEra-Google strategic development release | Company IR source identifies multiple GW-scale data-center campuses with supporting generation and capacity resources. Use as a non-PUC source target for merchant PPA / generation-development exposure, then link to PUC/IRP records where the actual campuses are jurisdictionally filed. |

## Machine-Readable Artifacts

- `handoffs/fixtures/utility_ratepayer_acquisition_targets_20260602.csv`:
  card-level extraction targets with regulator, docket, verified signal,
  expected fields, and priority.
- `handoffs/fixtures/source_catalog_utility_ratepayer_20260602.csv`:
  appendable source-catalog rows validated against `load_source_catalog()`.

## Verified vs Proposed

- **Verified:** source URIs exist; the named docket/proceeding IDs and filing
  classes above are source-backed by regulator or company materials; the sources
  contain explicit large-load/data-center/ratepayer-protection signals.
- **Proposed:** final ratepayer exposure amounts, stranded-cost allocation, and
  customer-protection sufficiency. Those require acquisition + extraction from
  the docket record, tariff sheets, settlement/order text, and IRP testimony.

## Extraction Fields To Add Downstream

`utility_family`, `regulated_opco`, `jurisdiction`, `regulator`,
`docket_id`, `filing_date`, `customer_or_load_driver`, `load_mw`,
`generation_or_transmission_capex_usd`, `tariff_threshold_mw`,
`minimum_contract_term_years`, `take_or_pay_pct`, `exit_fee_terms`,
`incremental_generation_charge`, `rate_base_recovery_mechanism`,
`cost_allocation_terms`, `ratepayer_protection_terms`,
`stranded_cost_language`, `source_uri`, `source_quote`.

