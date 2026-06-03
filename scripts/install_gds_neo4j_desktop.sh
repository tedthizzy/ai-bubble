#!/usr/bin/env bash
# Install Neo4j Graph Data Science (GDS) into the running Neo4j Desktop instance.
# Idempotent + safe: backs up neo4j.conf, skips an already-present jar, restarts
# the DBMS using Desktop's bundled JRE. Version-matched: GDS 2026.05.0 <-> Neo4j 2026.05.0.
set -euo pipefail

DBMS="$HOME/Library/Application Support/neo4j-desktop/Application/Data/dbmss/dbms-ac7a503c-b68a-40d3-8ca7-9e9d4ea604a4"
JAVA_HOME="$HOME/Library/Application Support/neo4j-desktop/Application/Cache/runtime/zulu21.48.17-ca-jre21.0.10-macosx_aarch64"
GDS_VERSION="2026.05.0"
GDS_URL="https://graphdatascience.ninja/neo4j-graph-data-science-${GDS_VERSION}.jar"
CONF="$DBMS/conf/neo4j.conf"
PLUGINS="$DBMS/plugins"
export JAVA_HOME
export PATH="$JAVA_HOME/bin:$PATH"

echo "==> 1/4 Download GDS ${GDS_VERSION} jar (idempotent)"
if ls "$PLUGINS"/neo4j-graph-data-science-*.jar >/dev/null 2>&1; then
  echo "    jar already present, skipping download"
else
  curl -fSL "$GDS_URL" -o "$PLUGINS/neo4j-graph-data-science-${GDS_VERSION}.jar"
  echo "    downloaded $(du -h "$PLUGINS/neo4j-graph-data-science-${GDS_VERSION}.jar" | cut -f1)"
fi

echo "==> 2/4 Patch neo4j.conf (backup + append GDS procedure allowlist if absent)"
if grep -q '^dbms.security.procedures.unrestricted=gds' "$CONF"; then
  echo "    procedures already configured, skipping"
else
  cp "$CONF" "$CONF.bak.$(date +%s 2>/dev/null || echo backup)"
  {
    echo ""
    echo "# --- GDS plugin (added by install_gds_neo4j_desktop.sh) ---"
    echo "dbms.security.procedures.unrestricted=gds.*,apoc.*"
    echo "dbms.security.procedures.allowlist=gds.*,apoc.*"
  } >> "$CONF"
  echo "    appended procedure settings (backup saved)"
fi

echo "==> 3/4 Restart Neo4j (bundled JRE)"
# Enterprise via CLI needs explicit license acceptance (Desktop's launcher does this for us).
# Evaluation = the local-dev terms Desktop already runs this instance under.
"$DBMS/bin/neo4j-admin" server license --accept-evaluation 2>/dev/null || true
"$DBMS/bin/neo4j" restart || "$DBMS/bin/neo4j" start || true

echo "==> 4/4 Wait for bolt + verify gds.version()"
set +x
# shellcheck disable=SC1090
NEO4J_PASSWORD="$(grep '^NEO4J_PASSWORD=' "$HOME/Documents/dev-archive/bubble/.env" | cut -d= -f2-)"
export NEO4J_USERNAME=neo4j NEO4J_PASSWORD
for i in $(seq 1 30); do
  if "$DBMS/bin/cypher-shell" -a bolt://127.0.0.1:7687 "RETURN gds.version() AS gds;" 2>/dev/null; then
    echo "==> GDS is live."
    exit 0
  fi
  sleep 3
done
echo "!! GDS verify did not return in time; check Neo4j Desktop status / logs."
exit 1
