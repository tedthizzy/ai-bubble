# =============================================================================
# BUBBLE — Just Commands (the single ergonomic interface)
# Install: `brew install just` (or cargo install just)
# Usage: `just up`, `just source-catalog`, `just ui`, `just burry-report MSFT`
# =============================================================================

set dotenv-load := true
set shell := ["bash", "-c"]

# Default recipe
default:
    @just --list

# --- Environment ---
install:
    uv sync --all-extras
    pre-commit install || true

sync:
    uv sync --all-extras

# --- Docker / Infra ---
up:
    docker compose up -d
    @echo "Neo4j: http://localhost:7474 | MinIO: http://localhost:9001 | Postgres: localhost:5432"
    @echo "Wait for healthchecks, then: just bootstrap-neo4j"

up-full:
    docker compose --profile with-prefect up -d

down:
    docker compose down

logs service="neo4j":
    docker compose logs -f {{service}}

bootstrap-neo4j:
    @echo "Bootstrapping Neo4j schema only (idempotent)..."
    uv run python -m bubble.graph.client --bootstrap

# --- Core Development ---
lint:
    uv run ruff check src tests
    uv run ruff format --check src tests

format:
    uv run ruff format src tests
    uv run ruff check --fix src tests

typecheck:
    uv run mypy src

test *args:
    uv run pytest {{args}}

test-fast:
    uv run pytest -x -q --tb=line

ci: lint typecheck test

# --- Data & Extraction (the Burry core) ---
# Compatibility alias: build a real-source acquisition catalog without graph seed data.
seed:
    uv run python scripts/seed_graph.py

# Ingest a specific CIK (uses edgartools + LLM if keys present)
ingest-cik CIK *FLAGS:
    uv run python -m bubble.ingestion.edgar.client ingest {{CIK}} {{FLAGS}}

# Build an auditable SEC filing backlog before extraction.
edgar-manifest *FLAGS:
    uv run python scripts/build_edgar_manifest.py {{FLAGS}}

# Build a real-source acquisition catalog for filings plus curated non-EDGAR sources.
source-catalog *FLAGS:
    uv run python scripts/build_source_catalog.py {{FLAGS}}

# Download EDGAR source documents from a manifest and emit pending deal candidates.
edgar-acquire MANIFEST *FLAGS:
    uv run python scripts/acquire_edgar_documents.py {{MANIFEST}} {{FLAGS}}

# Acquire raw artifacts and normalized extracted rows from a real source catalog.
source-acquire CATALOG *FLAGS:
    uv run python scripts/acquire_source_catalog.py {{CATALOG}} {{FLAGS}}

# Count acquired source corpus and extracted rows across filings, projects, queues, permits, and deals.
source-coverage *FLAGS:
    uv run python scripts/source_coverage_report.py {{FLAGS}}

# Audit production CSV outputs for blocked/non-source-backed provenance.
source-invariants *FLAGS:
    uv run python scripts/audit_source_invariants.py {{FLAGS}}

# Build source-backed entity universe and expanded EDGAR CIK candidates.
entity-universe *FLAGS:
    uv run python scripts/build_entity_universe.py {{FLAGS}}

# Run full end-to-end on a high-priority name (example: Microsoft data center capex notes)
ingest-msft:
    just ingest-cik 0000789019 --latest-10k

# Produce a real "Burry Report" artifact for an entity (Markdown + JSON + red flags)
burry-report ENTITY="MSFT":
    uv run python scripts/run_burry_report.py {{ENTITY}}

# Re-validate all high-risk nodes (simulates weekly deep pass)
revalidate:
    uv run python -m bubble.orchestration.prefect_flows.revalidate --watchlist

# Load source-backed physical evidence CSVs and create project risk assessments.
physical-evidence DIR="data/physical" *FLAGS:
    uv run python scripts/ingest_physical_evidence.py {{DIR}} {{FLAGS}}

# Match data-center queue rows to tracker-backed physical projects.
queue-project-matches *FLAGS:
    uv run python scripts/match_data_center_queues.py {{FLAGS}}

# Match EPA/EIA permit and equipment rows to tracker-backed physical projects.
physical-record-matches *FLAGS:
    uv run python scripts/match_physical_records.py {{FLAGS}}

# Roll up project-level physical risk scores from source-backed evidence.
physical-risk-summary *FLAGS:
    uv run python scripts/physical_risk_summary.py {{FLAGS}}

# Load source-backed capital/deal CSVs and compute leverage/refinancing metrics.
capital-evidence DIR="data/capital" *FLAGS:
    uv run python scripts/ingest_capital_evidence.py {{DIR}} {{FLAGS}}

# Build source-backed capital exposure graph CSVs and summary.
capital-exposure-graph *FLAGS:
    uv run python scripts/build_capital_exposure_graph.py {{FLAGS}}

# Build source-backed ownership/consolidation graph CSVs and summary.
ownership-graph *FLAGS:
    uv run python scripts/build_ownership_graph.py {{FLAGS}}

# Build source-backed weak-link candidates from capital exposure and physical risk.
weak-links *FLAGS:
    uv run python scripts/build_weak_links.py {{FLAGS}}

# Build source-backed human-review queue from capital, weak-link, physical, and compute blockers.
review-queue *FLAGS:
    uv run python scripts/build_review_queue.py {{FLAGS}}

# Build source-backed quarter timing signals for crack-window triage.
timing-signals *FLAGS:
    uv run python scripts/build_timing_signals.py {{FLAGS}}

# Normalize acquired PPA source rows into source-backed deal evidence.
ppa-deals *FLAGS:
    uv run python scripts/extract_ppa_deals.py {{FLAGS}}

# Normalize acquired project tracker rows into source-backed physical project evidence.
tracker-projects *FLAGS:
    uv run python scripts/extract_tracker_projects.py {{FLAGS}}

# Extract source-backed compute economics rows from acquired EDGAR documents.
compute-economics *FLAGS:
    uv run python scripts/extract_compute_economics.py {{FLAGS}}

# Acquire public GPU rental pricing snapshots into source-backed compute rows.
gpu-pricing *FLAGS:
    uv run python scripts/acquire_gpu_pricing.py {{FLAGS}}

# --- UI & Exploration ---
ui:
    uv run streamlit run src/bubble/ui/streamlit_app.py --server.port 8501

# Open Neo4j browser
neo4j:
    open http://localhost:7474 || xdg-open http://localhost:7474 || echo "Open http://localhost:7474 manually"

# --- Long-running / Continuous ---
daemon:
    @echo "Starting Prefect worker + scheduled flows (daily EDGAR delta, etc.)"
    uv run prefect deploy -n bubble-daily-edgar || echo "Define deployments first"
    uv run prefect worker start -p bubble-default

# --- Maintenance ---
clean:
    rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

reset-data:
    @echo "⚠️  This will DELETE all local Neo4j + MinIO + Postgres data for bubble."
    @read -p "Type 'YES' to continue: " ans && [ "$$ans" = "YES" ]
    docker compose down -v
    rm -rf neo4j_data neo4j_logs minio_data postgres_data prefect_data
    @echo "Data reset. Run 'just up && just bootstrap-neo4j' to start fresh."

# --- One-shot full demo (the 90-min vision) ---
demo: sync
    @echo "=== BUBBLE LOCAL DEMO (no Docker required) ==="
    @echo "Using high-fidelity in-memory graph + live SEC data + full red flag + stress engine"
    uv run python scripts/run_burry_report.py 0000789019
    @echo ""
    @echo "=== Launching UI (will use the same live data) ==="
    just ui

demo-local: demo

# One-command complete system demo (recommended)
full-demo:
    @echo "=== BUBBLE COMPLETE END-TO-END DEMO ==="
    uv run python scripts/run_burry_report.py 0000789019   # Microsoft
    uv run python scripts/run_burry_report.py 0001018724   # Amazon
    uv run python scripts/run_burry_report.py 0001101239   # Equinix
    @echo ""
    @echo "=== Launching Forensic UI ==="
    uv run streamlit run src/bubble/ui/streamlit_app.py --server.port 8501

# Go Big Mode - aggressive high-volume build
gobig-demo:
    @echo "=== BUBBLE GO BIG MODE (800+ entities / 16k+ deals target) ==="
    uv run python scripts/bulk_ingest.py --limit 50
    uv run python scripts/run_burry_report.py 0000789019
    @echo ""
    @echo "=== Launching UI with scaled map ==="
    uv run streamlit run src/bubble/ui/streamlit_app.py --server.port 8501

# Evidence-gated Go Big report. This is not a final high-confidence answer until
# the evidence gate has measured, corroborated, and human-approved the key claims.
final-delivery:
    @echo "=== EVIDENCE-GATED BURRY REPORT (Go Big Mode) ==="
    uv run python scripts/generate_final_burry_report.py
    @echo ""
    @echo "Run 'uv run streamlit run src/bubble/ui/streamlit_app.py' to explore the full map."

# Full production demo (requires Docker + Neo4j running)
demo-prod: up sync bootstrap-neo4j
    @echo "=== FULL PRODUCTION DEMO (Neo4j + GDS) ==="
    uv run python scripts/run_burry_report.py 0000789019
    uv run streamlit run src/bubble/ui/streamlit_app.py --server.port 8501
