# Bubble refresh operations, October 17, 2026

## Camera gestures and compact details, 2026-10-18T08:45:19.950437-07:00

Bubble dragging was the graph library's enabled default. It is now disabled.
Dragging over a bubble rotates the view. Click selection and camera pan remain.
The obsolete node-drag callbacks and their whole-field geometry rebuild were
removed. The financial graph SHA256 remains
f40f41d0ba786af1b6c1dfae78db422ea85a0d50f73c07800440fd0c4a9413e3.

Entity and deal details now use metric tiles and short bullets. Debt and cash
periods remain explicit. Repeated neighbor shortcuts were removed; All connections
retains every connection. Cards contain no citation links. The existing Sources
panel retains the selected entity or deal's full note and citation links, including
the issuer's longer subsequent-financing notes. Raw zero sentinels remain labeled
amount unmeasured. Arial 14/18 remains in use. The CoreWeave card fits its full
371px content inside the 390x844 mobile view without scrolling. Desktop and mobile
screenshots were rendered in the existing Chrome session and viewed. The computed
text and placeholder contrast minimum is 9.2095:1 over 27 compact-card checks.

The first timing comparison used different browser zoom levels and was withdrawn.
It remains retained in ui-interaction-review/. The corrected native pointer tests
verify the same 1440x900 CSS viewport, renderer ratio 1, initial camera and actual
CoreWeave pointer coordinates. Original: the node moved, the camera stayed fixed,
and script work was 0.982691 seconds over 4.3621 seconds. Updated: no node moved,
the camera rotated, and script work was 0.376391 seconds over 4.306 seconds. This
is about 62 percent less script work for that gesture, with both versions near
59 actual renderer calls per second. The corrected pan test also changes the
camera and target, with 257 render calls over 4.2969 seconds. Background rotation
and pan did not reproduce a separate low frame rate on this host. These are not
a general FPS speedup claim. Actual render counts are separate from display
animation callbacks; an early duplicate-callback sample was discarded.

node --test tests/viz/explorer.test.cjs: eleven passed, zero failed.
The source links/full-note preservation assertions pass. node --check and git
diff --check pass. The first test run found two assertions tied to the old card
copy and one missing raw-extraction label. The copy assertions now check the
same values in the new structure, and the raw label is restored. Failed passes
remain in the session record. No Python production code changed; complete CI
and deployment are checked separately for the publication commit.

Color remains a historical judgment, not a recomputed October measurement:
green 0, yellow 0.5, red 1. Twenty-eight core entities have assigned values;
79 core entities and the unmatched raw field remain unscored grey. No financial
source or risk judgment was changed by this interface work.

The retained source snapshots are named in
ui-interaction-review/snapshot.json under the refresh directory. Corrected
performance records are controlled-baseline.json, controlled-candidate.json and
controlled-pan.json in that directory. Initial browser debugging read true in
this pass; enhanced accessibility read false. Preserve that observed baseline
when closing only the owned QA targets and preview. Publication and restoration
have separate completion receipts. No secret files or GitHub authentication
settings were read or changed.

## Completed refresh and environment operation, 2026-10-18T04:44:21.915754-07:00

The final selected-document merge and source audit completed with 306,838 of
306,838 selected documents and zero missing. It retains 307,008 inventory rows.
The exhibit census checked 97,559 filing entries and acquired 38,026 documents
with zero failures. The complete capital graph, full raw visualization field,
freshness output and dated_engine_2026-10-17_v2 report all completed under the
2 GiB process-group budget. The observed final-processing peak was 497,370,384
bytes. The selected document and original URL measures remain separate because
two unavailable rendering URLs have verified official copies.

Publication 152245c32a72975bf311e21af79525923da8bd0c reached origin/main.
Pages 39123486180 and complete CI 39123486171 succeeded. publication-result.json
records matching deployed file hashes and the preserved original staged digest.
The main and auxiliary jobs have exited. No acquisition restart is pending.

### Project environment: check, undo and reapply

The active .venv now matches the reviewed uv.lock. The installer used the
verified temporary uv 0.13.1 binary, with --locked --all-extras. It changed 33
installed distribution records; actual before/final package inventories are in
security-environment-application-v3/. This supersedes the candidate count of 31.
The lock SHA256 remains
12d8ceca048c78b60b401e39b057ecd794c46358e4f3364f411b80337b595bc6.
No system package, shell configuration, authentication scope or global setting
was changed. API credentials were stripped from the install and test environments.

The retained restoration archive is
.codex/security-snapshots/2026-10-17/post-publication-20261018T113450.369821Z/.
venv-before and venv-updated are immutable restore sources. The operation renamed
the active environment into the archive, cloned FROM venv-before into .venv,
verified it, retained that restored active copy by rename, and cloned FROM
venv-updated into .venv. It then verified the final locked package inventory.
Both undo and reapply were executed at the real active path. No snapshot's
interpreter ran. Every file byte, symlink target, mode, filesystem flag and
modification time matched; directory metadata also matched. The executable
sequence is retained in verification_drivers/apply_locked_environment.py under
the refresh directory. Its result and four byte manifests are in
security-environment-application-v3/. The environment supervisor peaked at
133,842,768 bytes under 512 MiB.

The first copy stopped because cp -cRp could not preserve hidden Python symlink
flags. Its partial snapshot is retained untouched. The next host-Python attempt
stopped on a transitive httpx import before environment writes. The corrected
standalone driver uses cp -cR and copystat with follow_symlinks=False. A scratch
check proved all three links retained their target, mode, flags and modification
time before the full operation ran. No failed mutation was blindly replayed.

The final test command, with credential variables removed and PYTHONPATH=src,
was:

    .venv/bin/python -B scripts/run_with_memory_budget.py --budget-mib 1536 --report data/refresh_2026-10-17/installed-environment-tests-memory.jsonl -- .venv/bin/python -B -m pytest -o 'addopts=-ra --strict-markers' --ignore-glob='* 2.py' --no-cov -p no:cacheprovider -q

Output: 970 passed in 50.80s. Observed peak: 709,511,304 bytes. Validation
overlays were absent. Eleven Node tests passed. Ruff passed; 304 required files
passed formatting. A broader legacy-generator formatting check did not pass;
those pre-existing cosmetic differences were retained. The first scratch link
probe had a syntax error before execution; its corrected probe passed.

### Storage and remaining evidence limits

The historical SEC compression receipt still records 55,395 files, zero errors
and 46,908,620,800 fewer allocated bytes. Four large GLEIF CSVs remain normal
files after a supervised trial stopped before replacement. All source bytes,
logs and rollback copies remain retained. The project root is only
/Users/ted/Projects/bubble; /Users/ted/Documents/dev-archive/bubble is absent.
The rechecked project root inode is 70378520. Volume free space is read from
/System/Volumes/Data and is separate from the per-file compression savings.

