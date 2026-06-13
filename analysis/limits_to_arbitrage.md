# Limits to arbitrage — why this mispricing can persist

**2026-06-12.** Companion to [expectations_vs_measured.md](expectations_vs_measured.md). If cluster primary credit really prices essentially none of the measured fragility, the obvious objection is: *why hasn't anyone arbitraged it closed?* This note answers that by walking every available expression of the thesis and showing that each one is degraded — which is not a footnote but a finding: the asymmetry of access is itself part of why the divergence exists. This began life as a private note about instruments; it is published because the analysis is stronger as evidence than as a secret, and because this project holds no position to protect.

**Disclosure: the author holds no position, long or short, in any issuer named in this repository, and no AI-credit-adjacent paper. If that ever changes, it will be disclosed here first.** Nothing in this document is investment advice.

## The structural problem

The mispriced surface (per the expectations map) is **cluster primary credit and its funding chain** — not cluster equity, which has partially converged. A correcting trade would need (a) convex payoff to a 2026–2027 funding-window crack, (b) carry survivable while early, (c) accessibility to anyone outside a dealer relationship. No instrument has all three:

| expression | thesis fit | convexity | carry/bleed | feasibility | verdict |
|---|---|---|---|---|---|
| Short cluster bonds (e.g. the 9.75% '31s) | direct | moderate | **terrible** — pay the coupon plus borrow fee | borrow scarce, institutional only | no |
| Single-name CDS on cluster issuers | direct | high | low | **does not exist** at retail; thin even institutionally | no |
| Long-dated OTM puts on the listed flagship | indirect (equity → ~0 in a credit event) | high | defined but expensive — the −47%/high-short-interest regime keeps vol bid | listed | the classic shape, but squeeze-taxed and IV-taxed |
| Puts on weaker listed cluster names | direct-ish | high | thin chains, wide spreads | partial | situational |
| Short/puts on the listed BDC funding chain | funding-chain | **low by now** | moderate | easy | late — the worst discount is already ~41% to NAV; that move happened |
| Puts on listed private-credit managers | second-order | moderate | moderate | easy | diluted by non-AI businesses |
| Broad HY index puts | systemic | low | low | easy | wrong instrument — the index barely holds the tail (HY OAS ~2.8%) |
| Hold no AI-credit-adjacent paper | avoidance | n/a | zero | total | always available; the zero-cost expression |

## Why this is evidence, not inconvenience

The cleanly mispriced asset — private cluster credit held in BDCs, private funds, and insurance accounts — has **no liquid public short**. Its holders are buy-and-hold vehicles with quarterly marks and redemption gates; its skeptics have no instrument. That is the textbook limits-to-arbitrage condition (Shleifer–Vishny): a mispricing persists when the agents who see it cannot express it at survivable cost. The expressions that *do* exist either pay punitive carry while early (bond shorts), price the tail already (long-dated equity vol), or arrive after the move (listed BDC discounts). The carry math punishes earliness in every cell of that table — and "early" is exactly what the pre-registered signals say this is (S1 still contra at the latest print).

The corollary cuts both ways and is worth stating plainly: **the same access asymmetry that lets the mispricing persist also means its eventual correction is unlikely to be gradual.** There is no continuous short base grinding spreads wider; repricing, if it comes, comes through the primary market refusing a deal — which is why S1b (a failed print) is registered as a discrete event signal rather than a drift threshold.

## Pre-mortem — six ways transmission never reaches a tradeable instrument

Even if every measurement in this repository is right, the thesis can fail to pay any expression:

1. **Squeeze regime:** the listed flagship carries 9–16% short interest with index-inclusion flows; equity can double before it zeroes.
2. **Backstop absorption:** an anchor counterparty cures or acquires; the credit event never reaches the instruments. (The bull case's strongest leg.)
3. **Refi-forward reflexivity:** the window stays open into 2027+, negative carry notwithstanding; the wall gets refinanced before it matters.
4. **Vol already prices the tail:** entry IV on long-dated puts may embed most of the asymmetry before any position exists.
5. **Wrong layer cracks:** funding-chain stress resolves via dividend cuts and gating (already happening) without ever gapping new-issue spreads — thesis "right," no tradeable transmission.
6. **Attention failure:** the dial automates the measurement, but adjudication is human; an unmonitored signal pays nothing.

## Bottom line

Expression quality for this thesis is **mediocre**, and that fact does analytical work: it explains why the gap between measured fragility and priced belief can persist (no agent can profitably close it), and it predicts that convergence, if it comes, arrives discontinuously through the primary market rather than gradually through spreads — which is why S1b is registered as an event signal. For this project the conclusion is not "which instrument" at all. The engine's output is a calibrated, pre-registered verdict — a decision-grade model of reality — and this note is one of its inputs: a measured reason the market's price can stay wrong about the fragility the filings document. It is published like everything else here, because the project is open and the analysis is stronger as evidence than as a secret.
