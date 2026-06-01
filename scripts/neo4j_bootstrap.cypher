// =============================================================================
// BUBBLE Neo4j Schema Bootstrap
// Idempotent. Safe to re-run.
// =============================================================================

// --- Constraints (uniqueness + existence for forensic integrity) ---
CREATE CONSTRAINT entity_cik IF NOT EXISTS FOR (e:Entity) REQUIRE e.cik IS UNIQUE;
CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT deal_id IF NOT EXISTS FOR (d:Deal) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT risk_id IF NOT EXISTS FOR (r:Risk) REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT physical_id IF NOT EXISTS FOR (p:PhysicalAsset) REQUIRE p.id IS UNIQUE;

// --- Indexes for query performance (especially contagion & concentration) ---
CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name);
CREATE INDEX deal_type IF NOT EXISTS FOR (d:Deal) ON (d.deal_type);
CREATE INDEX risk_severity IF NOT EXISTS FOR (r:Risk) ON (r.severity);
CREATE INDEX risk_red_flag IF NOT EXISTS FOR (r:Risk) ON (r.red_flag_score);
CREATE INDEX deal_announced IF NOT EXISTS FOR (d:Deal) ON (d.announced_date);

// --- Full-text for entity search (nice for UI) ---
CREATE FULLTEXT INDEX entity_fulltext IF NOT EXISTS FOR (e:Entity) ON EACH [e.name, e.aliases];

// --- GDS projection example (for later contagion analysis) ---
// CALL gds.graph.project('exposure', 'Entity', {EXPOSED_TO: {orientation: 'UNDIRECTED'}})
// YIELD graphName, nodeCount, relationshipCount;

// Done. The Python client will add provenance-bearing nodes and relationships from acquired sources.
RETURN "Bubble Neo4j schema initialized successfully." AS status;
