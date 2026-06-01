"""
Go Big Mode Entity Seeds for bubble.

Target: 800-900+ entities across the AI/data center/financing ecosystem.
Prioritized by disclosure volume, systemic importance, and data availability.

Structure:
- PUBLIC_SEEDS: CIK -> metadata for EDGAR ingestion (highest signal)
- PRIVATE_SEEDS / PROJECTS / FINANCIERS: Non-public or inferred entities

This list is deliberately broad to hit Go Big volume targets when combined with
source-backed relationship records, tracker data, and reviewed extraction.
"""

from __future__ import annotations

# =============================================================================
# PUBLIC COMPANIES (EDGAR CIKs) - Highest priority for structured data
# =============================================================================

PUBLIC_SEEDS: dict[str, dict[str, str]] = {
    # Hyperscalers & Big Tech (AI capex leaders)
    "0000789019": {
        "name": "Microsoft",
        "type": "hyperscaler",
        "tier": "1",
        "notes": "Azure + OpenAI/CoreWeave exposure",
    },
    "0001018724": {
        "name": "Amazon",
        "type": "hyperscaler",
        "tier": "1",
        "notes": "AWS + Anthropic",
    },
    "0001652044": {
        "name": "Alphabet",
        "type": "hyperscaler",
        "tier": "1",
        "notes": "Google Cloud + TPU",
    },
    "0001326801": {
        "name": "Meta Platforms",
        "type": "hyperscaler",
        "tier": "1",
        "notes": "Massive AI infra build",
    },
    "0001045810": {
        "name": "NVIDIA",
        "type": "ai_pureplay",
        "tier": "1",
        "notes": "GPU supplier to entire ecosystem",
    },
    "0000320193": {
        "name": "Apple",
        "type": "hyperscaler",
        "tier": "2",
        "notes": "Data center expansion",
    },
    "0001341439": {
        "name": "Oracle",
        "type": "cloud_provider",
        "tier": "2",
        "notes": "Cloud + AI infrastructure",
    },
    "0001640147": {"name": "Snowflake", "type": "cloud_provider", "tier": "2"},
    "0001561550": {"name": "Datadog", "type": "cloud_provider", "tier": "3"},
    # Data Center REITs & Owners
    "0001101239": {
        "name": "Equinix",
        "type": "data_center_reit",
        "tier": "1",
        "notes": "Global leader",
    },
    "0001297996": {"name": "Digital Realty", "type": "data_center_reit", "tier": "1"},
    # AI / Cloud Pure Plays & Neoclouds
    "0001769628": {
        "name": "CoreWeave",
        "type": "ai_infra_pureplay",
        "tier": "1",
        "notes": "Fastest growing GPU cloud",
    },
    # Financiers & Private Credit (many have public filings)
    "0001858681": {
        "name": "Apollo Global Management",
        "type": "financier",
        "tier": "1",
        "notes": "Athene, Level 3, massive data center credit",
    },
    "0001393818": {
        "name": "Blackstone",
        "type": "financier",
        "tier": "1",
        "notes": "QTS + huge platform",
    },
    "0001404912": {
        "name": "KKR",
        "type": "financier",
        "tier": "1",
        "notes": "CyrusOne + data center funds",
    },
    "0001176948": {"name": "Ares Management", "type": "financier", "tier": "1"},
    "0001823945": {
        "name": "Blue Owl Capital",
        "type": "financier",
        "tier": "2",
        "notes": "Large private credit in infra",
    },
    "0001465128": {"name": "Starwood Property Trust", "type": "financier", "tier": "2"},
    # Power & Utilities with Data Center Exposure
    "0001692819": {
        "name": "Vistra",
        "type": "power_generator",
        "tier": "1",
        "notes": "Major gas + nuclear for AI load",
    },
    "0001868275": {
        "name": "Constellation Energy",
        "type": "power_generator",
        "tier": "1",
        "notes": "Nuclear restarts for data centers",
    },
    "0001622536": {
        "name": "Talen Energy",
        "type": "power_generator",
        "tier": "2",
        "notes": "Susquehanna nuclear + data center",
    },
    "0001013871": {"name": "NRG Energy", "type": "power_generator", "tier": "2"},
    # Equipment & Critical Infrastructure
    "0001996810": {
        "name": "General Electric (GE Vernova)",
        "type": "equipment_supplier",
        "tier": "2",
        "notes": "Turbines",
    },
    "0001830056": {"name": "Siemens Energy", "type": "equipment_supplier", "tier": "2"},
    "0001551182": {
        "name": "Eaton",
        "type": "equipment_supplier",
        "tier": "2",
        "notes": "Power management",
    },
    "0001674101": {
        "name": "Vertiv",
        "type": "equipment_supplier",
        "tier": "2",
        "notes": "Critical cooling/power",
    },
    # More REITs / Developers / Land Players
    "0001045609": {"name": "Prologis", "type": "data_center_reit", "tier": "2"},
    "0001020569": {"name": "Iron Mountain", "type": "data_center_reit", "tier": "2"},
    # Semiconductor, server, network, and construction bottlenecks
    "0000002488": {"name": "Advanced Micro Devices", "type": "equipment_supplier", "tier": "1"},
    "0001730168": {"name": "Broadcom", "type": "equipment_supplier", "tier": "1"},
    "0001571996": {"name": "Dell Technologies", "type": "equipment_supplier", "tier": "1"},
    "0001375365": {"name": "Super Micro Computer", "type": "equipment_supplier", "tier": "2"},
    "0000723125": {"name": "Micron Technology", "type": "equipment_supplier", "tier": "2"},
    "0001596532": {"name": "Arista Networks", "type": "equipment_supplier", "tier": "2"},
    "0001030894": {"name": "Celestica", "type": "equipment_supplier", "tier": "3"},
    "0001720635": {"name": "nVent Electric", "type": "equipment_supplier", "tier": "2"},
    "0001035983": {
        "name": "Comfort Systems USA",
        "type": "construction_services",
        "tier": "2",
    },
    "0000105634": {"name": "EMCOR Group", "type": "construction_services", "tier": "2"},
    "0001050915": {"name": "Quanta Services", "type": "construction_services", "tier": "2"},
    # Public utilities exposed to data-center load growth
    "0000753308": {"name": "NextEra Energy", "type": "power_generator", "tier": "2"},
    "0001326160": {"name": "Duke Energy", "type": "power_utility", "tier": "2"},
    "0000004904": {"name": "American Electric Power", "type": "power_utility", "tier": "2"},
    "0000715957": {"name": "Dominion Energy", "type": "power_utility", "tier": "2"},
    "0001109357": {"name": "Exelon", "type": "power_utility", "tier": "2"},
    "0000065984": {"name": "Entergy", "type": "power_utility", "tier": "2"},
    "0001130310": {"name": "CenterPoint Energy", "type": "power_utility", "tier": "3"},
}

