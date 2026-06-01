"""Source-data invariants for production ingestion paths."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from bubble.models.base import Provenance, SourceType

if TYPE_CHECKING:
    from collections.abc import Mapping

BLOCKED_SOURCE_URI_PREFIXES = (
    "model:inferred_estimate:",
    "seed:",
    "demo:",
    "sample:",
    "mock:",
    "dummy:",
    "placeholder:",
)
BLOCKED_SOURCE_URI_VALUES = {"", "unknown", "n/a", "na", "none", "null", "test", "fake"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class SourceDataInvariantError(ValueError):
    """Raised when production source data violates forensic data-quality rules."""


def assert_production_provenance(provenance: Provenance, *, context: str) -> None:
    """Reject non-source-backed provenance in production data paths."""

    if provenance.source_type == SourceType.INFERRED:
        raise SourceDataInvariantError(
            f"{context} uses inferred provenance; production source data must be source-backed."
        )
    _assert_source_uri_allowed(provenance.source_uri, context=context)
    _assert_content_hash_allowed(provenance.content_hash, context=context)


def assert_source_row(row: Mapping[str, str], *, context: str) -> None:
    """Reject non-source-backed CSV/source rows before they become domain objects."""

    source_type = (row.get("source_type") or "").strip().lower()
    if source_type == SourceType.INFERRED.value:
        raise SourceDataInvariantError(
            f"{context} row uses inferred source_type; production source data must be source-backed."
        )
    _assert_source_uri_allowed(row.get("source_uri", ""), context=context)


def is_source_backed_row(row: Mapping[str, str]) -> bool:
    """Return whether a row is eligible to count as source-backed production evidence."""

    try:
        assert_source_row(row, context="source-row")
    except SourceDataInvariantError:
        return False
    return True


def _assert_source_uri_allowed(source_uri: str, *, context: str) -> None:
    normalized = source_uri.strip().lower()
    if normalized in BLOCKED_SOURCE_URI_VALUES:
        raise SourceDataInvariantError(
            f"{context} source_uri is required for production source data."
        )
    if any(normalized.startswith(prefix) for prefix in BLOCKED_SOURCE_URI_PREFIXES):
        raise SourceDataInvariantError(
            f"{context} source_uri is not allowed in production source data: {source_uri}"
        )


def _assert_content_hash_allowed(content_hash: str, *, context: str) -> None:
    normalized = content_hash.strip().lower()
    if not SHA256_RE.fullmatch(normalized):
        raise SourceDataInvariantError(f"{context} content_hash must be a SHA-256 hex digest.")
