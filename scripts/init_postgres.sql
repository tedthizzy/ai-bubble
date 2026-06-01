-- BUBBLE Postgres bootstrap (operational metadata, adjudication queues, audit)
-- Runs automatically on first `docker compose up` for postgres service.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Raw document / filing cache metadata
CREATE TABLE IF NOT EXISTS raw_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_hash TEXT UNIQUE NOT NULL,
    source_uri TEXT NOT NULL,
    source_type TEXT NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    size_bytes BIGINT,
    mime_type TEXT,
    s3_key TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Ingestion / extraction jobs (for Prefect + operational tracking)
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type TEXT NOT NULL,           -- 'edgar_delta', 'full_revalidate', 'satellite_change', etc.
    entity_id TEXT,
    status TEXT NOT NULL,             -- 'queued', 'running', 'succeeded', 'failed', 'partial'
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    error TEXT,
    stats JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- LLM adjudication queue (core materiality gate)
CREATE TABLE IF NOT EXISTS review_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_type TEXT NOT NULL,          -- 'Deal', 'Risk', 'Assumption', 'Entity'
    node_id TEXT NOT NULL,
    reason TEXT NOT NULL,             -- 'low_confidence', 'verifier_disagreement', 'high_impact_red_flag', 'new_major_entity'
    confidence DOUBLE PRECISION,
    priority INTEGER DEFAULT 100,
    status TEXT DEFAULT 'pending',    -- 'pending', 'approved', 'overridden', 'rejected'
    assigned_to TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    UNIQUE (node_type, node_id)
);

-- Full audit / decision log (immutable append-only for every material conclusion)
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ DEFAULT now(),
    actor TEXT NOT NULL,              -- 'llm:claude-4', 'operator:ted', 'rule:concentration_check_v1'
    action TEXT NOT NULL,
    subject_type TEXT,
    subject_id TEXT,
    before JSONB,
    after JSONB,
    provenance JSONB,
    correlation_id UUID
);

CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts DESC);
CREATE INDEX IF NOT EXISTS idx_audit_subject ON audit_log(subject_type, subject_id);
CREATE INDEX IF NOT EXISTS idx_review_status_priority ON review_queue(status, priority DESC);

-- Scenario run history (for reproducibility & backtesting)
CREATE TABLE IF NOT EXISTS scenario_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_or_deal_id TEXT NOT NULL,
    scenario_name TEXT NOT NULL,      -- 'base', 'adverse', 'severe', 'tail_gpu_depreciation'
    parameters JSONB,
    results JSONB,
    red_flags JSONB,
    run_by TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE review_queue IS 'Core LLM adjudication gate. Low-confidence or high-stakes extractions land here for forensic adjudication.';
COMMENT ON TABLE audit_log IS 'Complete decision lineage. Every LLM call, rule firing, operator override, and graph mutation is recorded.';
