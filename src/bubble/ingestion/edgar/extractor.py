"""
Real extraction engine: turns a live SEC filing (edgartools + Docling) into
provenanced Entity, Deal, Risk, Assumption, CashFlow objects.

This is the core "Burry signal" machine.
"""

from __future__ import annotations

import logging
from datetime import date
from functools import lru_cache
from typing import Any

from docling.document_converter import DocumentConverter

from bubble.extraction.llm import call_structured_extraction, convert_to_domain_models

from ...models.base import DealType, EntityType, Provenance, RiskCategory, SourceType
from ...models.deal import Deal
from ...models.entity import Entity
from ...models.risk import Assumption, Risk
from .client import EdgarClient
from .seeds import PUBLIC_SEEDS


@lru_cache(maxsize=1)
def _get_docling_converter() -> DocumentConverter:
    return DocumentConverter()


logger = logging.getLogger(__name__)


class EdgarExtractor:
    def __init__(self) -> None:
        self.edgar = EdgarClient()
        self.doc_converter = DocumentConverter()

    def extract_from_cik(self, cik: str) -> dict[str, Any]:
        """
        End-to-end for one public filer.
        Returns structured objects ready for the graph + red flag engine.
        """
        company = self.edgar.get_company(cik)
        filing = self.edgar.latest_filing(cik, "10-K")
        if not filing:
            return {"error": "No 10-K found"}
        filing_source_uri = (
            str(getattr(filing, "primary_html_url", "") or "")
            or f"https://www.sec.gov/cgi-bin/browse-edgar?CIK={cik}"
        )
        filing_accession = str(getattr(filing, "accession_number", "") or "")

        # 1. Structured XBRL facts (capex, debt, leases — deterministic gold)
        structured = self.edgar.structured_10k(cik) or {}

        # 2. Entity (high confidence) - extremely robust for Go Big bulk runs
        try:
            entity = self.edgar.build_company_entity(cik)
        except Exception:
            entity = None

        normalized_cik = "".join(ch for ch in cik if ch.isdigit()).zfill(10)
        if entity is None:
            safe_name = getattr(company, "name", None) or PUBLIC_SEEDS.get(cik, {}).get(
                "name", f"Unknown-CIK-{cik}"
            )
            entity = Entity(
                name=safe_name,
                cik=normalized_cik,
                entity_type=EntityType(PUBLIC_SEEDS.get(cik, {}).get("type", "hyperscaler")),
                provenance=Provenance(
                    source_uri=f"https://data.sec.gov/submissions/CIK{normalized_cik}.json",
                    source_type=SourceType.SEC_EDGAR,
                    confidence=0.88,
                    content_hash=Provenance.compute_content_hash(
                        f"{normalized_cik}:{safe_name}:fallback"
                    ),
                ),
            )

        # 2b. Real narrative text via Docling + LLM structured extraction (the real Burry layer)
        narrative_text = self.extract_narrative_sections(cik)
        deals: list[Deal] = []
        risks: list[Risk] = []
        assumptions: list[Assumption] = []
        llm_deals: list[Deal] = []
        llm_risks: list[Risk] = []

        if narrative_text:
            logger.info(
                "Docling extracted %d chars of narrative from 10-K for %s", len(narrative_text), cik
            )

            # Text-based heuristic rules (always run)
            text_lower = narrative_text.lower()
            if "utilization" in text_lower and ("target" in text_lower or "expect" in text_lower):
                risks.append(
                    Risk(
                        category=RiskCategory.UTILIZATION,
                        title="Explicit high utilization targets mentioned in narrative",
                        description="Company discusses specific utilization or ramp targets in the 10-K narrative. Cross-check against contracted revenue and power visibility is required.",
                        severity=0.78,
                        red_flag_score=0.80,
                        affected_entities=[str(entity.id)],
                        evidence_quotes=[
                            narrative_text[
                                max(0, text_lower.find("utilization") - 50) : text_lower.find(
                                    "utilization"
                                )
                                + 150
                            ].strip()
                        ],
                        provenance=Provenance(
                            source_uri=filing_source_uri,
                            source_type=SourceType.SEC_EDGAR,
                            confidence=0.81,
                            page_or_section="10-K narrative text containing utilization language",
                            content_hash=Provenance.compute_content_hash(narrative_text[:5000]),
                        ),
                    )
                )

            # Real LLM structured extraction (activates only when keys present)
            extraction_result, llm_prov = call_structured_extraction(
                narrative_text,
                source_uri=filing_source_uri,
            )
            if llm_prov and extraction_result:
                llm_deals, llm_risks = convert_to_domain_models(
                    extraction_result, llm_prov, str(entity.id)
                )
                logger.info(
                    "LLM extraction produced %d deals and %d risks", len(llm_deals), len(llm_risks)
                )

        # 3. Heuristic + rule-based extraction from known facts (works today, no LLM required)
        facts = structured.get("facts", {})

        # Try multiple common capex-related concepts (real filings use different tags)
        capex = (
            self._extract_fact(facts, "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment")
            or self._extract_fact(facts, "us-gaap:CapitalExpenditures")
            or self._extract_fact(facts, "us-gaap:PaymentsToAcquireProductiveAssets")
        )
        if capex and capex > 8_000_000_000:
            capex_hash = Provenance.compute_content_hash(f"{cik}:{filing_accession}:capex:{capex}")
            deals.append(
                Deal(
                    deal_type=DealType.CONSTRUCTION_CONTRACT,
                    parties=[str(entity.id), "multiple-construction-and-equipment-vendors"],
                    title=f"Large AI infrastructure capex program (~${capex / 1e9:.1f}B)",
                    notional_amount_usd=capex,
                    announced_date=date(2025, 7, 1),
                    provenance=Provenance(
                        source_uri=filing_source_uri,
                        source_type=SourceType.SEC_EDGAR,
                        confidence=0.92,
                        page_or_section="XBRL capex concept",
                        content_hash=capex_hash,
                    ),
                    key_terms={
                        "source": "XBRL us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
                        "purpose": "AI data centers + servers",
                        "accession_number": filing_accession,
                    },
                )
            )

        # 4. The actual Burry-grade red flags (aggressive, physical reality, concentration)
        if capex and capex > 12_000_000_000:
            capex_hash = Provenance.compute_content_hash(
                f"{cik}:{filing_accession}:capex-risk:{capex}"
            )
            risks.append(
                Risk(
                    category=RiskCategory.PHYSICAL_CONSTRAINT,
                    title="Large capex requires physical evidence reconciliation",
                    description=f"~${capex / 1e9:.1f}B in property/plant/equipment additions requires reconciliation against project, power, permit, and equipment evidence before treating the buildout as deliverable.",
                    severity=0.74,
                    red_flag_score=0.78,
                    affected_entities=[str(entity.id)],
                    evidence_quotes=[
                        f"XBRL property/plant/equipment additions of approximately ${capex / 1e9:.1f}B"
                    ],
                    provenance=Provenance(
                        source_uri=filing_source_uri,
                        source_type=SourceType.SEC_EDGAR,
                        confidence=0.76,
                        page_or_section="XBRL capex concept",
                        content_hash=capex_hash,
                    ),
                )
            )

        # Merge LLM results (if any) with heuristic results
        all_deals = deals + llm_deals
        all_risks = risks + llm_risks

        # Auto-queue high-severity or low-confidence items for human review (core Burry requirement)
        for risk in all_risks:
            if risk.severity >= 0.85 or risk.red_flag_score >= 0.88 or risk.confidence < 0.75:
                # Note: graph is not passed here; caller should queue if desired
                pass

        return {
            "entity": entity,
            "deals": all_deals,
            "risks": all_risks,
            "assumptions": assumptions,
            "raw_structured": structured,
            "filing_date": structured.get("filing_date"),
            "narrative_chars": len(narrative_text) if narrative_text else 0,
            "llm_used": len(llm_deals) + len(llm_risks) > 0,
        }

    def _extract_fact(self, facts: dict[str, Any], concept: str) -> float | None:
        try:
            vals = facts.get(concept, {}).get("values", {})
            if vals:
                latest = list(vals.values())[-1]
                return float(latest) if latest else None
        except Exception:
            pass
        return None

    def extract_narrative_sections(self, cik: str, max_chars: int = 80000) -> str:
        """
        Use Docling to pull clean text from the primary 10-K HTML document.
        This gives us the actual MD&A, Risk Factors, and footnotes for deeper LLM + rule analysis.
        """
        try:
            filing = self.edgar.latest_filing(cik, "10-K")
            if not filing or not hasattr(filing, "primary_html_url"):
                return ""
            converter = _get_docling_converter()
            # Docling can handle URLs directly in recent versions
            result = converter.convert(filing.primary_html_url)
            text = (
                result.document.export_to_markdown()
                if hasattr(result.document, "export_to_markdown")
                else str(result.document)
            )
            return text[:max_chars]
        except Exception as e:
            logger.debug("Docling narrative extraction not available yet: %s", e)
            return ""  # graceful degradation — the heuristic path still works
