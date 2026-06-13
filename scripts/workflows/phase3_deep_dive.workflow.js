// Phase 3 — deep-agent forensic profile + adversarial verify, per flagged target.
//
// READY TO RUN, not auto-run. Invoke via the Workflow tool:
//   Workflow({ scriptPath: "scripts/workflows/phase3_deep_dive.workflow.js",
//              args: <the `targets` array from analysis/phase3_targets.json> })
// The orchestrator passes the targets (workflow scripts have no filesystem access),
// and handles any EDGAR confirmation LOCALLY afterward (agents must NOT fetch sec.gov).
//
// Pattern: pipeline(profile -> adversarial-verify) so each target's skeptic runs the
// moment its profile lands — canaries (which sort first) clear before the beams finish.

export const meta = {
  name: 'phase3-deep-dive',
  description: 'Per-target forensic profile + adversarial refutation for the flagged fragility set',
  phases: [
    { title: 'Profile', detail: 'one agent per target assembles the forensic profile (web research, no sec.gov)' },
    { title: 'Verify', detail: 'an adversarial skeptic tries to refute each distress thesis' },
  ],
}

const targets = Array.isArray(args) ? args : (args && args.targets) || []
if (!targets.length) {
  log('Phase 3: no targets passed via args — pass the `targets` array from analysis/phase3_targets.json')
  return []
}
log(`Phase 3 deep dive: ${targets.length} flagged targets (canary-first, then beams, then mid)`)

const PROFILE_SCHEMA = {
  type: 'object',
  required: ['entity', 'fragility_thesis', 'severity', 'confidence_tier', 'edgar_confirmation_needed'],
  properties: {
    entity: { type: 'string' },
    business: { type: 'string', description: 'what it actually does, in one line' },
    capital_structure: { type: 'string', description: 'debt stack, coupons, maturities, seniority — as known' },
    solvency_read: { type: 'string', description: 'coverage / leverage / liquidity / runway' },
    distress_indicators: { type: 'array', items: { type: 'string' }, description: 'covenant amendments, downgrades, insider selling, going-concern, layoffs, missed payments, equity collapse' },
    counterparty_concentration: { type: 'string' },
    fragility_thesis: { type: 'string', description: 'the specific way this entity is mispriced/fragile, or why it is NOT' },
    fails_first_mechanism: { type: 'string', description: 'if a canary: what trips it and when' },
    severity: { type: 'string', enum: ['none', 'low', 'moderate', 'high', 'already-distressed'] },
    confidence_tier: { type: 'string', enum: ['filing_verified', 'source_backed', 'press_reported', 'triangulated', 'estimate', 'rumor'] },
    edgar_confirmation_needed: { type: 'array', items: { type: 'string' }, description: 'specific filings/exhibits the orchestrator should pull locally to confirm' },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['is_real_fragility', 'refutation_attempted', 'residual_risk', 'revised_severity'],
  properties: {
    is_real_fragility: { type: 'boolean', description: 'after trying to refute, does a genuine mispricing/fragility survive?' },
    refutation_attempted: { type: 'string', description: 'the strongest counter-case (stable cash flows cover it / coupon is a one-off / already refinanced / signal is a data artifact)' },
    false_positive_reason: { type: 'string', description: 'if not real, why the scan flagged it spuriously' },
    residual_risk: { type: 'string' },
    revised_severity: { type: 'string', enum: ['none', 'low', 'moderate', 'high', 'already-distressed'] },
    confidence: { type: 'number' },
  },
}

const sigLine = (t) => Object.entries(t.signatures || {})
  .filter(([, v]) => v > 0).map(([k, v]) => `${k} ${v.toFixed(2)}`).join(', ')

const profilePrompt = (t) => `You are a forensic credit analyst. Build the fragility profile of a SINGLE entity.

ENTITY: ${t.entity}${t.ticker ? ` (ticker ${t.ticker})` : ''}${t.cik ? ` [CIK ${t.cik}]` : ''}
SECTOR (heuristic): ${t.sector}
TIER: ${t.tier}${t.tier === 'canary' ? '  ← a CANARY: small/obscure, fails first. This is the HIGHEST-priority kind of finding.' : ''}
WHAT THE ECONOMY-WIDE SCAN ALREADY FOUND (verify, don't trust blindly):
  - gross debt ~$${(t.debt_notional_usd / 1e9).toFixed(2)}B; near-term (≤2027) ~$${(t.near_term_notional_usd / 1e9).toFixed(2)}B
  - max observed coupon: ${t.max_coupon ? (t.max_coupon * 100).toFixed(1) + '%' : 'n/a'}
  - fired signatures: ${sigLine(t)}
  - seed hypotheses: ${(t.seed_hypotheses || []).join('; ') || 'none'}

RULES:
- Use web search / public knowledge. Do NOT fetch sec.gov directly — instead list exactly which SEC filings/exhibits would confirm each claim under "edgar_confirmation_needed"; the orchestrator pulls those locally.
- Frame: this is a general fragility hunt with NO sector prior. Judge THIS entity on its own cash flows vs obligations; do not assume it is fragile because it was flagged — confirm or reject.
- Tier every load-bearing claim. Distinguish gross facility size from net debt. Note if the flag looks like a data artifact (e.g., bank deposits counted as debt, a penalty-rate coupon, double-counted notional).
Return the structured profile.`

const verifyPrompt = (profile, t) => `You are an adversarial skeptic. Try to REFUTE the fragility thesis below. Default to "false positive" unless a genuine, source-grounded mispricing survives your strongest counter-case.

ENTITY: ${t.entity} (${t.sector}, tier ${t.tier})
THESIS: ${profile && profile.fragility_thesis}
SEVERITY CLAIMED: ${profile && profile.severity}
DISTRESS INDICATORS CLAIMED: ${(profile && profile.distress_indicators || []).join('; ')}

Attack it: are the cash flows actually adequate? Is the high coupon a one-off / penalty / mis-extraction? Already refinanced or covenant-cured? Is the leverage matched by hard assets or stable contracted revenue? Is the flagged signal a data artifact? Only if real fragility survives, say so and state the residual risk and revised severity.`

const results = await pipeline(
  targets,
  (t) => agent(profilePrompt(t), { label: `profile:${t.entity.slice(0, 28)}`, phase: 'Profile', schema: PROFILE_SCHEMA }),
  (profile, t) => agent(verifyPrompt(profile, t), { label: `verify:${t.entity.slice(0, 28)}`, phase: 'Verify', schema: VERDICT_SCHEMA })
    .then((verdict) => ({ entity: t.entity, sector: t.sector, tier: t.tier, ai_tagged: t.ai_tagged, profile, verdict })),
)

const clean = results.filter(Boolean)
const confirmed = clean.filter((r) => r.verdict && r.verdict.is_real_fragility)
log(`Phase 3 complete: ${clean.length} profiled, ${confirmed.length} survived adversarial verification`)
return { profiled: clean.length, confirmed: confirmed.length, results: clean }
