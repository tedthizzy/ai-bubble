"""Carded inputs for the four inverted names (WS1.1).

EV / net-debt / market figures are financial_press tier (stockanalysis.com aggregator, as of
the 2026-06-12 close, post-quarter financings already folded in). Revenue / backlog / tenor /
capacity are company_filing_or_release tier (earnings releases and call transcripts). Every
field's source is in `sources`. Re-card on each earnings cycle; the inversion is only as fresh
as these numbers, so the script stamps the as-of date into the output.

NOTE on `current_annualized_revenue`: the basis differs per name and is stated explicitly,
because these are mid-ramp businesses where one definition flatters and another buries. The
revenue-multiple band's direction of sensitivity to that choice is noted per name in `notes`.
"""

from __future__ import annotations

from bubble.expectations.inversion import NameInputs

AS_OF = "2026-06-12"

NAMES: list[NameInputs] = [
    NameInputs(
        ticker="CRWV",
        name="CoreWeave",
        ev_usd_b=87.74,
        current_annualized_revenue_usd_b=12.5,
        revenue_basis="FY2026 company revenue guidance midpoint ($12-13B); Q1-2026 run-rate "
        "~$8.3B (Q1 $2.078B x4). Using the midpoint UNDERSTATES the multiple vs the trailing "
        "run-rate; on the Q1 run-rate the implied multiples rise ~50%.",
        backlog_usd_b=99.4,
        backlog_tenor_years=4.0,
        backlog_basis="$99.4B RPO backlog; company says 75% expected recognized within 4 years "
        "-> 4yr tenor used. Counterparties: OpenAI, Microsoft, Meta ($21B), IBM, Anthropic, "
        "Jane Street; 10 customers >= $1B each.",
        net_debt_usd_b=32.88,
        is_landlord=False,
        notes="GPU cloud. $35.15B debt (post-quarter DDTL 4.0 + converts) inside a $87.7B EV. "
        "Backlog is the entire bull case: large, take-or-pay-weighted, but concentrated "
        "(OpenAI is the fragile demand leg).",
        sources={
            "ev_financials": "https://stockanalysis.com/stocks/crwv/statistics/",
            "revenue_backlog_capacity": "https://www.theglobeandmail.com/investing/markets/"
            "stocks/CRWV/pressreleases/1808417/",
        },
    ),
    NameInputs(
        ticker="NBIS",
        name="Nebius",
        ev_usd_b=59.71,
        current_annualized_revenue_usd_b=1.9,
        revenue_basis="Nebius AI ARR run-rate $1.9B (Q1-2026). FY2026 guide is $3.0-3.4B and "
        "exit ARR $7-9B; using the current ARR OVERSTATES the multiple vs the forward guide "
        "(on $3.2B the multiples roughly halve).",
        backlog_usd_b=12.0,
        backlog_tenor_years=5.0,
        backlog_basis="Meta 5yr capacity contract: ~$12B dedicated/committed (the headline $27B "
        "includes a $15B OPTION, excluded as non-committed). Plus a Microsoft contract not "
        "separately dollar-disclosed.",
        net_debt_usd_b=-0.22,
        is_landlord=False,
        notes="Cleanest balance sheet of the four (essentially net cash). Q1 GAAP net income is "
        "inflated by a noncash ClickHouse mark -- ignored. Backlog is the most conservatively "
        "carded (committed only).",
        sources={
            "ev_financials": "https://stockanalysis.com/stocks/nbis/statistics/",
            "revenue_backlog_capacity": "https://www.fool.com/earnings/call-transcripts/2026/"
            "05/13/nebius-nbis-q1-2026-earnings-transcript/",
        },
    ),
    NameInputs(
        ticker="IREN",
        name="IREN",
        ev_usd_b=23.43,
        current_annualized_revenue_usd_b=3.1,
        revenue_basis="Contracted AI-cloud ARR $3.1B used as the forward run-rate. Reported "
        "revenue is FALLING ($144.8M fiscal Q3, from $184.7M) as legacy Bitcoin mining winds "
        "down faster than AI cloud ramps, so a trailing-quarter annualization (~$0.58B) would "
        "badly misstate the forward business -- contracted ARR is the honest basis.",
        backlog_usd_b=13.1,
        backlog_tenor_years=5.0,
        backlog_basis="Total contract value: Microsoft $9.7B (5yr, GB300 at Childress) + NVIDIA "
        "$3.4B (5yr AI cloud). Microsoft $1.9B + NVIDIA $0.7B + Prince George $0.5B = $3.1B "
        "contracted ARR.",
        net_debt_usd_b=0.0,
        is_landlord=False,
        notes="GPU cloud mid-transition from Bitcoin. ~$3.7-3.96B converts; net-debt sign is "
        "ambiguous across sources (modest net cash to mild net debt). NVIDIA warrant (30M @ $70) "
        "is dilution overhang. The revenue series is the trap -- do not annualize the falling "
        "reported quarter. FILING FLAG (2026-06-13, 10-Q): IREN's GAAP RPO is only $710.3M as of "
        "2026-03-31, vs the ~$13.1B total-contract-value basis used here -- so the FIRM contracted "
        "backlog is a small fraction of the headline, and IREN's renewal-dependent share is "
        "UNDERSTATED. On a $0.71B RPO basis it would be ~99%. See analysis/filing_verifications.md.",
        sources={
            "ev_financials": "https://stockanalysis.com/stocks/iren/statistics/",
            "revenue_backlog_capacity": "https://iren.gcs-web.com/news-releases/"
            "news-release-details/iren-secures-97bn-ai-cloud-contract-microsoft",
        },
    ),
    NameInputs(
        ticker="APLD",
        name="Applied Digital",
        ev_usd_b=13.30,
        current_annualized_revenue_usd_b=0.51,
        revenue_basis="Fiscal Q3-2026 revenue $126.6M annualized (x4 = $0.51B). A landlord "
        "ramping capacity; lease revenue steps up as buildings deliver.",
        backlog_usd_b=16.0,
        backlog_tenor_years=12.0,
        backlog_basis="~$16B contracted LEASE revenue (take-or-pay rent), not cloud revenue: "
        "CoreWeave ~$11B (ELN-02/03 leases) + an IG hyperscaler ~$5B. Build-to-suit DC leases "
        "are long-dated; 12yr tenor assumed -- HIGH sensitivity, a shorter tenor raises renewal "
        "dependence materially.",
        net_debt_usd_b=1.10,
        is_landlord=True,
        notes="Different model: a data-center LANDLORD. Long leases mean the contracted backlog "
        "covers more of its (smaller) EV -> lower renewal dependence than the GPU clouds. BUT "
        "~$11B of the $16B backlog is CoreWeave, so CRWV counterparty risk is embedded here -- "
        "a neocloud leasing from a landlord whose backlog is another neocloud (recursion).",
        sources={
            "ev_financials": "https://stockanalysis.com/stocks/apld/statistics/",
            "revenue_backlog_capacity": "https://www.stocktitan.net/news/APLD/"
            "applied-digital-reports-fiscal-third-quarter-2026-29zuud06n6m3.html",
        },
    ),
]