No selected document gaps remain. Original 404 responses remain recorded.
The current registered demand basket is unmeasured; extracted SEC/FERC candidates
still require instrument review. Historical confidence values are dated judgments.
The live GitHub advisory still lists no patched Accelerate release. The active
HTML-only converter and its actual security checks passed. No alert was dismissed.
The web text reader could not open the Pages site; direct HTTP and actual Chrome
verified it. Owned browser controls and their restoration are recorded separately.

Earlier dated checkpoints are retained below. Their pending states are superseded by this completion entry.

## Currency description and market source checks, 2026-10-18T00:56:58.505344-07:00

The $90.184580B measure presents reported loan and note carrying amounts in USD.
It includes loans contracted in other currencies, including Bit Digital's CAD
credit facilities in its June 30 statement. Earlier entries describing the
aggregate as "USD-denominated" are superseded. Bitdeer's Bitcoin-denominated
borrowing remains separate. The source component balances and total are retained.
The primary Bit Digital filing is
https://www.sec.gov/Archives/edgar/data/1710350/000121390026088709/ea0300693-10q_bitdigital.htm.

The CleanSpark primary September 18 pricing notice and September 25 closing
notice were checked against their verified normalized-source hashes. Pricing
and closing remain distinct. The later DDC September 23 card remains the latest
registered coupon proxy. It retains its original-market-tape evidence tier;
its issuer offering memorandum was not independently acquired. Coupon and
issue yield remain separate.

FRED's public DGS5 and HY OAS pages still show October 15 observations, published
October 16, with the next release October 19. Those original frozen inputs remain
appropriate for October 17. Microsoft's Q4 release/transcript checks did not
supply a new comparable AI-business run-rate observation. Foundry token rates
and total Cloud revenue remain separate measures. The Anthropic and OpenAI
primary-page searches did not establish a new eligible registered demand basket.
No universal absence claim is made. The source checks are retained in
market-signal-revalidation.json. The original market snapshot is unchanged.

## Main acquisition complete and verified source copies, 2026-10-18T00:41:07.469578-07:00

The original acquisition ended with exit code 0 at 00:10 PDT on October 18.
It attempted 227,393 documents, acquired 227,347 and recorded 46 failures. The
observed peak was 2,068,515,024 bytes under its unchanged 2 GiB budget. Earlier
retries had recovered 27 failures. The resumed retry recovered 17 more; the two
remaining original SEC rendering URLs return 404 in both HTTP clients and Chrome.

The Theravance Form 4 complete SEC submission is available and contains the
requested primary_doc.xml ownership document. The standalone XML endpoint
returns zero bytes and is not counted as a recovered document. The Alumis
Schedule 13D official issuer mirror contains its accession and filer. Plain HTTP
clients received 403; the existing Chrome session returned HTTP 200. Its exact
response body is retained. No authentication or account settings changed.
The original failed URLs remain in the original manifests and error records.

The two replacement rows are acquired under their actual retrieval URLs.
Their source_document_replacements.json records original HTTP failures, source
representations, accession identity markers and byte hashes. The merger verifies
these bytes and retains the manifest. The coverage auditor reports selected
document coverage separately from exact original-URL coverage. The final result
will not claim that the two original HTTP URLs succeeded. The status builder and
retry driver share the same verified recovery logic. No original data was removed.
The recovery batch is source_gap_retries/20261018T072903.464955Z/.

The main-corpus scaling pass verified every raw hash for 268,980 documents,
81,775 extracted candidates and 20,624 tranches. Its capital build completed;
the complete pass peaked at 449,709,280 bytes under 1.5 GiB supervision.
The initial attempt stopped safely when a macOS child memory measurement failed.
Its child group was confirmed absent. The partial retry held two in-flight and
17 queued records, with no successful document. Its SQLite state was backed up
before resuming. Explicit group admission in the continuation avoided redundant
nested supervision. The next pass finished normally. The failed attempt remains.
The extended recovery proof verifies 268,982 documents and both official copies;
its selected-document coverage audit is recorded separately when completed.

All 960 local candidate tests passed in 14.82s. Focused strict Mypy for the new
source replacement validator passed. Ruff passed and all 299 files passed
formatting. Eight Node visualization tests passed. The actual Chrome Sources
panel shows 46 recovered failures, two verified source replacements and zero
unresolved document gaps. Arial remains 14/18, and the observed 390px body has
no horizontal overflow. The snapshot timestamp now displays Pacific date and
minute. Full timestamp precision remains in the JSON. The viewed screenshot
and exact source hashes are in viz_browser_validation_2026-10-17.json.
Browser debugging and enhanced accessibility were restored false; only owned
tabs and processes were closed. Source recovery probe failures are recorded in
official-source-recovery/receipt.json, including an unavailable read-only SSH
route and the unchanged source page CSP. No remote state changed.

The pre-upgrade .venv snapshot is an APFS clone under
.codex/security-snapshots/2026-10-17/venv-before-upgrades. All 59,169 files and
symlinks match; verified logical bytes total 1,942,538,766. The snapshot's
interpreter was not executed. Main .venv installation still waits for active
source processing to end. This is an environment snapshot, not another checkout.

The old waiting finisher 98015 and publisher 99024 were retired before any final
stages ran. Finisher 93982 and publisher 94613 now retain the distinction between
verified document completion and direct-URL completion. Their budgets remain
2 GiB and 512 MiB. The exhibit workload 86908 continues; full-field replacement,
final publication, environment installation and final browser checks remain.

## Financing correction and co-registrant repair, 2026-10-17T23:46:07.652486-07:00

The 13-issuer USD-denominated borrowing measure is now $90.184580B. The previous
$90.302128B included Bitdeer's $117.548M USD carrying amount of BTC-denominated
borrowing. That borrowing remains separately recorded. Bitdeer's June 30
USD-denominated balance is $1.724136B. The later formal September 29 statement
and its note columns are verified against the retained source. The separate
September 29 BTC principal is 3,669 BTC; no current USD equivalent is invented.

The reviewed event ledger now has 19 entries. It adds CoreWeave facility draws,
Nebius secured financing, Core Scientific's undrawn revolving/LC facilities,
MARA's USD facilities secured by BTC, Bit Digital's CAD facility and subsequent
draw/equity, and Bitdeer's USD facility, BTC facility and equity disclosures.
Commitments, draws, refinancing and later balances remain distinct. The review
has 45 relationships and the graph has 41 core entities with 58 connections.
Five new counterparties retain unknown fragility. RBC and JPMorgan roles do
not invent retained lender allocations. Volta's lease termination and conditional
backstop terms remain explicit. All new references use verified retained hashes.

The real Chrome session rendered 41 core entities, 7,687 retained grey points
and 9,640 total links. Search, Bitdeer's corrected card, the RBC facility card,
source links and mobile Sources were inspected. Sources and Deals now hide
other panels and selected cards; opening an evidence card closes those panels.
Viewed desktop/mobile screenshots show no body overflow. Arial remains 14/18.
The settled five-second observation rendered zero additional frames with a
13,176,229-byte JS heap. Eight Node interaction tests passed. Browser debugging
and enhanced accessibility were restored false; owned tabs and processes closed.
Exact source and screenshot hashes are in viz_browser_validation_2026-10-17.json.