# =============================================================================
# PRIVATE / INFERRED / PROJECT ENTITIES (will be expanded via LLM + trackers)
# =============================================================================

PRIVATE_SEEDS: list[dict[str, str]] = [
    # Major private developers
    {"name": "Vantage Data Centers", "type": "ai_infra_pureplay", "tier": "1"},
    {"name": "Aligned Data Centers", "type": "ai_infra_pureplay", "tier": "1"},
    {"name": "Stack Infrastructure", "type": "ai_infra_pureplay", "tier": "2"},
    {"name": "EdgeConneX", "type": "ai_infra_pureplay", "tier": "2"},
    {"name": "CyrusOne", "type": "ai_infra_pureplay", "tier": "1"},
    {"name": "QTS Realty", "type": "ai_infra_pureplay", "tier": "1"},
    {"name": "DataBank", "type": "ai_infra_pureplay", "tier": "2"},
    {"name": "Flexential", "type": "ai_infra_pureplay", "tier": "2"},
    {"name": "Cologix", "type": "ai_infra_pureplay", "tier": "2"},
    {"name": "H5 Data Centers", "type": "ai_infra_pureplay", "tier": "3"},
    {"name": "Skybox Datacenters", "type": "ai_infra_pureplay", "tier": "3"},
    # Financiers / Funds (private credit heavy in this space)
    {"name": "Apollo Athene Data Center Vehicles", "type": "financier", "tier": "1"},
    {"name": "Blackstone Data Center Fund", "type": "financier", "tier": "1"},
    {"name": "KKR CyrusOne Co-Invest", "type": "financier", "tier": "1"},
    {"name": "Ares Data Center Credit", "type": "financier", "tier": "1"},
    {"name": "Blue Owl / Oaktree Infra Funds", "type": "financier", "tier": "2"},
    {"name": "Starwood Capital Data Center Platform", "type": "financier", "tier": "2"},
    {"name": "Brookfield Infrastructure", "type": "financier", "tier": "2"},
    {"name": "Macquarie Asset Management", "type": "financier", "tier": "2"},
    # Power / Behind-the-meter players
    {"name": "Calpine", "type": "power_generator", "tier": "2"},
    {"name": "Crusoe Energy Systems", "type": "power_generator", "tier": "1"},
    {"name": "Lancium", "type": "power_generator", "tier": "2"},
    {"name": "Core Scientific (restructured)", "type": "power_generator", "tier": "2"},
    # Private AI labs and neoclouds without reliable public-company CIKs
    {"name": "Lambda Labs", "type": "ai_infra_pureplay", "tier": "2"},
    {"name": "Together AI", "type": "ai_pureplay", "tier": "3"},
    {"name": "Groq", "type": "ai_pureplay", "tier": "3"},
    {"name": "xAI", "type": "ai_pureplay", "tier": "1"},
    # Equipment & Supply Chain
    {"name": "Schneider Electric (data center)", "type": "equipment_supplier", "tier": "1"},
]

