"""Typed models used by the data contract review agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


SUPPORTED_LOGICAL_TYPES = {"string", "integer", "number", "boolean", "date", "datetime"}
SUPPORTED_SEVERITIES = {"error", "warning", "info"}


@dataclass(slots=True)
class DatasetMetadata:
    source_path: Path
    file_name: str
    file_extension: str
    sheet_name: str | None
    row_count: int
    column_count: int
    columns: list[str]


@dataclass(slots=True)
class FreshnessRule:
    max_age_days: int
    reference: str = "max_value"


@dataclass(slots=True)
class ColumnContract:
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
    name: str
    version: str | None = None
    owner: str | None = None
    description: str | None = None


@dataclass(slots=True)
class DatasetExpectation:
    expected_name: str | None = None
    format: str | None = None
    grain: str | None = None
    severity_defaults: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class SchemaExpectation:
    allow_unexpected_columns: bool = False


@dataclass(slots=True)
class RowCountRule:
    min: int | None = None
    max: int | None = None
    severity: str | None = None


@dataclass(slots=True)
class UniquenessRule:
    name: str
    columns: list[str]
    severity: str | None = None


@dataclass(slots=True)
class DataContract:
    contract: ContractMetadata
    dataset: DatasetExpectation = field(default_factory=DatasetExpectation)
    schema: SchemaExpectation = field(default_factory=SchemaExpectation)
    columns: dict[str, ColumnContract] = field(default_factory=dict)
    row_count: RowCountRule | None = None
    uniqueness: list[UniquenessRule] = field(default_factory=list)


@dataclass(slots=True)
class ValidationFinding:
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
    contract_name: str
    dataset_name: str
    row_count: int
    column_count: int
    findings: list[ValidationFinding] = field(default_factory=list)
