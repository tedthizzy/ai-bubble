# Explorer data status, September 16, 2026

The checked-in explorer is a June 2026 forensic snapshot. Its graph and verdict have not been recalculated from the September research. The current research and bubble assessment are in [the September 16 full refresh](../analysis/FULL_REFRESH_2026-09-16.md).

- `viz/graph_data.json` records `meta.generated_from = BURRY_REPORT_EvidenceGated_20260603-2312`. The core data embedded in `viz/index.html` names the same report. Their `0.67` and `0.25` verdict readings, exposure amounts, company notes, and cascade are historical June outputs.
- The checked-in `viz/live.json` records `generated_utc = 2026-06-13T13:46:40Z`. Its market quotes, credit series, issuance card, and signal statuses are therefore not September observations. The overlay script describes an hourly refresh, but that schedule does not establish the state of the deployed site.
- The checked-in `viz/expectations.json` records `as_of = 2026-06-12`. The checked-in `viz/calendar.json` records `as_of = 2026-06-13`.

The September 16 research includes new public-company filings, financing terms, demand data, power and semiconductor evidence, and registered market signals. Those observations live in the dated research artifacts. They have not been substituted into the June graph or its embedded fallback. The deployed site's current contents and refresh schedule have not been observed here.

The checked-in [scored-record page](track_record.html) still says the first `P_real` Brier resolution is the 2026-Q4 TIMING-KILL adjudication. That display is incorrect. Q4 adjudicates TIMING-KILL; `P_real` covers filing-verified qualifying issuer events through September 30, 2027. It can resolve positive on an earlier verified event, while a negative result needs the full window and a complete issuer-event audit. See the dated [verdict-tree correction](../analysis/verdict_tree.md#september-16-2026-scoring-correction) and its [outcome rule](../src/bubble/verdict_tree.py). The page has not been edited or visually verified here, so its Q4 statement must not be used to score `P_real`. The June 2026-Q2 engine peak is an elapsed input-pressure date, not a realized issuer event.
