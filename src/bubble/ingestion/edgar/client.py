"""
EDGAR ingestion client for bubble — built on the excellent edgartools library.

This is the primary automated source for public company disclosures (10-K, 10-Q, 8-K, etc.).
"""

from __future__ import annotations

import logging
import os
from typing import Any

from edgar import Company, set_identity  # type: ignore

from ...config import settings
from ...models.base import EntityType, Provenance, SourceType
from ...models.entity import Entity

logger = logging.getLogger(__name__)

# SEC requires a proper User-Agent for all automated access (legal requirement).
# Set a professional identity once at import.
_IDENTITY = os.getenv(
    "EDGAR_IDENTITY", "bubble-forensic-research/0.1 (contact: your-email@example.com)"
)
set_identity(_IDENTITY)
logger.info("edgartools identity set to: %s", _IDENTITY)


class EdgarClient:
    """Thin, production-friendly wrapper around edgartools."""

    def __init__(self) -> None:
        self.watchlist = settings.watchlist_ciks

    def get_company(self, cik: str) -> Company:
        """Return an edgartools Company object (handles normalization)."""
        return Company(cik)

    def latest_filing(self, cik: str, form: str = "10-K") -> Any | None:
        """Get the most recent filing of a given form type."""
        company = self.get_company(cik)
        filings = company.get_filings(form=form)
        if filings:
            latest = filings.latest()
            logger.info("Latest %s for %s: %s", form, cik, latest)
            return latest
        return None

    def structured_10k(self, cik: str) -> dict[str, Any] | None:
        """
        Return the rich structured object from edgartools (XBRL facts + sections).
        This is gold for capex, debt, lease commitments, etc. without LLM.
        """
        filing = self.latest_filing(cik, "10-K")
        if filing and hasattr(filing, "obj"):
            try:
                obj = filing.obj()
                return {
                    "company": obj.company,
                    "facts": getattr(obj, "facts", {}),
                    "financials": getattr(obj, "financials", None),
                    "filing_date": str(getattr(filing, "filing_date", "")),
                    "accession": getattr(filing, "accession_number", ""),
                }
            except Exception as e:
                logger.exception("Failed to parse structured 10-K for %s: %s", cik, e)
        return None

    def build_company_entity(self, cik: str) -> Entity | None:
        """Create a high-confidence Entity from EDGAR company metadata."""
        try:
            normalized_cik = "".join(ch for ch in cik if ch.isdigit()).zfill(10)
            company = self.get_company(cik)
            prov = Provenance(
                source_uri=f"https://data.sec.gov/submissions/CIK{normalized_cik}.json",
                source_type=SourceType.SEC_EDGAR,
                confidence=0.98,
                content_hash=Provenance.compute_content_hash(
                    f"{normalized_cik}:{company.name}:{getattr(company, 'ticker', '')}"
                ),
            )
            return Entity(
                name=company.name,
                cik=normalized_cik,
                ticker=getattr(company, "ticker", None),
                entity_type=EntityType.HYPERSCALER,  # will be refined later
                provenance=prov,
                confidence=0.98,
            )
        except Exception as e:
            logger.warning("Could not build seed entity for CIK %s: %s", cik, e)
            return None


# Quick CLI entry for `just ingest-cik ...`
if __name__ == "__main__":
    import sys

    client = EdgarClient()
    if len(sys.argv) > 1 and sys.argv[1] == "ingest":
        cik = sys.argv[2] if len(sys.argv) > 2 else "0000789019"
        print(f"Ingesting CIK {cik} (stub — full pipeline coming in next iteration)")
        ent = client.build_company_entity(cik)
        if ent:
            print(ent)
        struct = client.structured_10k(cik)
        if struct:
            print("Structured 10-K keys:", list(struct.keys())[:5])
    else:
        print("EdgarClient ready. Try: python -m bubble.ingestion.edgar.client ingest 0000789019")
