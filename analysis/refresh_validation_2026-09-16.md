# Refresh validation, September 16, 2026

## Overall assessment

**Share with caveats.** The dated report is internally consistent and the highest-impact arithmetic and provenance checks pass. It does not support a complete SEC census, a measured global usable-AI-GW total, or a calibrated September bubble probability.

## Question and scope

The refresh answers whether the AI/data-center financing cycle shows bubble conditions as of September 16 Pacific, how the evidence changed since the June baseline, which companies and financing links require tracking, and whether the supplied Hot Chips 2026 transcript's claims are supported. It separates recognized demand, private financing marks, issuer cash investment, physical queue requests, listed GPU rates, and registered credit signals.

## Calculation checks

- The official Q2 and Q3 master indexes contain 367,387 raw rows, 367,371 unique CIK-accession pairs, and 257,675 unique accessions through September 15. The stored coverage JSON preserves the two index hashes and the repeated-row treatment.
- The final selected primary and exhibit URL audit requests 180,044 URLs. It finds 37,706 acquired URLs, 142,338 missing URLs, and 724 known SEC HTTP 429 errors. It reports 3,883 acquired URLs outside the selected manifests as retained extra work.
- The corrected offline parser verified 41,589 local documents and 14,477,363,465 raw bytes. It produced 27,759 deal candidates and 6,116 tranche candidates with no hash mismatch or network call. The metadata-preserving rerun matched all inventory rows to the 183,927-row union manifest (SHA-256 `b11249b9bca0c9f76aa967616b7bd85c5487539ff013b3f6e2ab1d7de5879bbf`) and retained all 27,759 deal IDs. Relative to the prior current table, it changes 2,412 maturity values and 404 confidence fields; 2,056 exhibit title changes are literal description-prefix changes. The earlier 6,975-document diagnostic independently reproduced the 478 maturity corrections.
- The dated engine v7 reads the exact coverage JSON and returns S1 contra at 180 basis points, S1b confirming, S2 confirming at +2.04 percentage points, S3 contra at +1.5 points, S4 unmeasured, and `bubble_probability: null`.
- The financial panel has 11 of 11 matched 2026 issuer observations negative after cash capex. This is a preselected capital-intensive panel, not a sector rate.
- The physical function reads 16,515 queue rows and reports 531,011.143 MW of gross generation requests; the data-center classifier covers 11,717.7 MW. Neither is energized AI load.
- The compute function reads 87 September listed GPU quotes. Forty-five June-to-September matches contain 12 increases, one decrease, and 32 unchanged observations. Listed rates contain no occupancy or transaction volume.
- The notebook verifier reproduced five saved-output cells, 558 FRED observations, six BDC prices/NAVs, and five EDGAR search hits. It also reproduces the $800 billion full-year 40 GW rental arithmetic and the $200 billion uniform second-half 2027 example.
- The final provenance audit scans 49 CSV outputs, 13,094,234 rows, and 6,864,373 source-URI values. It reports zero violations and zero warnings.
- The standard test command `PYTHONPATH=src /tmp/bubble-refresh-20260916/bin/python -m pytest -q` exits 0. The collection check reports 847 tests, and the full run reaches 100%.

## Evidence and methodology review

Primary company filings and releases support real cloud demand, large capital commitments, and negative cash-after-capex observations in the selected issuer panel. The report labels secondary revenue updates for Anthropic and OpenAI as reported run rates rather than audited revenue. It treats the Anthropic S-1 as confidential because no public prospectus was found in the reviewed SEC full-text and company newsroom checks. It keeps the Hot Chips capacity and revenue-per-GW claims as arithmetic scenarios because the transcript does not provide a reconciled installed-capacity or utilization denominator.

The report preserves the registered signal definitions. S1 uses the selected QTS coupon proxy, S1b uses original reporting of two abandoned or postponed offerings, S2 uses the CCC-minus-HY spread differential, S3 uses exposed-versus-control BDC discounts, and S4 remains unmeasured because there is no synchronized comparable company-stated basket. The report does not convert these mixed signals into a new probability.

## Material limitations

- The SEC direct-document corpus is incomplete because the SEC returned HTTP 429 responses. The Feed route proved viable on June 10 but the global 74-day run stopped at rate limiting and its pilot did not reconcile one-to-one to the dated master index.
- The September 16 daily index was not present in the saved master files, and the later direct check returned HTTP 403. The refresh therefore does not assert that no September 16 filing exists.
- Private 144A books, private-company cash flow, customer contract cancellability, facility utilization, and realized inference ROI remain unavailable in the reviewed public sources.
- The checked-in explorer graph and overlay remain June snapshots. No live-browser rendering or deployment check was performed, so the report does not call the explorer current.

The durable source and coverage details are in [the SEC acquisition status](sec_acquisition_status_2026-09-16.md), [the full refresh](FULL_REFRESH_2026-09-16.md), [the corrected parser output](../data/edgar_reextracted_current_inventory_2026-09-16_v2/offline_reextraction.summary.json), and [the dated engine JSON](dated_engine_2026-09-16_v7.json).
