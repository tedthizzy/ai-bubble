#!/usr/bin/env python
"""Politely probe whether THIS network can reach SEC EDGAR (WS2.1 enabler).

Run from any candidate egress box before wiring a cron. Makes a tiny number of well-behaved
requests with a declared identity, at well under the SEC fair-access rate, and reports which
endpoints are reachable. It NEVER spoofs a User-Agent or retries aggressively to defeat a
block -- if an IP is blocked by policy, the remediation is to move networks (see
docs/edgar_access_remediation.md), not to disguise the client.

Usage:
    EDGAR_IDENTITY="Your Name <you@example.com>" python scripts/check_edgar_access.py
"""

from __future__ import annotations

import os
import sys
import time
import urllib.error
import urllib.request

IDENTITY = os.environ.get("EDGAR_IDENTITY", "").strip()

# A small, representative set: ticker map (light), a submissions JSON, a bulk index.
PROBES = [
    ("company_tickers.json", "https://www.sec.gov/files/company_tickers.json"),
    ("submissions API (CRWV CIK)", "https://data.sec.gov/submissions/CIK0002028537.json"),
    ("full-index (bulk)", "https://www.sec.gov/Archives/edgar/full-index/2026/QTR1/"),
]


def _probe(label: str, url: str) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": IDENTITY})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return label, f"OK {resp.status} ({len(resp.read())} bytes)"
    except urllib.error.HTTPError as e:
        hint = (
            " -> IP blocked by policy; use a different network (paths a/b/c/d)"
            if e.code
            in (
                403,
                401,
            )
            else ""
        )
        return label, f"HTTP {e.code}{hint}"
    except Exception as e:  # noqa: BLE001 -- a probe is allowed to report any failure
        return label, f"unreachable: {type(e).__name__}"


def main() -> int:
    if not IDENTITY or "@" not in IDENTITY:
        print(
            "Set EDGAR_IDENTITY to a real 'Name <email>' first (SEC fair-access requires a "
            "real contact in the User-Agent). Refusing to probe without one."
        )
        return 2
    print(f"Probing EDGAR as: {IDENTITY}\n(polite: 1 request / 2s, no retries)\n")
    reachable = 0
    for label, url in PROBES:
        name, result = _probe(label, url)
        print(f"  {name:32s} {result}")
        if result.startswith("OK"):
            reachable += 1
        time.sleep(2.0)  # well under the 10/s fair-access limit
    print(
        f"\n{reachable}/{len(PROBES)} endpoints reachable from this network. "
        + (
            "This box can serve as the egress path (a)."
            if reachable == len(PROBES)
            else "Some endpoints blocked -- see docs/edgar_access_remediation.md for alternatives."
        )
    )
    return 0 if reachable else 1


if __name__ == "__main__":
    sys.exit(main())