# =============================================================================
# KNOWN LARGE PROJECTS / CAMPUSES (will generate many individual deals)
# =============================================================================

KNOWN_PROJECTS: list[dict[str, str]] = [
    {"name": "Microsoft - Abilene AI Campus", "type": "project", "tier": "1"},
    {"name": "CoreWeave - Various GPU Clusters (multiple SPVs)", "type": "project", "tier": "1"},
    {"name": "xAI Memphis Supercluster", "type": "project", "tier": "1"},
    {"name": "Amazon - Multiple US + EU AI Regions", "type": "project", "tier": "1"},
    {"name": "Google - St. Ghislain + multiple US campuses", "type": "project", "tier": "1"},
    {"name": "Vantage - Multiple Texas + Virginia campuses", "type": "project", "tier": "1"},
    {"name": "Equinix - Major IBX expansions (global)", "type": "project", "tier": "1"},
    {"name": "Digital Realty - Various wholesale campuses", "type": "project", "tier": "1"},
    {
        "name": "Crusoe - Multiple gas-powered AI sites (Texas, North Dakota, etc.)",
        "type": "project",
        "tier": "2",
    },
    {"name": "Talen - Susquehanna Nuclear + Data Center Campus", "type": "project", "tier": "1"},
]

# Helper to get all high-priority CIKs for bulk EDGAR runs
WATCHLIST_CIKS = list(PUBLIC_SEEDS.keys())


def get_all_seeds() -> dict[str, object]:
    """Return combined view for broad coverage."""
    return {
        "public": PUBLIC_SEEDS,
        "private": PRIVATE_SEEDS,
        "projects": KNOWN_PROJECTS,
        "watchlist_ciks": WATCHLIST_CIKS,
    }