SEC accession 0001918704-26-031708 proves that a co-registrant filing index can
link documents under a different CIK within the same accession. Parser v2
retains that canonical SEC URL while rejecting foreign origins, other
accessions and traversal segments. A SQLite backup and cofiler_rejections table
preserve the 960 previous path rejections before requeue. The new workload PID
86908 uses the same 2 GiB budget. Its log is exhibit-completion-cofilers.log.
An accession cache verifies retained raw bytes and avoids duplicate HTTP index
requests for co-filers. The census has 97,559 parents and 89,924 accessions.
The new pass has no failed parent indexes at this observation.

The supervised candidate suite returned 952 passed in 12.08s, with a
703,006,808-byte observed peak. Ruff passed; 297 files passed formatting.
An earlier invocation overrode the configured ignore glob and collected the
retained iCloud '* 2.py' copies. It returned 976 passed and two stale duplicate
failures. The corrected invocation restores the existing ignore glob; none of
those retained files was edited or deleted. Both logs remain.

Remote CI 39103139050 passed dependency installation, security checks, Ruff,
formatting and full strict source Mypy. Its two test failures were portability
issues: a process-footprint check included the Linux ML imports, and an exporter
test relied on ignored local acquisition files. The check now uses an isolated
child under the same threshold; the exporter supplies baseline schemas from
actual fixture extraction. Local full tests pass. Next remote CI is pending.

The finisher now rejects unchecked/failed exhibit parent indexes and an
incomplete freshness report. The publisher requires complete source coverage.
The old waiting publisher 93528 and finisher 93485 were retired by verified PID
before any stages ran. Current finisher 98015 and publisher 99024 wait under
their unchanged budgets. No acquisition was restarted for this guard update.

At 2026-10-17T23:46:07.652486-07:00, the main queue was {'acquired': 215945, 'failed': 46, 'inflight': 8, 'queued': 11394}; parent indexes were {'checked': 4261, 'queued': 93298}.
Full byte verification, complete capital graph/field, final dated report,
publication and main-environment dependency installation remain outstanding.

## Published financial review and valuation checkpoint, 23:09 PDT

Commit 0afb9b6f4de6b86df40d5031e87517e1b3201d4f reached origin/main.
Pages workflow 39101477259 succeeded. The deployed HTML, JavaScript, CSS and
graph hashes match the verified local files. The existing Chrome session showed
the current 36-node core, $90.302128B issuer balances and October 17 report date.
The retained grey field cutoff remains unverified. Full-source replacement is
still pending. financial-review-publication.json records the HTTP hashes;
viz_browser_validation_2026-10-17.json records the real browser observation.
The first CI run stopped at eight existing formatting failures. Those eight
files now pass formatting with unchanged ASTs. Complete remote CI for the next
checkpoint remains pending.

The four valuation input cards now use October 16 EV observations and reported
consolidated trailing revenue on a common basis. Source rows and exact prior-year
periods are checked. APLD's prior-year quarter is $80.934M, producing $872.252M
trailing revenue. Nebius's later formal June 30 statement reports $37.4906B RPO;
the broader $40B customer-commitment figure is separate. IREN's $16.6B combined
RPO and lease value remains a different accounting measure. APLD's $36B gross
base-term rent excludes renewal options. Assumed timing and FCF margins are
explicit. No new bubble probability or measured GPU lifetime is claimed.
The source card is bundled inside the Python package; a built wheel contains
identical card bytes. The original June inputs remain in git and snapshots.

The September issuance snapshot exactly matches the SHA-256 recorded in the
original September report. The October snapshot freezes the current registry.
Each dated runner now uses its own snapshot. The mutable overlay can continue
to read the current registry without making older reports fail or use later
prints. The original registered forecast priors and arithmetic remain unchanged.
Its 0.67 structural confidence is labeled as a June 3 historical judgment.

The record page now uses Arial at 14px and 18px. Actual Chrome checks covered
390px mobile and desktop, input disclosures, 1,001 long-name rows with emoji,
RTL/CJK and HTML-shaped text, empty data, a blocked market file and throttled
network. No unsafe image/script elements or horizontal body overflow appeared.
Computed contrast was at least 9.2095:1 over 91 visible text checks. Signal rows
and numeric wrapping were corrected after viewing the rendered page. All test
fetch overrides, blocks and throttling were removed. All owned test tabs closed;
remote debugging and enhanced accessibility were observed false after restore.
The owned preview server and CDP controller stopped. The record browser evidence
is in record_browser_validation_2026-10-17.json.

The full dependency candidate passes 947 tests at a 705,775,728-byte observed
peak. All 301 locked PyPI registry versions were checked with zero acquisition
errors; Accelerate remains the affected package under its known advisory. The
HTML-only converter restriction remains enforced. The candidate is tested in an
isolated overlay. The active acquisition environment has not changed. Its final
installation, with a retained snapshot, remains required after acquisition.
See dependency_security_audit_2026-10-17.md for package and verification details.

At 23:08 PDT the original acquisition had 198,054 acquired, 46 failed, eight in
flight and 29,286 queued documents. Its observed peak remains below 2 GiB. The
auxiliary exhibit census continues at the shared SEC rate. The finisher and
publisher still wait for both acquisitions; no complete-source claim is made.
The additional financing-context census is under review and has already found
further facilities to add before the final current report.


## Typed exhibit indexes and current browser checkpoint, 22:40 PDT

This entry corrects the 21:57 checkpoint below. SEC exhibit selection now reads
Document Type from the official filing document table. Filename-only selection
missed the CoreWeave and Applied Digital earnings releases. Both releases are
now acquired. All 3,029 indexes checked by the earlier filename method were
retained in previous_index_pass and requeued for the typed parser. The migration
used a SQLite backup. No acquired document was removed.

The exhibit job now uses four index executor workers with its four index slots.
Sixteen workers previously competed for those slots and let later baseline
filings pass pending current core filings. The current core parent indexes are
now all checked. The active log is exhibit-completion-priority.log. The prior
workers were stopped by their verified exact PIDs; all logs and markers remain.
The current prepared core library is core_review_v7/manifest.json: 415 verified
sources and zero missing selected core documents. Each financial card retains
its own immutable source hash and library reference.

The retained grey field has no independently verified observation cutoff.
June 3 is the historical report context, not proof of the field's date. The
viewer now says Unverified / retained field until the complete dated capital
graph replaces it. That replacement remains pending acquisition completion.

The real existing Chrome session rendered the 36-node current core and retained
7,687 grey points. Mobile Sources, debt cards, source links, search and cascade
interactions were inspected. The current page uses Arial at 14px and 18px,
shows no horizontal mobile overflow, and rendered zero additional frames during
a five-second settled observation. The observed JS heap was 13,034,251 bytes.
The unchanged color tokens retain a minimum checked text contrast of 6.0123:1.
An actual hidden-tab reload exposed an early initial camera fit; fitting now
waits for visibility and a rendered frame. Background-to-visible rendering was
checked again. Some paused CDP captures omitted a compositor layer. A native
view and an active Sources capture showed the complete page; failed captures
and the diagnostic ReferenceError remain retained as probe errors.

