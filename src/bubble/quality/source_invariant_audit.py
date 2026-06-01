"""Repository-wide source provenance audit helpers."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bubble.quality.source_invariants import SourceDataInvariantError, assert_source_row

URI_FIELDS = ("source_uri", "provenance_source_uri", "filing_url")
URI_LIST_FIELDS = ("source_uris",)
HASH_FIELDS = ("content_hash", "provenance_content_hash", "content_hashes")
RETRIEVAL_TIME_FIELDS = ("retrieved_at", "downloaded_at")
DIRECT_ACQUISITION_PARTS = (
    ("source_acquisition", "source_rows"),
    ("source_acquisition", "source_artifact_inventory.csv"),
    ("edgar_acquisition", "edgar_document_inventory.csv"),
    ("compute", "gpu_price_source_artifacts.csv"),
)


@dataclass(frozen=True)
class SourceInvariantFinding:
    """One source/provenance audit finding."""

    path: str
    row_number: int
    field: str
    value: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SourceInvariantAudit:
    """Summary of a repository-wide source/provenance audit."""

    generated_at: str
    data_dirs: list[str]
    files_scanned: int
    rows_scanned: int
    rows_with_source_uri: int
    source_uri_values_checked: int
    violations: list[SourceInvariantFinding]
    warnings: list[SourceInvariantFinding]

    @property
    def passed(self) -> bool:
        return not self.violations

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "data_dirs": self.data_dirs,
            "files_scanned": self.files_scanned,
            "rows_scanned": self.rows_scanned,
            "rows_with_source_uri": self.rows_with_source_uri,
            "source_uri_values_checked": self.source_uri_values_checked,
            "violations": [finding.to_dict() for finding in self.violations],
            "warnings": [finding.to_dict() for finding in self.warnings],
            "violation_count": len(self.violations),
            "warning_count": len(self.warnings),
            "passed": self.passed,
        }


def audit_source_invariants(
    data_dirs: list[str | Path],
    *,
    max_findings: int = 500,
) -> SourceInvariantAudit:
    """Scan production CSV outputs for blocked source URIs and provenance gaps."""

    roots = [Path(data_dir) for data_dir in data_dirs]
    csv_paths = _csv_paths(roots)
    files_scanned = 0
    rows_scanned = 0
    rows_with_source_uri = 0
    source_uri_values_checked = 0
    violations: list[SourceInvariantFinding] = []
    warnings: list[SourceInvariantFinding] = []

    for path in csv_paths:
        files_scanned += 1
        direct_acquisition = _is_direct_acquisition_output(path)
        source_catalog = _is_source_catalog(path)
        with path.open(newline="") as f:
            reader = csv.DictReader(f)
            for row_number, row in enumerate(reader, start=2):
                rows_scanned += 1
                normalized = {key: (value or "").strip() for key, value in row.items()}
                uri_values = _row_uri_values(normalized)
                if uri_values:
                    rows_with_source_uri += 1
                elif _requires_source_uri(normalized):
                    _append_finding(
                        violations,
                        SourceInvariantFinding(
                            path=str(path),
                            row_number=row_number,
                            field="source_uri",
                            value="",
                            message="Row has source/provenance columns but no source URI value.",
                        ),
                        max_findings=max_findings,
                    )

                for field, value in uri_values:
                    source_uri_values_checked += 1
                    try:
                        assert_source_row(
                            {
                                "source_uri": value,
                                "source_type": normalized.get("source_type", ""),
                            },
                            context=f"{path}:{row_number}:{field}",
                        )
                    except SourceDataInvariantError as exc:
                        _append_finding(
                            violations,
                            SourceInvariantFinding(
                                path=str(path),
                                row_number=row_number,
                                field=field,
                                value=value,
                                message=str(exc),
                            ),
                            max_findings=max_findings,
                        )

                if uri_values and not source_catalog:
                    _check_hash_and_timestamp(
                        path=path,
                        row=normalized,
                        row_number=row_number,
                        direct_acquisition=direct_acquisition,
                        violations=violations,
                        warnings=warnings,
                        max_findings=max_findings,
                    )

    return SourceInvariantAudit(
        generated_at=datetime.now(UTC).isoformat(),
        data_dirs=[str(root) for root in roots],
        files_scanned=files_scanned,
        rows_scanned=rows_scanned,
        rows_with_source_uri=rows_with_source_uri,
        source_uri_values_checked=source_uri_values_checked,
        violations=violations,
        warnings=warnings,
    )


def write_source_invariant_audit(audit: SourceInvariantAudit, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit.to_dict(), indent=2, sort_keys=True))
    return output


def _csv_paths(roots: list[Path]) -> list[Path]:
    paths: list[Path] = []
    for root in roots:
        if root.exists():
            paths.extend(path for path in root.rglob("*.csv") if path.is_file())
    return sorted(paths)


def _row_uri_values(row: dict[str, str]) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    for field in URI_FIELDS:
        value = row.get(field, "")
        if value:
            values.append((field, value))
    for field in URI_LIST_FIELDS:
        values.extend((field, value) for value in _split_uri_list(row.get(field, "")))
    return values


def _split_uri_list(raw: str) -> list[str]:
    text = raw.strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            loaded = json.loads(text)
        except json.JSONDecodeError:
            loaded = None
        if isinstance(loaded, list):
            return [str(item).strip() for item in loaded if str(item).strip()]
    separators = ["|", ";"]
    values = [text]
    for separator in separators:
        if separator in text:
            values = [item.strip() for item in text.split(separator)]
            break
    return [value for value in values if value]


def _requires_source_uri(row: dict[str, str]) -> bool:
    return any(field in row for field in (*URI_FIELDS, *URI_LIST_FIELDS))


def _check_hash_and_timestamp(
    *,
    path: Path,
    row: dict[str, str],
    row_number: int,
    direct_acquisition: bool,
    violations: list[SourceInvariantFinding],
    warnings: list[SourceInvariantFinding],
    max_findings: int,
) -> None:
    missing_hash = not any(row.get(field, "").strip() for field in HASH_FIELDS if field in row)
    missing_timestamp = not any(
        row.get(field, "").strip() for field in RETRIEVAL_TIME_FIELDS if field in row
    )
    target = violations if direct_acquisition else warnings

    if missing_hash:
        _append_finding(
            target,
            SourceInvariantFinding(
                path=str(path),
                row_number=row_number,
                field="content_hash",
                value="",
                message="Row has source URI evidence but no content hash field/value.",
            ),
            max_findings=max_findings,
        )
    if direct_acquisition and missing_timestamp:
        _append_finding(
            violations,
            SourceInvariantFinding(
                path=str(path),
                row_number=row_number,
                field="retrieved_at",
                value="",
                message="Direct acquisition row has no retrieval/download timestamp.",
            ),
            max_findings=max_findings,
        )


def _append_finding(
    findings: list[SourceInvariantFinding],
    finding: SourceInvariantFinding,
    *,
    max_findings: int,
) -> None:
    if len(findings) < max_findings:
        findings.append(finding)


def _is_direct_acquisition_output(path: Path) -> bool:
    parts = path.parts
    return any(all(part in parts for part in required) for required in DIRECT_ACQUISITION_PARTS)


def _is_source_catalog(path: Path) -> bool:
    return path.name.startswith("source_catalog")
