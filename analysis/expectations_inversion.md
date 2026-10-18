# Expectations inversion

Reviewed through 2026-10-17. Enterprise values use the October 16 market close. Revenue and contract balances retain their stated observation dates.

The model uses discount rates 10%, 12%, 15%, hypothetical FCF margins 15%, 25%, 35%, and 4% perpetual growth for the implied revenue multiple. The math and scenario grid are unchanged. Revenue bases now use reported consolidated trailing 12 months for all four issuers.

The original June inputs remain in git and the retained refresh snapshot. The current card file is src/bubble/expectations/inputs_2026-10-17.json. It records source hashes, the exact prior-year revenue periods and the market quote comparison. scripts/review_expectations_inputs.py verifies retained source bytes before re-carding. scripts/build_expectations_inversion.py regenerates this report and viz/expectations.json.

## CRWV / CoreWeave

EV $79.89B. Provider net debt $46.03B. Reported trailing revenue $7.590000B through 2026-06-30.

Implied revenue multiple: 1.80x to 7.72x; grid median 3.37x.

Renewal-dependent share of EV: 67.7% to 88.1%; grid median 78.3%.

$103.7B unsatisfied GAAP RPO at June 30. 41% expected within 24 months, 39% in months 25-48, remainder in months 49-78. Later announced commitments are separate.

6.5-year uniform recognition assumption uses the disclosed final 78-month horizon; actual recognition is earlier-weighted. EV uses the provider's debt and cash definitions. Uniform FCF margins are model assumptions; the uncovered EV share can also depend on new customers or other businesses.

Sources: [contract_and_interim_statement](https://www.sec.gov/Archives/edgar/data/1769628/000176962826000366/crwv-20260630.htm); [market](https://stockanalysis.com/stocks/crwv/statistics/); [revenue_companyfacts](https://data.sec.gov/api/xbrl/companyfacts/CIK0001769628.json).

## NBIS / Nebius

EV $47.51B. Provider net debt $2.15B. Reported trailing revenue $1.355100B through 2026-06-30.

Implied revenue multiple: 6.01x to 25.71x; grid median 11.22x.

Renewal-dependent share of EV: 79.1% to 92.1%; grid median 85.8%.

$37.4906B unsatisfied RPO at June 30. 36% expected within 24 months, 40% in months 25-48, remainder thereafter. Includes estimated variable consideration; excludes original terms of one year or less. Broader $40B customer commitments are separate.

Five-year uniform recognition assumption; disclosed recognition is 76% within four years and the remainder thereafter. Final duration is not independently reconciled. EV uses the provider's debt and cash definitions. Uniform FCF margins are model assumptions; the uncovered EV share can also depend on new customers or other businesses.

Sources: [contract_and_interim_statement](https://www.sec.gov/Archives/edgar/data/1513845/000110465926094844/nbis-20260812xex99d2.htm); [market](https://stockanalysis.com/stocks/nbis/statistics/); [revenue_companyfacts](https://data.sec.gov/api/xbrl/companyfacts/CIK0001513845.json).

## IREN / IREN

EV $12.58B. Provider net debt $1.94B. Reported trailing revenue $0.707007B through 2026-06-30.

Implied revenue multiple: 3.05x to 13.05x; grid median 5.69x.

Renewal-dependent share of EV: 65.0% to 86.7%; grid median 76.2%.

$16.6B company-reported combined June 30 ASC 606 RPO and ASC 842 contracted lease value. Separately rounded components are $5.1B and $11.4B. This combined measure is broader than GAAP RPO.

Five-year uniform recognition assumption; the stated RPO schedule ends at month 60. The lease component is a separate accounting measure. EV uses the provider's debt and cash definitions. Uniform FCF margins are model assumptions; the uncovered EV share can also depend on new customers or other businesses.

Sources: [contract_and_interim_statement](https://www.sec.gov/Archives/edgar/data/1878848/000187884826000052/iren-20260630.htm); [market](https://stockanalysis.com/stocks/iren/statistics/); [revenue_companyfacts](https://data.sec.gov/api/xbrl/companyfacts/CIK0001878848.json).

## APLD / Applied Digital

EV $8.99B. Provider net debt $3.53B. Reported trailing revenue $0.872252B through 2026-08-31.

Implied revenue multiple: 1.77x to 7.56x; grid median 3.30x.

Renewal-dependent share of EV: 28.9% to 76.6%; grid median 54.5%.

Approximately $36B base-term contracted lease revenue disclosed October 7. Excludes the $86B total conditional on all renewal options. Gross original lease value is not GAAP RPO or an audited remaining rent balance.

15-year uniform recognition assumption follows the disclosed new lease base terms. Construction start delays and individual remaining lease schedules are not modeled. EV uses the provider's debt and cash definitions. Uniform FCF margins are model assumptions; the uncovered EV share can also depend on new customers or other businesses.

Sources: [contract_and_interim_statement](https://www.sec.gov/Archives/edgar/data/1144879/000114487926000057/apldq127earningsrelease.htm); [market](https://stockanalysis.com/stocks/apld/statistics/); [revenue_companyfacts](https://data.sec.gov/api/xbrl/companyfacts/CIK0001144879.json).

## Model limits

- The implied revenue multiple uses a Gordon-growth perpetuity with immediate steady-state cash flows. It does not model the ramp or near-term funding needs.
- Renewal-dependent share of EV is the share beyond modeled contracted cash-flow PV. New customers, expansion or other businesses can supply that value. This calculation cannot identify actual renewal dependence.
- Revenue uses consolidated reported trailing 12 months for every issuer. Contract measures differ between GAAP RPO, combined lease value and gross base-term rent. These measures are not directly interchangeable.
- Backlog is recognized uniformly over the stated assumed horizon. Construction delays, default losses and incremental capex funding are not separately modeled. The same hypothetical FCF margin grid applies to clouds and the landlord.
- EV and net debt use the market provider's definitions, including its lease treatment. They differ from the issuer borrowing and note carrying amounts in the financial review.
- These sensitivities do not measure GPU economic life, default probabilities or a calibrated bubble probability.