analysis/viz_browser_validation_2026-10-17.json records the exact current HTML,
JavaScript and CSS hashes fetched in Chrome and the viewed screenshot hashes.
The guarded publisher will reject sources changed after that check.

At 22:38 PDT the original acquisition had 184,155 acquired, 45 failed, eight in
flight and 43,186 queued documents. Its observed peak remained 2,068,515,024
bytes under its 2 GiB budget. The exhibit workload used about 148 MB. These
counts are dated observations; read the SQLite queues and supervisor logs for
live state. The complete-source finisher and publisher remain waiting.


## Current financial review and complete-source continuation, 21:57 PDT

This checkpoint supersedes the earlier June-core and continuation descriptions.
The October core review now verifies 13 issuer statement balances against saved
primary rows and raw/normalized SHA-256 hashes. It includes convertible notes
that partial XBRL debt tags omitted. The reported carrying amounts total
$90.302128B. They retain June 30 period ends, except Applied Digital August 31,
and include non-AI businesses. The seven later financing events are a separate
ledger. Gross issue principal and commitments are not silently added to those
balances. All 13 matched cash-flow periods show negative cash after capex.

The relationship review contains 38 source-supported connections. It corrects
the CoreWeave 67% Microsoft claim, the terminated Core Scientific merger,
the repaid Core Scientific term loan and Hut 8's converted Coatue note. It
separates trustee and agent roles from beneficial lending. It adds named
customer leases and lease-payment backstops. NVIDIA's conditional $105B PORTS
guarantee is separate from funded debt. Current NVIDIA 13F tables do not list
Applied Digital; that check does not cover every possible economic interest.
Unconfirmed historical connections remain qualified, with the original graph
preserved in historical_core. Current probabilities are unmeasured.

September priced-bond cards now supply S1. Convertible issues remain separate
from that registered coupon proxy. The October demand review preserves the
original basket and records why S4 has no fresh comparable primary observation.
analysis/market_snapshot_2026-10-17.json freezes the market inputs, retaining
October 16 prices and October 15 credit dates. An overnight completion cannot
use later observations under the October 17 cutoff.

The original filing discovery omitted exhibits. The auxiliary complete-exhibit
job repairs this coverage gap across every selected eligible parent filing,
including retained baseline parents. It has no per-filing exhibit cap. Its
97,559-parent census and independent document queue are under
data/refresh_2026-10-17/exhibit_completion/. It shares one SEC request/second
while the original eight-request producer runs, then uses eight after that
observed process exits. Discovery and downloads have separate semaphores to
keep the document workers fed. Both retain the authentic declared SEC contact.
PDF-only exhibits remain outside the current text-exhibit ingester.

At 21:57 PDT, the original queue held 164,764 acquired, 45 failed, eight in
flight and 62,576 queued documents. The exhibit queue had 747 acquired and no
failed documents; 2,332 parent indexes were checked and 95,227 remained. These
counts are dated observations. Recheck the queues and logs before acting.

The merge now uses disk-backed SQLite for deduplication and streams its output.
The full retained 41,589-document baseline passed every raw-document byte hash,
with a 35,537,376-byte observed peak. The capital builder now streams Deal
objects, keeps duplicate checks on disk, releases accumulators, indexes edges
by connected component and streams CSV serialization. Its full 74,805-row
baseline/current-FERC preflight finished at a 275,825,288-byte peak. All four
CSV outputs match the previous production graph logic byte for byte; the entire
serialized summary also matches. The reference check initially compared Python
tuples against JSON lists. Comparing both serialized documents resolved that
verification error without changing production results. The old retained-object
preflight stopped at its 1 GiB supervision budget. That partial attempt remains.

The complete field builder consumes only the explicit dated capital graph and
verifies its input hashes. It retains all named entities and every named
obligor-to-risk-bearer pair without the old four-party cap. Each pair counts an
extracted deal once. Existing positions survive by name; new positions are
deterministic. No browser force simulation runs for the raw field. The preflight
used 38,617,568 bytes and retained 5,746 entities and 6,977 pairs from that
74,805-row input. These are test-input counts, not the finished current corpus.

The previous waiting publisher (6502) and finisher (6278) were retired after
confirming that no postprocessing or publication had started. Their markers and
logs remain. The replacement finisher is recorded in
finish-start-current-review.json. It waits for the original acquisition and
the exact exhibit workload, retries recorded document gaps, verifies the merged
bytes, audits all selected URLs, builds the complete capital graph and raw
visualization field, then writes current freshness and dated engine v2.
The replacement publisher is recorded in publication-start-current-review.json.
It commits the current graph along with freshness and engine v2, preserves
Ted's original 15 staged additions and verifies the deployed graph hash too.
Both retain their supervision budgets and never restart a stopped acquisition.

Check the current continuation logs:

    tail -n 6 data/refresh_2026-10-17/acquisition-resumed-document-fix.log
    tail -n 6 data/refresh_2026-10-17/exhibit-completion-resumed.log
    tail -n 6 data/refresh_2026-10-17/finish-refresh-current-review.log
    tail -n 6 data/refresh_2026-10-17/publish-refresh-current-review.log

The financial review is current to the stated public cutoff. The broad source
acquisition and grey field remain incomplete at this checkpoint. Their final
coverage audit and observed deployment remain required work.

## Browser and publication checkpoint - 2026-10-17 18:50 PDT

The later dated checkpoints supersede the earlier pending states below.
Ted's latest confirmation authorizes using his existing Chrome and publishing
this work while retaining the existing published Git history. The exception
covers the 136 existing attribution matches. New commits must have zero matches.
No history rewrite is authorized or needed.

The explorer was rendered in the existing Chrome 155 session. Desktop and
390px mobile screenshots were viewed. Search, keyboard selection, core cards,
raw-point selection, all 459 connections on the largest raw-entity card, deal
cards and cascade controls were exercised. Reduced motion, ten rapid cascade
clicks, long mixed-script names, empty data and unavailable sources were checked.
At 150ms latency and 100,000 bytes/second with graph and overlay requests blocked,
the saved 28-entity core loaded with explicit unavailable-data messages.

Browser checks found and repaired synchronous render-resume recursion when
returning to a paused tab, an unclosed report definition list, and an empty
library tooltip. Grey lines now dim during selection. Header and legend
backgrounds preserve contrast over graph objects. Computed fonts are Arial at
14px and 18px; minimum checked text contrast is 6.0123:1.

After settling, Chrome rendered zero frames in five seconds. A post-cascade
sample taken during the remaining camera tween rendered 26 frames in five
seconds; a later settled sample rendered zero. The latter sample had 56 draw
calls in its last rendered frame, 7,687 points, zero textures and a 12,900,476-byte
JavaScript heap. These are observations on this browser, not a device-independent
speedup estimate. The full old renderer was not loaded for a comparative
benchmark, to avoid allocating its thousands of label textures in Ted's browser.

