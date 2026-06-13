"""News-distress corroboration of the confirmed set via GDELT (free API, no agents).

Ingests the 'archived news' dimension: for each confirmed-fragile name, counts recent
distress-context news articles (bankruptcy / default / going-concern / delisting /
restructuring / layoffs) via the free GDELT DOC API. Cross-checks the filing-based
confirmations against an INDEPENDENT source — high news volume = publicly-salient distress
(corroborated); zero = low-salience obscure canary (the thing that fails quietly first).

Output: analysis/gdelt_news_distress.{json,md}
"""

from __future__ import annotations

# ruff: noqa: PERF401
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FINDINGS = ROOT / "analysis" / "phase3_findings.json"
OUT_JSON = ROOT / "analysis" / "gdelt_news_distress.json"
OUT_MD = ROOT / "analysis" / "gdelt_news_distress.md"
UA = "Mozilla/5.0 (ai-bubble research ted1508@gmail.com)"
DISTRESS = '(bankruptcy OR default OR "going concern" OR delisting OR restructuring OR layoffs OR insolvency)'


def short_name(entity: str) -> str:
    head = re.split(r"\s*[(\[]", entity, maxsplit=1)[0].strip()
    head = re.sub(
        r",?\s+(Inc|Corp|Corporation|Company|Co|Ltd|LLC|LP|Holdings|Group|plc|"
        r"Technologies|Enterprises|International)\.?$",
        "",
        head,
        flags=re.I,
    ).strip()
    return head


def gdelt_count(name: str) -> int | None:
    q = f'"{name}" {DISTRESS}'
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(
        {"query": q, "mode": "artlist", "maxrecords": 75, "format": "json", "timespan": "6months"}
    )
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read().decode("utf-8", "ignore")
            if not body.strip().startswith("{"):
                return 0
            return len(json.loads(body).get("articles", []))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(5 + attempt * 3)
                continue
            return None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(2)
    return None


def main() -> None:
    conf = [
        x for x in json.loads(FINDINGS.read_text())["findings"] if x["is_real_fragility"] is True
    ]
    # dedup by short name, keep severity
    seen: dict[str, dict] = {}
    for x in conf:
        sn = short_name(x["entity"])
        if len(sn) >= 4 and sn.lower() not in seen:
            seen[sn.lower()] = {"name": sn, "severity": x["severity"]}
    names = list(seen.values())
    print(f"querying GDELT for {len(names)} confirmed names ...")

    results = []
    for i, e in enumerate(names, 1):
        cnt = gdelt_count(e["name"])
        results.append({**e, "distress_news_6mo": cnt})
        time.sleep(1.5)
        if i % 5 == 0:  # checkpoint often — GDELT throttling makes the full sweep slow
            OUT_JSON.write_text(
                json.dumps({"partial": results, "done": i, "of": len(names)}, indent=2)
            )

    ok = [r for r in results if r["distress_news_6mo"] is not None]
    corroborated = [r for r in ok if (r["distress_news_6mo"] or 0) >= 5]
    quiet = [r for r in ok if (r["distress_news_6mo"] or 0) == 0]
    corroborated.sort(key=lambda r: -(r["distress_news_6mo"] or 0))
    out = {
        "queried": len(results),
        "with_response": len(ok),
        "news_corroborated_distress": len(corroborated),
        "low_salience_quiet": len(quiet),
        "top_corroborated": corroborated[:40],
        "quiet_canaries": [r["name"] for r in quiet][:60],
    }
    OUT_JSON.write_text(json.dumps(out, indent=2))
    write_md(out)
    print(
        f"wrote {OUT_JSON.relative_to(ROOT)} | responded {len(ok)} | "
        f"news-corroborated {len(corroborated)} | quiet {len(quiet)}"
    )


BANNER = (ROOT / "analysis" / "economy_wide_fragility_map.md").read_text().split("\n")[2]


def write_md(out: dict) -> None:
    L = []
    L.append("# News-distress corroboration of the confirmed set (GDELT, independent source)")
    L.append("")
    L.append(BANNER)
    L.append("")
    L.append(
        f"Ingests the **archived-news dimension** (free GDELT API): distress-context article "
        f"counts over 6 months for the confirmed-fragile names — an *independent* cross-check "
        f"of the filing-based confirmations. {out['with_response']}/{out['queried']} returned. "
        f"**{out['news_corroborated_distress']} are news-corroborated** (≥5 distress articles); "
        f"**{out['low_salience_quiet']} are quiet** (0 articles — the obscure canaries that "
        f"fail without headlines). Machine-readable: [gdelt_news_distress.json](gdelt_news_distress.json)."
    )
    L.append("")
    L.append("## News-corroborated distress (filing + news agree)")
    L.append("")
    L.append("| entity | severity | distress news (6mo) |")
    L.append("|---|---|---:|")
    for r in out["top_corroborated"]:
        L.append(f"| {r['name'][:34]} | {r['severity']} | {r['distress_news_6mo']} |")
    L.append("")
    L.append(
        "## Quiet canaries (confirmed distress, ~no news — the fails-first obscure tail)\n\n"
        + ", ".join(out["quiet_canaries"])
    )
    L.append("")
    L.append(
        "*GDELT entity matching is name-based and noisy; counts are a salience proxy, not a "
        "precise event tally. The value is the SPLIT: corroborated names are publicly-known "
        "distress; quiet names are the canary thesis — real fragility the market isn't watching.*"
    )
    OUT_MD.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
