# September 16, 2026 capital graph refresh

The dated driver is `scripts/refresh_capital_graph_2026_09_16.py`. It names only the September 16 FERC PPA, EDGAR deal, and GLEIF CSV inputs. It does not scan the historical data roots or import the June AI-direct handoff fixtures. Its ignored graph artifacts and JSON manifests are under `data/capital_graph_refresh_2026-09-16/`.

The FERC-only run read 46,483 derived PPA rows from `data/source_acquisition_2026-09-16/derived/ppa_deals.csv` (SHA256 `78eae144a00e83224f9e841292009f5e76b1565f494ea99db830a95bc1c5cd47`). Each row points to official FERC dataset 17 at `https://data.ferc.gov/api/v1/dataset/17/`. There were no duplicate `(deal_id, source_uri)` keys. All 46,483 rows are pending human review; zero are approved or overridden. The source labels 25,156 rows Active and 21,327 Inactive. Those labels describe FERC PPA records, not metered data-center load.

The production capital graph builder emitted 4,175 entity nodes, 6,741 source-backed PPA edges, 54,605 contract nodes, and 122,636 contract edges in `ferc_only/`. It emitted zero USD notional. Its 2,210,270.81 MW PPA-capacity field mixes active and inactive source records and aggregates graph edges. It is neither unique committed capacity nor delivered power. The raw source-row `amount_mw` sums to 1,223,642.71 MW for Active rows and 1,007,226.03 MW for Inactive rows; these are non-additive agreement records. The graph's 155 AI-relevant edges are heuristic name/keyword matches and remain pending review.

The GLEIF ownership layer read `ownership_records.csv` (SHA256 `014d80381cf5b9d12928611c2912f1e811749f666116a693833f06c11cff8d99`) and `lei_records.csv` (SHA256 `7f8a2236dff127f518f4fecefe690a14654eb356f9096ae7b6c5f967020f02ca`) from `data/source_acquisition_2026-09-16/gleif/source_rows/`. The production ownership builder scanned 669,374 rows and emitted 662,417 relationships among 437,020 LEI nodes in `ownership_current/`. The relationships include 482,099 Active and 180,318 other statuses. This is a separate legal-entity and consolidation graph. The production code does not join GLEIF relationships to capital obligations, so this refresh makes no ownership-based financing exposure claim.

Graph notional is repeated across parties and contract relationships. The `total_edge_notional_usd` field is a sum of exposure edges, not a distinct-obligation total. This FERC-only graph has no USD notional, so the issue becomes material only when EDGAR debt, lease, or guarantee rows are added. Exact duplicate source rows are removed by `(deal_id, source_uri, content_hash)`; conflicting content for one `(deal_id, source_uri)` fails the run. Different source IDs that describe one economic obligation are not merged. Rejected rows are excluded; pending rows remain labeled pending. A complete graph must not be described as reviewed exposure until its source rows are adjudicated.

QA commands and observed output:

```text
python3 -m py_compile scripts/refresh_capital_graph_2026_09_16.py tests/test_refresh_capital_graph_2026_09_16.py
# exit 0
.venv/bin/ruff check scripts/refresh_capital_graph_2026_09_16.py tests/test_refresh_capital_graph_2026_09_16.py
# All checks passed!
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. .venv/bin/python -m pytest -q -o addopts='' tests/test_refresh_capital_graph_2026_09_16.py
# 2 passed, 1 warning in 0.11s; warning is unknown asyncio_mode config with plugin autoload disabled
PYTHONPATH=src:. .venv/bin/python scripts/refresh_capital_graph_2026_09_16.py --mode ferc-only --layer capital
# 46,483 graph deals; 46,483 pending; zero reviewed; exit 0
PYTHONPATH=src:. .venv/bin/python scripts/refresh_capital_graph_2026_09_16.py --layer ownership
# 669,374 ownership rows scanned; 662,417 relationships; exit 0
```

Independent CSV row counts and recomputed SHA256 hashes matched each output's `input_manifest.json`: FERC entity nodes 4,175, exposure edges 6,741, contract nodes 54,605, contract edges 122,636; GLEIF nodes 437,020 and relationships 662,417. Exact output file hashes are in the two manifests. The dated EDGAR `deals.csv` was absent at the time of these two runs, so no EDGAR financing finding is included here yet.

The GLEIF source-row URIs resolve to the official [relationship concatenated file](https://leidata.gleif.org/api/v1/concatenated-files/rr/get/42221/zip) and [LEI concatenated file](https://leidata.gleif.org/api/v1/concatenated-files/lei2/get/42218/zip). The local source rows record retrieval at about 17:04 Pacific on September 16, 2026.