Exact observations, screenshot hashes and source hashes are recorded in
analysis/viz_browser_validation_2026-10-17.json. Local screenshots and test drivers
remain in data/refresh_2026-10-17/browser-validation/. The Node suite now has six
passing tests, including a regression for synchronous resume callbacks.

The existing finisher remains responsible for acquisition completion, retry,
full-byte merge, coverage audit, capital graph and dated engine v2. A separate
supervised scripts/publish_public_refresh.py process now waits for that exact
finisher PID. It requires its completion record and a drained queue. It verifies
the exact browser-checked UI hashes, preserves the original staged-diff digest,
and commits only freshness.json and the dated engine v2 JSON/Markdown outputs.
It accepts only a fast-forward of the known market-overlay files. Divergence,
unrelated incoming edits, source changes or stage failures stop publication.
It never restarts acquisition, retries a push, forces history or deletes files.

The publisher checks attribution, dry-runs and performs the authorized main push,
observes the Pages workflow, and compares the deployed freshness and explorer
file hashes. It publishes honest coverage gaps if sources remain unavailable;
publication does not mean every URL was acquired or the June core was recarded.
Its 14 focused tests passed, including preservation of an unrelated staged
addition in a real temporary Git repository. Mypy and Ruff passed. The first
Mypy run found one missing JSON-result annotation; that annotation was corrected.
The already-running process differs only by that inert type annotation; its
exact launch source is retained in .codex/refresh-2026-10-17/publisher-running-source.py.

Check the existing processes before starting anything:

    tail -n 6 data/refresh_2026-10-17/acquisition-resumed-document-fix.log
    tail -n 6 data/refresh_2026-10-17/finish-refresh.log
    tail -n 6 data/refresh_2026-10-17/publish-refresh.log

The publisher records publication-start.json and, after finishing, either
publication-result.json or publication-stopped.json in that run directory.
The exclusive start record prevents accidental duplicate launches. A partial
push is unknown until fresh remote state is checked; do not replay it blindly.
This checkpoint precedes the first push. Deployment is not yet verified here.

Bubble is at /Users/ted/Projects/bubble. The former Documents/dev-archive/bubble
location is absent. The move evidence remains in .codex/relocation-2026-10-17/.
Do not create a second checkout as a substitute for resuming this one.

The unbounded first refresh contributed to memory exhaustion and a remote reboot.
See [the incident and repair](refresh_memory_incident_2026-10-17.md). Heavy entry
points used for this refresh enter a process-group memory supervisor. It measures physical
footprint, stops its owned group above budget, and retains partial outputs.
This is a polling supervisor, not a kernel allocation limit. Inspect fresh state
after a stop. Never assume a partial operation failed or replay it blindly.

The resumed broad acquisition uses SQLite for pending documents and batches
filing discovery. Its SEC requests share an 8-request/second client. It retains
the full selected backlog and the new official-index CIK universe. Acquisition
is incomplete at this checkpoint. Recheck with:

    tail -n 8 data/refresh_2026-10-17/acquisition-resumed.log

The journal, queue, and raw sources remain under data/refresh_2026-10-17.
The driver accepts --resume after the previous owned process has ended.
Completed source batches remain immutable. The recovery tests include successful
journal replay and legacy failure keys. Failed URLs need reconciliation and
retry before claiming complete selected-manifest coverage.

The completed market refresh contains October 16 closes and October 15 credit
observations. All 19 graph quotes, 12 filing counts, eight BDC marks, four credit
series, and two adjacent quotes were present. BDC NAV is the latest reported
quarterly value found in saved SEC periodic filings, dated June 30. The NAV
builder excludes proxy estimates, future periods, and period-change facts.
It does not change the registered basket memberships or thresholds.

The latest GLEIF artifacts carry October 17 source timestamps. They contain
3,466,099 LEI records and 674,460 relationship records. The complete ownership
graph scans those relationships and retains 667,429 valid relationships among
440,154 entities. Self-links and incomplete endpoints follow the existing
production parser. The SQLite builder preserves the original fields, ordering,
reference replacement, and summary semantics in parity tests. Its full-input
run peaked at 85,148,128 bytes under a 512 MiB budget. The older object-based
attempt stopped safely at its 1 GiB budget; it produced no output directory.
Do not increase the budget to work around retained-record growth.

The August EIA workbook is the latest published release resolved from its page.
It was released September 24, with the next release listed as October 23.
The earlier July URL failed. The corrected ERCOT normalization retains 1,789
large/small generator records; its large-generator header occurs after the old
30-row scan window. The corrected PJM serial export contains 9,263 records.
PJM's anonymous export header is resolved from its public application and is
not stored in repository catalog metadata. These corrections retain the
unsuccessful first attempts.

The historical SEC storage pass compressed 55,395 files with zero recorded
errors. Every replacement passed complete before/after SHA-256 checks.
Allocated storage for replaced files fell by 46,908,620,800 bytes (43.7 GiB).
The volume's free space increased by 44,970,954,752 bytes (41.9 GiB) while
acquisition continued adding data. APFS sharing and concurrent writes mean the
volume change is not an isolated measurement of compression savings.

Compression preserves filenames and readable bytes. The snapshots retain the
same verified content in compressed APFS clones. Future writes to either copy
are independent. Original modes, ownership, timestamps, unrelated flags, and
extended-attribute hashes are checked. The pass skipped ineligible files.
It did not prune transcripts, logs, prior snapshots, or source artifacts.
The pass used a 512 MiB process budget and peaked at 106,562,424 bytes.

The retained action records and snapshots are under:

    .codex/storage-compaction/2026-10-17/historical-sec-text-v2/

Each action directory contains original.json, result.json, and snapshot.
To restore one file as an uncompressed file:

    .venv/bin/python -B scripts/compact_public_data.py --restore-action ACTION_DIRECTORY

The restore checks that the target still has the recorded content hash, retains
a snapshot of the target, and refuses to overwrite changed content. Compression,
restore, reapplication, and independent clone writes passed real filesystem
checks. Evidence is in data/refresh_2026-10-17/compression-tracked-roundtrip.json
and compression-roundtrip-verification.json. Never prune those snapshots.

To run a later compression pass, use a new archive directory:

    .venv/bin/python -m py_compile scripts/compact_public_data.py && .venv/bin/python -u -B scripts/compact_public_data.py --roots HISTORICAL_PUBLIC_DATA_DIRECTORY --archive .codex/storage-compaction/NEW_PASS

The first conservative pass skipped all tracked files and changed nothing.
The completed second pass explicitly preserves UF_TRACKED and the compression
flag. Both summaries remain available.

The explorer implementation uses one Arial family and two CSS sizes: 14px and
18px. The extracted field uses static Points and LineSegments buffers. Core
entities retain interaction; raw entities remain searchable and selectable.
Every connection remains accessible through the selected entity's card.
Rendering pauses while idle and wakes for interaction. Reduced motion removes
camera tweening and cascade animation. Libraries are pinned locally with their
licenses. The report date and market dates remain separate.

