"""Phase 4 prep — extract & pair the Phase-3 deep-dive findings from agent transcripts.

Reads the workflow's per-agent JSONL transcripts, pulls each structured output (profile
or adversarial verdict), pairs them per entity, and aggregates: confirmed-vs-refuted,
severity distribution, by tier/sector. Durable + reproducible (a committed artifact),
and works on a PARTIAL run (re-run as more agents finish).

Usage: uv run python scripts/extract_phase3_findings.py <workflow_transcript_dir>
Outputs: analysis/phase3_findings.{json,md}
"""

from __future__ import annotations

import glob
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "analysis" / "phase3_findings.json"
OUT_MD = ROOT / "analysis" / "phase3_findings.md"

PROFILE_KEYS = {"fragility_thesis", "severity", "confidence_tier"}
VERDICT_KEYS = {"is_real_fragility", "refutation_attempted", "revised_severity"}


def _walk_for_keys(obj, keys: set[str]):
    """Depth-first search for a dict that contains >=2 of the schema keys."""
    if isinstance(obj, dict):
        if len(keys & obj.keys()) >= 2:
            return obj
        for v in obj.values():
            hit = _walk_for_keys(v, keys)
            if hit:
                return hit
    elif isinstance(obj, list):
        for v in obj:
            hit = _walk_for_keys(v, keys)
            if hit:
                return hit
    return None


def _norm_entity(name: str) -> str:
    head = re.split(r"\s*[(\[]", name, maxsplit=1)[0]
    return re.sub(r"[^a-z0-9]+", " ", head.lower()).strip()[:40]


def parse_agent(fp: str) -> dict | None:
    raw = open(fp, errors="ignore").read()  # noqa: SIM115
    m = re.search(r"ENTITY:\s*(.+)", raw)
    entity_from_prompt = m.group(1).strip() if m else ""
    profile = verdict = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if profile is None and "fragility_thesis" in line:
            profile = _walk_for_keys(obj, PROFILE_KEYS)
        if verdict is None and "is_real_fragility" in line:
            verdict = _walk_for_keys(obj, VERDICT_KEYS)
    if not (profile or verdict):
        return None
    entity = (profile or {}).get("entity") or entity_from_prompt
    return {"entity": entity, "profile": profile, "verdict": verdict}


def main() -> None:
    wd = sys.argv[1] if len(sys.argv) > 1 else ""
    files = sorted(glob.glob(f"{wd}/agent-*.jsonl"))
    if not files:
        print(f"no agent transcripts found under {wd!r}")
        return

    paired: dict[str, dict] = defaultdict(lambda: {"profile": None, "verdict": None, "entity": ""})
    for fp in files:
        rec = parse_agent(fp)
        if not rec or not rec["entity"]:
            continue
        key = _norm_entity(rec["entity"])
        slot = paired[key]
        slot["entity"] = slot["entity"] or rec["entity"]
        if rec["profile"]:
            slot["profile"] = rec["profile"]
        if rec["verdict"]:
            slot["verdict"] = rec["verdict"]

    findings = []
    for slot in paired.values():
        p, v = slot["profile"], slot["verdict"]
        if not p and not v:
            continue
        sev = (v or {}).get("revised_severity") or (p or {}).get("severity") or "unknown"
        findings.append(
            {
                "entity": slot["entity"],
                "severity": sev,
                "is_real_fragility": (v or {}).get("is_real_fragility"),
                "confidence_tier": (p or {}).get("confidence_tier"),
                "fragility_thesis": (p or {}).get("fragility_thesis", ""),
                "false_positive_reason": (v or {}).get("false_positive_reason", ""),
                "has_profile": p is not None,
                "has_verdict": v is not None,
            }
        )

    sev_rank = {
        "already-distressed": 0,
        "high": 1,
        "moderate": 2,
        "low": 3,
        "none": 4,
        "unknown": 5,
    }
    findings.sort(key=lambda f: (sev_rank.get(f["severity"], 9), not bool(f["is_real_fragility"])))

    confirmed = [f for f in findings if f["is_real_fragility"] is True]
    refuted = [f for f in findings if f["is_real_fragility"] is False]
    out = {
        "transcript_dir": wd,
        "entities_with_findings": len(findings),
        "verdicts_in": sum(1 for f in findings if f["has_verdict"]),
        "confirmed_real": len(confirmed),
        "refuted_false_positive": len(refuted),
        "severity_distribution": dict(Counter(f["severity"] for f in findings)),
        "findings": findings,
    }
    OUT_JSON.write_text(json.dumps(out, indent=2))
    write_md(out)
    print(f"wrote {OUT_JSON.relative_to(ROOT)} + {OUT_MD.relative_to(ROOT)}")
    print(
        f"  {len(findings)} entities | confirmed {len(confirmed)} | refuted {len(refuted)} "
        f"| severities {out['severity_distribution']}"
    )


BANNER = (ROOT / "analysis" / "economy_wide_fragility_map.md").read_text().split("\n")[2]


def write_md(out: dict) -> None:
    L: list[str] = []
    L.append("# Phase 3 deep-dive findings — confirmed vs refuted")
    L.append("")
    L.append(BANNER)
    L.append("")
    L.append(
        f"Per-target forensic profile + adversarial verdict, paired from the deep-dive "
        f"fan-out. **{out['entities_with_findings']} entities** with findings "
        f"({out['verdicts_in']} adversarially verified): **{out['confirmed_real']} confirmed "
        f"real fragility**, **{out['refuted_false_positive']} refuted as false positives**. "
        f"Severity: {out['severity_distribution']}. Machine-readable: "
        f"[phase3_findings.json](phase3_findings.json)."
    )
    L.append("")
    L.append("## Confirmed real fragility (severity-ordered)")
    L.append("")
    for f in out["findings"]:
        if f["is_real_fragility"] is not True:
            continue
        L.append(f"### {f['entity']} — **{f['severity']}** ({f['confidence_tier'] or 'untiered'})")
        L.append(f["fragility_thesis"][:700] or "_(profile pending)_")
        L.append("")
    L.append("## Refuted / false positives (scan flagged, verification cleared)")
    L.append("")
    for f in out["findings"]:
        if f["is_real_fragility"] is not False:
            continue
        L.append(f"- **{f['entity']}** — {f['false_positive_reason'][:240] or 'cleared'}")
    L.append("")
    OUT_MD.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
