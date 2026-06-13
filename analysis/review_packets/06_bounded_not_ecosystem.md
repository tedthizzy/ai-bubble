# Review packet 06_bounded_not_ecosystem

**Claim.** The leveraged cluster stays ~4.3% of the classified AI-infra universe even at the ~2x capture-recapture true size — bounded, not ecosystem-wide; the ecosystem verdict is held at 0.25 by design.

**Evidence tier.** source_backed; the 0.25 cap is a deliberate evidence-gate floor

**Where the figure comes from.** viz/graph_data.json meta.{cluster_share_pct, ecosystem_confidence}; data/published/BURRY_REPORT_...json burry_separation_test

**Reproduce it.**
```bash
python -c "import json;m=json.load(open('viz/graph_data.json'))['meta'];print('cluster share', m['cluster_share_pct'],'%; ecosystem conf', m['ecosystem_confidence'])"
```

**Your job as reviewer.** Is the cluster boundary drawn too tightly (excluding genuinely leveraged names) or too loosely? Does capture-recapture's unobserved-fraction bound hold? This claim is what keeps the verdict SCOPED — attack the scoping.

**Verdict (reviewer fills in):** ☐ stands · ☐ stands with caveats · ☐ does not stand

Notes:
