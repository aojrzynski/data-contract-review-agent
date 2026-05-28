"""Contract loading and structural validation.

This layer verifies contract shape and allowed field values before runtime
dataset validation begins.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from data_contract_review_agent.contract_models import (
    ColumnContract,
    ContractMetadata,
    DataContract,
    DatasetExpectation,
    FreshnessRule,
    RowCountRule,
    SUPPORTED_LOGICAL_TYPES,
    SUPPORTED_SEVERITIES,
    SchemaExpectation,
    UniquenessRule,
)


def _validate_severity(value: str | None, field_name: str) -> None:
    """Centralize severity vocabulary validation for all contract sections."""
    if value is not None and value not in SUPPORTED_SEVERITIES:
        raise ValueError(
            f"Invalid severity '{value}' for {field_name}. "
            f"Supported severities: {', '.join(sorted(SUPPORTED_SEVERITIES))}"
        )


def _read_contract_dict(path: Path) -> dict[str, Any]:
    """Read YAML/JSON contract payloads into a validated top-level dictionary."""
    extension = path.suffix.lower()
    try:
        if extension in {".yaml", ".yml"}:
            with path.open("r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle)
        elif extension == ".json":
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        else:
            raise ValueError(
                f"Unsupported contract extension '{extension}'. Supported extensions: .yaml, .yml, .json"
            )
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise ValueError(f"Failed to parse contract file '{path}': {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("Contract file must contain a top-level object.")
    return payload


def load_contract(path: str | Path) -> DataContract:
    """Load a contract file into typed models for deterministic validation."""
    source_path = Path(path)
    if not source_path.exists():
        raise FileNotFoundError(f"Contract file not found: {source_path}")

    raw = _read_contract_dict(source_path)

    # contract metadata
    raw_contract = raw.get("contract")
    if not isinstance(raw_contract, dict):
        raise ValueError("Missing required 'contract' object.")

    contract_name = raw_contract.get("name")
    if not contract_name:
        raise ValueError("Missing required field 'contract.name'.")

    contract = ContractMetadata(
        name=str(contract_name),
        version=(str(raw_contract["version"]) if raw_contract.get("version") is not None else None),
        owner=(str(raw_contract["owner"]) if raw_contract.get("owner") is not None else None),
        description=(
            str(raw_contract["description"]) if raw_contract.get("description") is not None else None
        ),
    )

    # dataset-level options and severity defaults
    raw_dataset = raw.get("dataset") or {}
    if not isinstance(raw_dataset, dict):
        raise ValueError("'dataset' must be an object when provided.")
    severity_defaults = raw_dataset.get("severity_defaults") or {}
    if not isinstance(severity_defaults, dict):
        raise ValueError("'dataset.severity_defaults' must be an object when provided.")
    for key, sev in severity_defaults.items():
        _validate_severity(sev, f"dataset.severity_defaults.{key}")

    dataset = DatasetExpectation(
        expected_name=raw_dataset.get("expected_name"),
        format=raw_dataset.get("format"),
        grain=raw_dataset.get("grain"),
        severity_defaults=severity_defaults,
    )

    # schema expectations
    raw_schema = raw.get("schema") or {}
    if not isinstance(raw_schema, dict):
        raise ValueError("'schema' must be an object when provided.")
    schema = SchemaExpectation(
        allow_unexpected_columns=bool(raw_schema.get("allow_unexpected_columns", False))
    )

    # column expectations
    raw_columns = raw.get("columns")
    if not isinstance(raw_columns, dict) or not raw_columns:
        raise ValueError("Missing required 'columns' section with at least one column.")

    columns: dict[str, ColumnContract] = {}
    for column_name, raw_column in raw_columns.items():
        if not isinstance(raw_column, dict):
            raise ValueError(f"Column '{column_name}' definition must be an object.")

        logical_type = raw_column.get("type")
        if logical_type is not None and logical_type not in SUPPORTED_LOGICAL_TYPES:
            raise ValueError(
                f"Unsupported logical type '{logical_type}' for column '{column_name}'. "
                f"Supported types: {', '.join(sorted(SUPPORTED_LOGICAL_TYPES))}"
            )

        severity = raw_column.get("severity")
        _validate_severity(severity, f"columns.{column_name}.severity")

        # freshness rules
        freshness_payload = raw_column.get("freshness")
        freshness_rule = None
        if freshness_payload is not None:
            if not isinstance(freshness_payload, dict):
                raise ValueError(f"Freshness rule for column '{column_name}' must be an object.")
            max_age_days = freshness_payload.get("max_age_days")
            if not isinstance(max_age_days, int) or max_age_days <= 0:
                raise ValueError(
                    f"Freshness rule for column '{column_name}' must set positive integer max_age_days."
                )
            reference = freshness_payload.get("reference", "max_value")
            if reference != "max_value":
                raise ValueError(
                    f"Freshness reference for column '{column_name}' must be 'max_value'."
                )
            freshness_rule = FreshnessRule(max_age_days=max_age_days, reference=reference)

        columns[column_name] = ColumnContract(
            required=bool(raw_column.get("required", True)),
            type=logical_type,
            nullable=bool(raw_column.get("nullable", True)),
            unique=bool(raw_column.get("unique", False)),
            allowed_values=list(raw_column.get("allowed_values", [])),
            min=raw_column.get("min"),
            max=raw_column.get("max"),
            pattern=raw_column.get("pattern"),
            min_length=raw_column.get("min_length"),
            max_length=raw_column.get("max_length"),
            freshness=freshness_rule,
            description=raw_column.get("description"),
            severity=severity,
        )

    # row count rule
    row_count_rule = None
    raw_row_count = raw.get("row_count")
    if raw_row_count is not None:
        if not isinstance(raw_row_count, dict):
            raise ValueError("'row_count' must be an object when provided.")
        min_rows = raw_row_count.get("min")
        max_rows = raw_row_count.get("max")
        if min_rows is not None and min_rows < 0:
            raise ValueError("row_count.min must not be negative.")
        if max_rows is not None and max_rows < 0:
            raise ValueError("row_count.max must not be negative.")
        if min_rows is not None and max_rows is not None and min_rows > max_rows:
            raise ValueError("row_count.min must not be greater than row_count.max.")
        row_count_severity = raw_row_count.get("severity")
        _validate_severity(row_count_severity, "row_count.severity")
        row_count_rule = RowCountRule(min=min_rows, max=max_rows, severity=row_count_severity)

    # uniqueness rules
    uniqueness_rules: list[UniquenessRule] = []
    raw_uniqueness = raw.get("uniqueness", [])
    if not isinstance(raw_uniqueness, list):
        raise ValueError("'uniqueness' must be a list when provided.")
    for index, rule in enumerate(raw_uniqueness):
        if not isinstance(rule, dict):
            raise ValueError(f"uniqueness[{index}] must be an object.")
        name = rule.get("name")
        if not name:
            raise ValueError(f"uniqueness[{index}].name is required.")
        cols = rule.get("columns")
        if not isinstance(cols, list) or not cols or not all(isinstance(item, str) and item for item in cols):
            raise ValueError(f"uniqueness[{index}].columns must be a non-empty list of column names.")
        severity = rule.get("severity")
        _validate_severity(severity, f"uniqueness[{index}].severity")
        uniqueness_rules.append(UniquenessRule(name=name, columns=cols, severity=severity))

    return DataContract(
        contract=contract,
        dataset=dataset,
        schema=schema,
        columns=columns,
        row_count=row_count_rule,
        uniqueness=uniqueness_rules,
    )
