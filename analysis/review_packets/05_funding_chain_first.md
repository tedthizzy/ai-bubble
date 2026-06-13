# Review packet 05_funding_chain_first

**Claim.** The first transmission channel is the semi-liquid-fund redemption gate, and it is already binding in 2026 (Apollo ~45% fill, Ares 43.1%, Blue Owl OTIC 40.7% requested, BCRED's first gate) — corroborating the funding-chain-first read.

**Evidence tier.** press_reported (named vehicle gate events, multi-source verified)

**Where the figure comes from.** analysis/marginal_buyer_constraints.{md,json} (4_semiliquid_gates.gates_actually_hit_2026)

**Reproduce it.**
```bash
python -c "import json;print(json.load(open('analysis/marginal_buyer_constraints.json'))['constraints']['4_semiliquid_gates']['gates_actually_hit_2026'])"
```

**Your job as reviewer.** Are these gates AI-credit-specific or broad private-credit risk-off? The fill-% inferences (BCRED Q2, Blue Owl per-fund) are arithmetic, not printed — verify against the primary filings. Does the manager-coupling claim (~12:1) hold?

**Verdict (reviewer fills in):** ☐ stands · ☐ stands with caveats · ☐ does not stand

Notes:
