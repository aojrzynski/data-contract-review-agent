"""Typed models shared by intake, validation, reporting, and tests.

These dataclasses are intentionally small and explicit so every pipeline stage
can exchange the same structures without hidden behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


# Supported contract vocabulary for v1 logical type declarations.
SUPPORTED_LOGICAL_TYPES = {"string", "integer", "number", "boolean", "date", "datetime"}
# Supported contract vocabulary for v1 validation severities.
SUPPORTED_SEVERITIES = {"error", "warning", "info"}


@dataclass(slots=True)
class DatasetMetadata:
    """Stable file-level dataset facts captured during intake."""
    source_path: Path
    file_name: str
    file_extension: str
    sheet_name: str | None
    row_count: int
    column_count: int
    columns: list[str]


@dataclass(slots=True)
class FreshnessRule:
    """Recency rule used to evaluate date or datetime freshness constraints."""
    max_age_days: int
    reference: str = "max_value"


@dataclass(slots=True)
class ColumnContract:
    """Declared expectations and rule overrides for one contract column."""
    required: bool = True
    type: str | None = None
    nullable: bool = True
    unique: bool = False
    allowed_values: list[str | int | float | bool] = field(default_factory=list)
    min: int | float | None = None
    max: int | float | None = None
    pattern: str | None = None
    min_length: int | None = None
    max_length: int | None = None
    freshness: FreshnessRule | None = None
    description: str | None = None
    severity: str | None = None


@dataclass(slots=True)
class ContractMetadata:
    """Human-facing contract identity and ownership metadata."""
    name: str
    version: str | None = None
    owner: str | None = None
    description: str | None = None


@dataclass(slots=True)
class DatasetExpectation:
    """Dataset-level defaults and descriptive expectations applied across rules."""
    expected_name: str | None = None
    format: str | None = None
    grain: str | None = None
    severity_defaults: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class SchemaExpectation:
    """Schema-wide behavior flags, including unexpected-column handling."""
    allow_unexpected_columns: bool = False


@dataclass(slots=True)
class RowCountRule:
    """Dataset volume expectation used for min/max row count sanity checks."""
    min: int | None = None
    max: int | None = None
    severity: str | None = None


@dataclass(slots=True)
class UniquenessRule:
    """Single-column or composite-key uniqueness expectation."""
    name: str
    columns: list[str]
    severity: str | None = None


@dataclass(slots=True)
class DataContract:
    """Complete typed contract object consumed by deterministic validators."""
    contract: ContractMetadata
    dataset: DatasetExpectation = field(default_factory=DatasetExpectation)
    schema: SchemaExpectation = field(default_factory=SchemaExpectation)
    columns: dict[str, ColumnContract] = field(default_factory=dict)
    row_count: RowCountRule | None = None
    uniqueness: list[UniquenessRule] = field(default_factory=list)


@dataclass(slots=True)
class ValidationFinding:
    """One deterministic piece of validation evidence for a specific rule."""
    finding_id: str
    rule_type: str
    column: str | None
    columns: list[str] = field(default_factory=list)
    severity: str = "error"
    status: str = "failed"
    message: str = ""
    evidence: dict[str, object] = field(default_factory=dict)
    suggested_action: str | None = None


@dataclass(slots=True)
class ValidationResult:
    """Complete collection of findings and run metadata for one validation pass."""
    contract_name: str
    dataset_name: str
    row_count: int
    column_count: int
    findings: list[ValidationFinding] = field(default_factory=list)
