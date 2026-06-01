"""Generic source artifact acquisition from real source catalogs."""

from .catalog import (
    CatalogAcquisitionBatch,
    SourceArtifactRecord,
    SourceCatalogClient,
    SourceCatalogRow,
    acquire_source_catalog,
)
from .catalog_builder import SourceCatalogBuildSummary, build_seed_source_catalog

__all__ = [
    "CatalogAcquisitionBatch",
    "SourceArtifactRecord",
    "SourceCatalogBuildSummary",
    "SourceCatalogClient",
    "SourceCatalogRow",
    "acquire_source_catalog",
    "build_seed_source_catalog",
]
