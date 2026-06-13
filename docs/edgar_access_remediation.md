# EDGAR access remediation (WS2.1)

**2026-06-12; corrected 2026-06-13.** Earlier this card claimed both the local machine and the GitHub Actions runner are 403-blocked from EDGAR. **That was wrong for the local environment — direct testing on 2026-06-13 showed all EDGAR endpoints (`data.sec.gov`, `www.sec.gov`, `efts.sec.gov`) return HTTP 200 from the local research box** with a compliant `User-Agent`. The local environment *is* a working egress path; the first exhibit verification (the SpaceX 424B4 — see `analysis/spacex_adjacency.md`) was done from it. **Only the GitHub Actions runner IP is blocked** (the hourly overlay's EDGAR filing-count step returns 0 every run). So exhibit-level verification — utilization bottom-up, waterfall depth, the SpaceX terms, the BDC schedules — is **not blocked**; it runs locally now. This card remains useful for (i) automating it on a cron and (ii) the runner case. **No path uses User-Agent spoofing or any evasion.**

## The four paths (priority order)

### (a) Residential / office egress box — [TED], the unblock
Run the existing fetchers from Ted's home or office network (a normal residential/commercial IP that EDGAR serves), on a cron, with the declared identity.

```bash
export EDGAR_IDENTITY="Ted <ted1508@gmail.com>"   # SEC fair-access: real contact in the UA
just edgar-manifest --all-public --since 2024-01-01 --include-exhibits --max-workers 16 \
    --sec-domain-concurrency 8 --sec-requests-per-second 8     # <= SEC's 10/s fair-access lane
just edgar-acquire data/manifests/edgar_filing_manifest_*.csv --output-dir data/edgar_acquisition
```

Set a launchd/cron entry to run the daily-delta manifest (small) and rsync `data/edgar_acquisition/` back to wherever extraction runs. This is the only step that needs Ted's network; the box can be a spare Mac, a Raspberry Pi, or a cheap always-on machine. Verify reachability first with `scripts/check_edgar_access.py` (below).

### (b) SEC bulk datasets — no per-request fetching
SEC publishes full bulk archives that sidestep per-filing rate limits and are mirrorable:
- `https://www.sec.gov/Archives/edgar/full-index/` (quarterly form indexes)
- `https://www.sec.gov/dera/data/financial-statement-data-sets` (XBRL financial-statement sets)
- `https://www.sec.gov/files/company_tickers.json` (ticker→CIK; already used by the overlay)

Pull these once from path (a) or any compliant network, commit the derived indexes, and the manifest build needs no live SEC calls. Best for the structured financial-statement numbers; weaker for narrative exhibits (EX-10 credit agreements), which need (a) or (d).

### (c) Commercial EDGAR mirror API — paid fallback (~$1–3k/mo)
If (a) is impractical, a commercial mirror (e.g. a filings API) returns the same public documents from compliant infrastructure. Cost is the only real line item in the whole program; use it only if the free paths fail. The fetchers' source-URI provenance is preserved (the document is the same public artifact; only the transport changes).

### (d) Browser-assisted manual pulls — top exhibits only
For the highest-value exhibits (the SpaceX S-1 termination clauses; the top 10–15 facility credit agreements), a human can open the EDGAR page in a normal browser and save the document into `data/edgar_acquisition/documents/` with a hand-written inventory row (source URI, retrieval timestamp, content hash). Slow, but it upgrades a specific carded item from press to filing tier immediately, and needs nothing but a browser. The SpaceX adjacency card and the top waterfall facilities are the priority queue.

## What unblocks once any path is live

| downstream | status | unblocked by |
|---|---|---|
| Utilization bottom-up (11 issuers) — WS2.2 | scaffold ready | (a) or (b) for transcripts/financials |
| Waterfall depth (top 10–15 facilities) — WS2.3 | schema ready | (a) or (d) for EX-10 credit agreements |
| SpaceX S-1 exhibit verification | carded press-tier | (d) is enough (one document) |
| BDC schedules of investments (S3' exposure) | carded press-tier | (a) or (d) |
| Daily-delta ingest — WS3.2 | code ready | (a) on cron |

## Compliance invariants (non-negotiable)

- Declare a real contact in `EDGAR_IDENTITY` / the `User-Agent` on every request.
- Stay at or below the SEC's published 10 requests/second fair-access limit (`--sec-requests-per-second 8` default).
- Never spoof a User-Agent to defeat a block. If an IP is blocked, move networks (paths a/b/c/d) — do not disguise the client.
- Preserve source-URI + retrieval-timestamp + content-hash provenance on every acquired document (the existing fetchers already enforce this).

Run `python scripts/check_edgar_access.py` from any candidate network to see, politely, whether that network can reach EDGAR before wiring a cron.