The UI has passed logic and data-parity tests. The minimum checked text contrast
across its declared text/background colors is 6.01:1. The generated SVG banner
was rendered and viewed. Browser rendering, interaction, throttled-network
checks, and measured frame performance remain unverified. Browser control is
pending Ted's confirmation under the Mac instructions. Do not describe the
explorer as visually verified or deployed.

Source freshness is generated from saved outputs:

    .venv/bin/python -B scripts/build_refresh_status.py --run data/refresh_2026-10-17

The status snapshots and original files are retained under .codex. The June
adjudicated core and confidence judgments have not been recomputed. A market
refresh does not update those conclusions. SEC coverage reconciliation, the
current complete capital graph, and the dated engine report remain outstanding.
The UI changes and new source outputs have not been pushed at this checkpoint.

Git fetched origin/main on this date. The remote had no newer commits than the
local base; local main was ahead. Preserve the 15 pre-existing staged analysis
additions. The staged raw-diff check is:

    git diff --cached --raw -z | shasum -a 256

Before adding this pass's files, and after committing only this pass's files,
its expected hash is df66eae0573bd34899df7e4451677d9050f1db80625921296cb8651112e2bf7d.

## Current acquisition log - 2026-10-17 17:04 PDT

The earlier resumed log records a safe budget stop at 14:11:25 PDT.
The document-memory repair and complete queue audit are in the incident record.
The subsequent main refresh uses:
    data/refresh_2026-10-17/acquisition-resumed-document-fix.log

This supersedes acquisition-resumed.log as the current progress log.
Check the private workload PID in its supervisor event before any resume.
The 2 GiB threshold is unchanged. Large documents run under a byte-weighted
text-processing reservation; downloads stream to disk. Completed raw sources,
failed response parts, prior results and every checkpoint remain retained.
The stopped queue and original edited files are backed up in
.codex/refresh-2026-10-17/before-document-memory-fix-1792281345903613000/.

## Public-source and continuation checkpoint - 2026-10-17 17:18 PDT

Dynamic source identity now includes request and revision metadata. The previous
URI-only check dropped FERC pages at the same API endpoint. Latest discovery
contained 47,232 FERC records; the older catalog acquired 46,669. A repair batch
acquired 476 artifacts with zero source errors: all 473 current FERC pages,
the current PJM cycle export and two current FracTracker pages. All 476 saved
artifacts passed full SHA-256 checks. The normalized FERC IDs are unique and
exactly match the discovered total. The earlier artifacts remain unchanged.

The repair wrapper failed only while relativizing its log path after acquisition.
Fresh inspection verified the completed outputs; the acquisition was not replayed.
The child exit code was not captured by the failed wrapper. The retained
repair-reconciliation.json records that distinction. A regression now verifies
the relative-log-path case.

The public derivation completed under 1 GiB at a 277,529,344-byte peak.
It retains 18,322 queue records after replacing 908 PJM serial rows represented
in the current cycle; all 105,405 equipment reference rows; and current tracker
records. It produces 47,046 pending PPA candidates from 47,232 source rows.
Its immutable input/output hashes and selection counts are in:
    data/refresh_2026-10-17/derived_public_current/input_manifest.json

The current FERC-only capital graph completed under 2 GiB at a
753,173,464-byte peak. Its 47,046 deals remain pending review. The current
ownership graph remains separate. These are not additive debt totals.

Modal's new page includes accessible static prices plus animated duplicate
digits and a changed CPU heading. The old parser silently returned no rows.
The parser now reads the static prices, supports T4 and records empty parses
as errors. Reprocessing all four saved snapshots produced 88 quotes, zero errors,
and a 57,606,648-byte peak. The new raw directory uses relative symlinks to the
saved originals; source acquisition dates and hashes remain unchanged.
    data/refresh_2026-10-17/gpu_prices_reparsed/

The dated engine v1 ran the existing deterministic market, financial,
physical-capacity and compute functions. It explicitly records incomplete SEC
acquisition, stale S1 and unmeasured S4. It adds no new bubble probability.
The June adjudicated core remains historical.

The supervised continuation is running:
    data/refresh_2026-10-17/finish-refresh.log
It waits for the exact observed acquisition PID to exit, rejects PID reuse,
requires a valid completion record and a drained queue, then runs one gap retry,
the production merge with full raw-byte hashing, the exact URL coverage audit,
the complete capital graph and the v2 dated engine report. Stage errors stop
later stages and retain their results. A stopped acquisition is never restarted
automatically. The continuation does not publish or rewrite Git history.

Source freshness uses Pacific dates for saved SEC panels even after UTC
midnight. Its regression covers 00:30 UTC while the Pacific date is still
October 17.

Git fetched successfully. Before this checkpoint, origin/main had no incoming
commits and local main was ahead by three. The required whole-history attribution
check returned 136 matching lines across 130 older commits, all with existing
Co-Authored-By trailers. None belongs to this work's new commits. History remains
unchanged. This conflicts with Projects/AGENTS.md:244, which requires zero matches
before pushing; an explicit exception or a separate authorized history decision
is needed before publication. Browser control also remains pending the required
confirmation under Projects/AGENTS.md:303. No push or deployment ran.

## Publication privacy repair - 2026-10-17 18:53 PDT

The first actual push was rejected with GH007 because this task's five local
commits used a private email address. A fresh fetch confirmed that no remote
commit had changed. GitHub email protection remains enabled. The authenticated
public profile identified Ted as tedthizzy, ID 21343243. GitHub's documented
ID-based noreply address is now configured only in this repository. Global Git
configuration and GitHub account settings were not changed.

Only the five unpublished commits were recreated with noreply author/committer
email metadata. Every tree and message is unchanged; only local parent hashes
changed as required. The published origin/main anchor stayed
058507182b198e80a2e662db126cc79c2ba8c264. The original commits are retained in
.codex/refresh-2026-10-17/unpublished-email-repair-015311036443/original-main.bundle.
Its bundle verification passed. The original index and repository config are
retained beside it. The staged-diff digest is unchanged. No force push ran.
The repair driver and measured memory trace are retained locally.

An earlier publication preflight used system Python and could not import httpx.
The local commit had already been created, but no push ran until the preflight
was repeated successfully through .venv. That check scanned all 82 changed
public files. Its single pattern match is the intentional private-key-header
fixture in the publisher tests; no credential value matched. Exact UI source
hashes matched browser evidence. Whole-history attribution remained 136,
covered by Ted's exception; all new commit messages had zero matches.

The privacy-preserving address follows [GitHub's email reference](https://docs.github.com/en/account-and-profile/reference/email-addresses-reference).
Future commits, including the waiting final publisher, inherit the repository
setting. Restore individual repository config values from the retained original
only after checking fresh state; never overwrite unrelated later config edits.

## Authentication checkpoint - 2026-10-17T18:57:02.539976-07:00

The privacy-repaired push reached a separate GitHub authorization block:
OAuth credentials lack workflow scope for .github/workflows/refresh-and-deploy.yml.
The CLI scopes are gist, read:org and repo. Existing SSH authentication returned
Permission denied (publickey). The existing Chrome session reached GitHub's
sign-in page. Ted was asked to sign in while acquisition continues. No account
protection was disabled, new key created, or token printed. Fresh fetches show
that origin/main is unchanged and the six local commits are unpublished.
The workflow edit remains retained with the other requested work. Publication
and deployment are not complete. The exact checkpoint is recorded in
data/refresh_2026-10-17/publication-auth-block.json. The finishing process and
its waiting publisher remain active; a later push cannot succeed with a workflow
change until GitHub authorization is resolved. Inspect fresh state before retry.

## Sign-in request withdrawn - 2026-10-17 20:24 PDT

The sign-in was avoidable. The existing published workflow already deploys
main pushes and retains saved market data after refresh failures. The optional
edit only improved warning presentation and changed a generated commit message.
The task now retains the published workflow byte for byte. No additional GitHub
permission or browser login is required for the visualization and source updates.
The GitHub sign-in tab opened by this task was closed.

Only this task's seven unpublished commit trees were adjusted to retain that
one workflow file. Every other tree entry is unchanged. Published history and
Ted's original staged-diff digest are unchanged. Original commits, the improved
workflow and an applyable patch remain under
.codex/refresh-2026-10-17/retained-workflow-032315773473/.
No source data, UI behavior or deployment trigger was removed. The waiting
final publisher can use the existing repository-write credential after this
checkpoint is pushed. Its queue and exact-PID checks remain unchanged.

## Live verification and copy feedback - 2026-10-17T20:31:37.168541-07:00

The normal push succeeded using the existing credential. Pages workflow
39093503858 completed successfully. The deployed explorer JS, CSS and freshness
bytes matched the local checkpoint. Actual Chrome checks on the public URL
confirmed 7,715 entities, two Arial sizes, a working CoreWeave search/card with
18 connections, and zero rendered frames in a settled five-second interval.
The 390px view had no horizontal overflow, and the session reported no runtime
exceptions. The market overlay bot commit was fast-forwarded without changing
Ted's original staged work.

Ted then requested removal of explanatory subtitles. The tagline and successful
load instructions were removed, the search placeholder is Search, and the
redundant Sources introduction was removed. Loading and actual error states
remain available. Desktop/mobile screenshots were viewed; six Node tests passed.
The exact UI hashes in the browser evidence were updated for the waiting final
publisher. The copied June report data remains historical.

## Copy feedback deployed - 2026-10-17T20:41:05.920684-07:00

Commit a02fffcc94e66dd1ef033a2a0b9d0a6bca4cf4bd deployed through the unchanged
workflow in successful run 39093958460. HTTP hashes matched local index.html,
explorer.js and explorer.css. The public page was rendered and viewed again
on desktop and mobile. It has no tagline or successful-load instructions.
Search still selected NVIDIA; all 7,715 entities remain available.

The preview server and browser driver were stopped by their verified owned
PIDs. Remote debugging was switched off. The accessibility setter reported
-25208 after the settings tab closed, but its returned state and a separate
fresh AX probe both showed the original false state. Initial restoration
attempts stopped before changes because the guard expected DevTools; the
observed title was Inspect with Chrome Developer Tools. The corrected helper
and observed results are retained with browser-validation evidence.

The GitHub runner returned zero fresh EDGAR filing counts while other market
sources succeeded. Its source_status lists all twelve missing. The original
September public baseline also had zero EDGAR counts. Earlier twelve-count
observations and all saved submissions remain retained locally and in Git.
Do not claim current SEC filing counts are available on the deployed overlay.
Broad acquisition, the finisher and its final publisher remain active.

## Financing deployment and security follow-up, 2026-10-17T23:51:08.162147-07:00

Commit 24ab2703507e0e35eeb7269d950d0c7b406b7177 reached origin/main.
Pages 39105258021 and complete CI 39105258023 succeeded. The deployed HTML,
JavaScript, CSS and graph hashes match the reviewed financing checkpoint.
The complete CI passed strict Mypy and tests with five platform skips. The
initial publication helper used system Python and stopped at its import of
httpx before any mutation. Fresh git state was checked, and the project .venv
interpreter completed publication. Ted's original staged digest is unchanged.

GitHub's post-push alert set added the Mako advisory omitted from PyPI metadata.
The fixed release is 1.4.2; the revised lock selects 1.4.3 and only changes Mako.
All 301 locked registry versions were rechecked with zero acquisition errors.
The full Mac candidate including Mako passes 952 tests at a 704,497,800-byte
peak. Main-environment installation remains pending acquisition completion.
The original lock and all previous audit records remain in git and snapshots.

Storage trial, 2026-10-17T23:53:19.705356-07:00: the
large immutable GLEIF CSV trial stopped at the unchanged 512 MiB budget, with
642,123,000 bytes observed. Native ditto was in the measured workload. The
attempted source's SHA-256, size and modification time still match the saved
pre-action record. No replacement action completed. Partial files and the
original record remain under .codex/storage-compaction/2026-10-17/current-gleif-csv.
The eligibility maximum was restored to its original 256 MiB; the script again
matches git. The original-limit pass returned 2 compressed,
4 skipped, 0 errors and 37613568 allocated
bytes saved. These large CSVs remain available uncompressed. The earlier
43.7 GiB historical SEC compression savings remain the completed storage result.
No budget was raised and no source was deleted. See gleif-csv-compression-stopped.json.

Main-document coverage proof, 2026-10-18T00:43:15.064499-07:00:
main_document_recovery_proof/coverage.json reports 265,099 selected documents
acquired, zero missing and zero unresolved errors. Exact original-URL coverage
is 265,097 of 265,099. The two official copies remain separately identified.
The 268,982-document merge verified every raw byte hash at an 86,819,320-byte
observed peak. The 960-test run peaked at 706,807,992 bytes. The full exhibit
census remains pending; this is a main-corpus milestone, not final completion.

## Memory measurement guard, 2026-10-18T01:14:43.773543-07:00

The macOS physical-footprint measurement retries a transient EPERM twice, with
10 ms waits. Persistent measurement failure still stops the workload. A zero
measurement requires an absent process or confirmed zombie. Failed measurements
record the exact PID and errno without process arguments. Memory budgets remain
unchanged. Existing running supervisors retain their originally loaded code.

The supervised focused memory tests passed: 8 passed in 1.45s. The complete
local suite passed: 964 passed in 14.67s, peak 703,334,536 bytes under 1.5 GiB.
The commands and reports are retained as measurement-guard-tests.log and
measurement-guard-full-tests.log with their memory JSONL reports. Tests cover
transient EPERM, persistent EPERM, absent and zombie processes, and real group
budget enforcement. Local tests use the staged security package overlays;
installation into the active environment follows completion of source jobs.

## Private capital and compute reconciliation, 2026-10-18T01:24:28.051805-07:00

The relationship review now contains 147 reviewed pairs. The graph has 107 core
entities and 160 retained connections. All original graph participants and the
historical_core remain. The current financial total is unchanged. Source
provenance is retained in lab_relationship_review/manifest.json: 22 sources
with original and normalized SHA256 hashes, including seven exact HTTP 200
response bodies acquired through the existing Chrome session. HTTP 403 attempts
and the original 404 Series C catalog guess remain retained; the actual company
Series C page was then located and acquired. No login, cookie export, account
setting or CSP change was needed.

Later Amazon and SoftBank disclosures supersede announced-capital readings.
Amazon OpenAI funding is $50B complete. Amazon Anthropic investment cost is $18B
at June 30; $15B separate milestone-linked capacity remains. SoftBank investment
cost is $64.6B cumulative after October 1. The repaid and canceled March bridge
is not portrayed as current debt. The shared OpenAI revolver has eleven named
banks, no invented individual allocations, and zero drawn at its March close.
Current draws remain unmeasured. Round totals retain overlaps with strategic
commitments. The source review does not attribute Alphabet's anonymously named
private-company balances to Anthropic. The reported Nscale contract is also
unquantified. Vendor gigawatts remain planned agreements, not verified delivery.

The supervised full Python suite passed: 966 passed in 13.52s, peak 704,514,208
bytes under 1.5 GiB. Node interactions passed all eight tests. Ruff passed src,
tests and the changed producer; formatting passed 300 files. A broader optional
Ruff pass over all scripts reported 42 pre-existing findings in unrelated
historical drivers; those files were not edited. One source-inspection command
initially lacked PYTHONPATH and stopped at import before any write. The corrected
command verified the source hashes before inspection.

Actual Chrome checks rendered the expanded 107-core graph at desktop 1291x724
and mobile 390x844 CSS pixels. Search opened Amazon and SoftBank, then the Amazon
$50B evidence connection. Sources closed the active evidence card. All views
retained Arial at 14px and 18px. Body width matched each viewport. The placeholder
used rgb(173,184,200) on rgb(12,20,32), contrast 9.2095:1. The unchanged full
color-token minimum is 6.0123:1. Screenshots were opened and viewed. A 5002.9 ms
idle observation had zero rendered frames, rendering paused, 269 draw calls when
rendered and 12,912,817 bytes of JavaScript heap. No runtime exceptions were
observed. Prior graph measurements retain their own dates.

Owned browser tabs, controller and preview PID 63356 were closed. Remote
debugging returned false. The accessibility setter again returned -25208 after
the settings tab closed; actual readback was false. No other tabs were closed.

## Report provenance and published private capital, 2026-10-18T01:30:32.115699-07:00

The final dated report now hashes the relationship review, its private-capital
source manifest and the consumed demand review. It includes separately dated
funding rounds and shared credit-facility records. A changed manifest or source
published after October 17 stops report generation. The actual saved manifest
passed: 147 reviewed relationships and 22 private-capital sources. The full
local suite passed: 969 passed in 12.02s, peak 706,873,504 bytes under 1.5 GiB.
Ruff passed src, tests and the changed report builder; all 301 checked files
passed formatting. The waiting finisher will execute the updated builder.

Commit a3414b05878645219c68c99901d541c6e17b92e8 reached origin/main. Pages
39111487353 and complete CI 39111487391 both succeeded, including full strict
source Mypy. The deployed index, JavaScript, CSS and graph hashes match the
actual Chrome-verified checkpoint. The HTTP receipt is private-capital-publication.json.

## Vendor relationships and full main-field rehearsal, 2026-10-18T02:19:05.789244-07:00

The relationship review now has 148 reviewed pairs and 161 retained graph
connections across 107 core entities. The additional OpenAI/NVIDIA connection
records the primary February 27 3 GW inference and 2 GW training announcement.
The July NVIDIA filing explicitly requires exclusive NVIDIA infrastructure at
the guaranteed PORTS site, subject to limited exceptions. The first annotation
attempt stopped at an assertion because the existing note lacked that phrase;
fresh state still showed 147 pairs. The actual hash-verified filing was then
checked before the source-backed annotation was applied.

Vendor review flags now use current reciprocal funding/purchase relationships
and explicitly documented hardware exclusivity. The NVIDIA-only checks are
removed. Historical Google investment and undrawn bank roles do not establish
current vendor purchase loops. These are review flags, not traced dollar flows.
SpaceX and Google cards now show their existing dated adjacent market quotes.
No new quote provider or API call was added. Raw candidates with no measured
amount display amount unmeasured, preserving the original raw source values.

The completed main-corpus field rehearsal used the production field builder.
It retained 17,786 entities, 128,821 extracted candidates and 7,933 connections,
with 33 core matches and a 51,331,552-byte peak under 512 MiB. Its 17,786 raw
display names are unique. This artifact is not published and excludes the
auxiliary exhibit census. A filter-only Node diagnostic on 17,860 total
entities returned a 1.112 ms p95 over 1,100 searches. A cached version saved
less than a millisecond; no additional search cache was added. This is not a
browser latency result. The benchmark retained identical query results.

Actual Chrome rendered the larger field at 390x844 and 1291x724 CSS pixels.
Arial remained the sole declared family, at 14px and 18px. Body widths matched
the viewports. Sources closed the evidence card. Google displayed the existing
GOOGL quote; Amazon displayed its current investment source and vendor flag.
A grey-point click opened raw-party evidence. Initial pointer probes missed;
DOM event capture measured a 1.25 coordinate factor from the existing profile
zoom. The full pointermove/down/up sequence with explicit button states then
selected raw parties. The production picking code was unchanged. A settling
probe counted 15 frames after clearSelection; the settled 5002.4 ms observation
counted zero frames, with rendering paused and 15,999,685 bytes of JavaScript
heap. No runtime exceptions were observed. The unchanged text-token minimum
remains 6.0123:1. Updated screenshots were opened and viewed.

The general visualization rebuild now applies the current core review before
matching raw parties. Its new regression checks that current counterparties
exist when field projection runs. The real generator reproduced graph_data.json
and index.html byte for byte. The supervised full suite passed 970 tests in
13.65 seconds at a 702,924,960-byte peak under 1.5 GiB. All eleven Node tests
passed. Ruff passed src, tests and the changed producers; 302 files passed
formatting. The initial Callable import lint finding was corrected with a
type-checking import before the passing run.

All owned QA tabs, controller and preview PID 19001 were closed. Remote debugging
and enhanced accessibility read back false. The accessibility setter returned
-25208 after the settings tab closed; actual readback was false.

The latest saved live refresh received all 21 quotes, 13 filing counts, four
credit series, eight BDC marks and two adjacent quotes, with no reported source
errors. Earlier missing filing-count observations remain historical. The
revalidation is retained in live-source-status-revalidation.json. No refresh
authentication or network mechanism changed.

The local environment continuation remains supervised at 512 MiB and waits for
successful final publication. Main .venv installation and its actual undo/reapply
checks remain pending. The original project path was rechecked absent, with the
current checkout inode 70378520. No second checkout was created.
