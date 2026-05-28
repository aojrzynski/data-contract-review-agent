"""Deterministic, evidence-producing checks for dataset-vs-contract validation."""

from __future__ import annotations

import re
from datetime import date

import pandas as pd

from data_contract_review_agent.contract_models import ColumnContract, DataContract, ValidationFinding
from data_contract_review_agent.profiling import DatasetProfile


DEFAULT_SEVERITY_BY_RULE = {
    "missing_required_column": "error",
    "unexpected_column": "warning",
    "type_mismatch": "error",
    "nullability_violation": "error",
    "uniqueness_violation": "error",
    "allowed_values_violation": "error",
    "range_violation": "error",
    "pattern_violation": "warning",
    "length_violation": "error",
    "freshness_violation": "warning",
    "row_count_violation": "warning",
}


def _severity(
    contract: DataContract,
    rule_type: str,
    column: ColumnContract | None = None,
    rule_severity: str | None = None,
) -> str:
    # Severity precedence: column override > rule override > dataset defaults > global defaults.
    if column and column.severity:
        return column.severity
    if rule_severity:
        return rule_severity
    return contract.dataset.severity_defaults.get(rule_type, DEFAULT_SEVERITY_BY_RULE[rule_type])


def _finding_id(rule_type: str, columns: list[str]) -> str:
    # Finding IDs are deterministic so findings remain traceable across reruns.
    suffix = "_".join(columns) if columns else "dataset"
    return f"{rule_type}:{suffix}"


def validate_required_columns(dataframe: pd.DataFrame, profile: DatasetProfile, contract: DataContract) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    available = list(dataframe.columns)
    for column_name, column_rule in contract.columns.items():
        if column_rule.required and column_name not in dataframe.columns:
            findings.append(
                ValidationFinding(
                    finding_id=_finding_id("missing_required_column", [column_name]),
                    rule_type="missing_required_column",
                    column=column_name,
                    columns=[column_name],
                    severity=_severity(contract, "missing_required_column", column=column_rule),
                    status="failed",
                    message=f"Required column '{column_name}' is missing from the dataset.",
                    evidence={"expected_column": column_name, "available_columns": available},
                    suggested_action=f"Add column '{column_name}' to the dataset or mark it as not required.",
                )
            )
    return findings


def validate_unexpected_columns(dataframe: pd.DataFrame, profile: DatasetProfile, contract: DataContract) -> list[ValidationFinding]:
    if contract.schema.allow_unexpected_columns:
        return []
    declared = set(contract.columns.keys())
    findings: list[ValidationFinding] = []
    for column_name in dataframe.columns:
        if column_name not in declared:
            findings.append(
                ValidationFinding(
                    finding_id=_finding_id("unexpected_column", [str(column_name)]),
                    rule_type="unexpected_column",
                    column=str(column_name),
                    columns=[str(column_name)],
                    severity=_severity(contract, "unexpected_column"),
                    status="warning",
                    message=f"Column '{column_name}' is not declared in the contract.",
                    evidence={"unexpected_column": str(column_name), "declared_columns": sorted(declared)},
                    suggested_action="Declare the column in the contract or allow unexpected columns.",
                )
            )
    return findings


def validate_type_expectations(dataframe: pd.DataFrame, profile: DatasetProfile, contract: DataContract) -> list[ValidationFinding]:
    compatible = {
        "date": {"date"},
        "datetime": {"datetime", "date"},
        "number": {"integer", "number"},
        "integer": {"integer"},
        "string": {"string"},
        "boolean": {"boolean"},
    }
    findings: list[ValidationFinding] = []
    for name, rule in contract.columns.items():
        if name not in dataframe.columns or not rule.type:
            continue
        observed = profile.columns[name].observed_logical_type
        if observed == "empty":
            continue
        expected = rule.type
        if observed not in compatible.get(expected, set()):
            findings.append(
                ValidationFinding(
                    finding_id=_finding_id("type_mismatch", [name]),
                    rule_type="type_mismatch",
                    column=name,
                    columns=[name],
                    severity=_severity(contract, "type_mismatch", column=rule),
                    status="failed",
                    message=f"Column '{name}' has observed type '{observed}', expected '{expected}'.",
                    evidence={"expected_type": expected, "observed_type": observed},
                    suggested_action="Align the dataset values with the expected type or update the contract type.",
                )
            )
    return findings


def validate_nullability(dataframe: pd.DataFrame, profile: DatasetProfile, contract: DataContract) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for name, rule in contract.columns.items():
        if name not in dataframe.columns or rule.nullable:
            continue
        col_profile = profile.columns[name]
        if col_profile.null_count > 0:
            findings.append(
                ValidationFinding(
                    finding_id=_finding_id("nullability_violation", [name]),
                    rule_type="nullability_violation",
                    column=name,
                    columns=[name],
                    severity=_severity(contract, "nullability_violation", column=rule),
                    status="failed",
                    message=f"Column '{name}' is non-nullable but contains null values.",
                    evidence={
                        "null_count": col_profile.null_count,
                        "row_count": profile.row_count,
                        "null_percentage": col_profile.null_percentage,
                    },
                    suggested_action="Backfill null values or mark the column as nullable.",
                )
            )
    return findings


def _evaluate_uniqueness(
    dataframe: pd.DataFrame,
    contract: DataContract,
    columns: list[str],
    severity: str,
    name: str,
    max_examples: int,
) -> ValidationFinding | None:
    missing = [col for col in columns if col not in dataframe.columns]
    if missing:
        return ValidationFinding(
            finding_id=_finding_id("uniqueness_violation", columns),
            rule_type="uniqueness_violation",
            column=columns[0] if len(columns) == 1 else None,
            columns=columns,
            severity=severity,
            status="skipped",
            message=f"Uniqueness check '{name}' skipped because required columns are missing.",
            evidence={"rule_name": name, "checked_columns": columns, "missing_columns": missing},
            suggested_action="Ensure all uniqueness rule columns are present in the dataset.",
        )

    duplicate_mask = dataframe.duplicated(subset=columns, keep=False)
    if not duplicate_mask.any():
        return None

    duplicate_rows = dataframe.loc[duplicate_mask, columns]
    duplicate_key_count = int(duplicate_rows.drop_duplicates().shape[0])
    duplicate_row_count = int(duplicate_rows.shape[0])
    sample_keys = duplicate_rows.drop_duplicates().head(max_examples).to_dict(orient="records")

    return ValidationFinding(
        finding_id=_finding_id("uniqueness_violation", columns),
        rule_type="uniqueness_violation",
        column=columns[0] if len(columns) == 1 else None,
        columns=columns,
        severity=severity,
        status="failed",
        message=f"Uniqueness rule '{name}' failed with duplicate keys.",
        evidence={
            "rule_name": name,
            "checked_columns": columns,
            "duplicate_key_count": duplicate_key_count,
            "duplicate_row_count": duplicate_row_count,
            "sample_duplicate_keys": sample_keys,
        },
        suggested_action="Deduplicate rows or update uniqueness expectations.",
    )


def validate_uniqueness(
    dataframe: pd.DataFrame, profile: DatasetProfile, contract: DataContract, max_examples: int = 20
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for name, column_rule in contract.columns.items():
        if column_rule.unique:
            finding = _evaluate_uniqueness(
                dataframe,
                contract,
                [name],
                _severity(contract, "uniqueness_violation", column=column_rule),
                f"column_unique:{name}",
                max_examples,
            )
            if finding:
                findings.append(finding)

    for rule in contract.uniqueness:
        finding = _evaluate_uniqueness(
            dataframe,
            contract,
            rule.columns,
            _severity(contract, "uniqueness_violation", rule_severity=rule.severity),
            rule.name,
            max_examples,
        )
        if finding:
            findings.append(finding)

    return findings


def validate_allowed_values(dataframe: pd.DataFrame, profile: DatasetProfile, contract: DataContract, max_examples: int = 20) -> list[ValidationFinding]:
    findings = []
    for name, rule in contract.columns.items():
        if name not in dataframe.columns or not rule.allowed_values:
            continue
        non_null = dataframe[name].dropna()
        invalid = non_null[~non_null.isin(rule.allowed_values)]
        if invalid.empty:
            continue
        counts = invalid.value_counts().head(max_examples)
        findings.append(
            ValidationFinding(
                finding_id=_finding_id("allowed_values_violation", [name]),
                rule_type="allowed_values_violation",
                column=name,
                columns=[name],
                severity=_severity(contract, "allowed_values_violation", column=rule),
                status="failed",
                message=f"Column '{name}' contains values outside the allowed set.",
                evidence={
                    "allowed_values": list(rule.allowed_values),
                    "unexpected_values": {str(k): int(v) for k, v in counts.items()},
                    "failed_row_count": int(invalid.shape[0]),
                },
                suggested_action="Update the data values or expand allowed_values in the contract.",
            )
        )
    return findings


def validate_numeric_range(dataframe: pd.DataFrame, profile: DatasetProfile, contract: DataContract) -> list[ValidationFinding]:
    findings = []
    for name, rule in contract.columns.items():
        if name not in dataframe.columns or (rule.min is None and rule.max is None):
            continue
        numeric = pd.to_numeric(dataframe[name], errors="coerce")
        valid = numeric.dropna()
        below = int((valid < rule.min).sum()) if rule.min is not None else 0
        above = int((valid > rule.max).sum()) if rule.max is not None else 0
        if below == 0 and above == 0:
            continue
        findings.append(
            ValidationFinding(
                finding_id=_finding_id("range_violation", [name]),
                rule_type="range_violation",
                column=name,
                columns=[name],
                severity=_severity(contract, "range_violation", column=rule),
                status="failed",
                message=f"Column '{name}' violates numeric range constraints.",
                evidence={
                    "min_allowed": rule.min,
                    "max_allowed": rule.max,
                    "observed_min": valid.min() if not valid.empty else None,
                    "observed_max": valid.max() if not valid.empty else None,
                    "below_min_count": below,
                    "above_max_count": above,
                },
                suggested_action="Clamp, clean, or correct out-of-range values in the dataset.",
            )
        )
    return findings


def validate_pattern(dataframe: pd.DataFrame, profile: DatasetProfile, contract: DataContract, max_examples: int = 20) -> list[ValidationFinding]:
    findings = []
    for name, rule in contract.columns.items():
        if name not in dataframe.columns or not rule.pattern:
            continue
        try:
            regex = re.compile(rule.pattern)
        except re.error as exc:
            findings.append(
                ValidationFinding(
                    finding_id=_finding_id("pattern_violation", [name]),
                    rule_type="pattern_violation",
                    column=name,
                    columns=[name],
                    severity=_severity(contract, "pattern_violation", column=rule),
                    status="skipped",
                    message=f"Pattern check skipped for column '{name}' because regex is invalid.",
                    evidence={"pattern": rule.pattern, "error": str(exc)},
                    suggested_action="Fix the contract regex pattern.",
                )
            )
            continue
        values = dataframe[name].dropna().astype(str)
        failed = values[~values.map(lambda value: bool(regex.fullmatch(value)))]
        if failed.empty:
            continue
        findings.append(
            ValidationFinding(
                finding_id=_finding_id("pattern_violation", [name]),
                rule_type="pattern_violation",
                column=name,
                columns=[name],
                severity=_severity(contract, "pattern_violation", column=rule),
                status="warning",
                message=f"Column '{name}' contains values that do not match the required pattern.",
                evidence={
                    "pattern": rule.pattern,
                    "failed_row_count": int(failed.shape[0]),
                    "sample_failed_values": failed.head(max_examples).tolist(),
                },
                suggested_action="Correct source values or adjust the contract regex.",
            )
        )
    return findings


def validate_length(dataframe: pd.DataFrame, profile: DatasetProfile, contract: DataContract) -> list[ValidationFinding]:
    findings = []
    for name, rule in contract.columns.items():
        if name not in dataframe.columns or (rule.min_length is None and rule.max_length is None):
            continue
        lengths = dataframe[name].dropna().astype(str).map(len)
        too_short = int((lengths < rule.min_length).sum()) if rule.min_length is not None else 0
        too_long = int((lengths > rule.max_length).sum()) if rule.max_length is not None else 0
        if too_short == 0 and too_long == 0:
            continue
        findings.append(
            ValidationFinding(
                finding_id=_finding_id("length_violation", [name]),
                rule_type="length_violation",
                column=name,
                columns=[name],
                severity=_severity(contract, "length_violation", column=rule),
                status="failed",
                message=f"Column '{name}' violates string length constraints.",
                evidence={
                    "min_length": rule.min_length,
                    "max_length": rule.max_length,
                    "observed_min_length": int(lengths.min()) if not lengths.empty else None,
                    "observed_max_length": int(lengths.max()) if not lengths.empty else None,
                    "too_short_count": too_short,
                    "too_long_count": too_long,
                },
                suggested_action="Trim, pad, or validate values to meet length constraints.",
            )
        )
    return findings


def validate_freshness(dataframe: pd.DataFrame, profile: DatasetProfile, contract: DataContract, reference_date: date) -> list[ValidationFinding]:
    findings = []
    for name, rule in contract.columns.items():
        if name not in dataframe.columns or not rule.freshness:
            continue
        parsed = pd.to_datetime(dataframe[name], errors="coerce").dropna()
        if parsed.empty:
            findings.append(
                ValidationFinding(
                    finding_id=_finding_id("freshness_violation", [name]),
                    rule_type="freshness_violation",
                    column=name,
                    columns=[name],
                    severity=_severity(contract, "freshness_violation", column=rule),
                    status="skipped",
                    message=f"Freshness check skipped for column '{name}' because no parseable datetime values were found.",
                    evidence={
                        "latest_value": None,
                        "reference_date": reference_date.isoformat(),
                        "max_age_days": rule.freshness.max_age_days,
                        "observed_age_days": None,
                    },
                    suggested_action="Provide parseable date/datetime values for freshness checks.",
                )
            )
            continue
        latest = pd.Timestamp(parsed.max())
        age_days = (reference_date - latest.date()).days
        if age_days <= rule.freshness.max_age_days:
            continue
        findings.append(
            ValidationFinding(
                finding_id=_finding_id("freshness_violation", [name]),
                rule_type="freshness_violation",
                column=name,
                columns=[name],
                severity=_severity(contract, "freshness_violation", column=rule),
                status="warning",
                message=f"Column '{name}' is older than the allowed freshness window.",
                evidence={
                    "latest_value": latest.isoformat(),
                    "reference_date": reference_date.isoformat(),
                    "max_age_days": rule.freshness.max_age_days,
                    "observed_age_days": age_days,
                },
                suggested_action="Refresh the dataset with newer records.",
            )
        )
    return findings


def validate_row_count(dataframe: pd.DataFrame, profile: DatasetProfile, contract: DataContract) -> list[ValidationFinding]:
    if contract.row_count is None or (contract.row_count.min is None and contract.row_count.max is None):
        return []
    rows = profile.row_count
    min_allowed = contract.row_count.min
    max_allowed = contract.row_count.max
    is_low = min_allowed is not None and rows < min_allowed
    is_high = max_allowed is not None and rows > max_allowed
    if not is_low and not is_high:
        return []
    return [
        ValidationFinding(
            finding_id=_finding_id("row_count_violation", []),
            rule_type="row_count_violation",
            column=None,
            columns=[],
            severity=_severity(
                contract,
                "row_count_violation",
                rule_severity=contract.row_count.severity,
            ),
            status="warning",
            message="Dataset row count is outside configured bounds.",
            evidence={"row_count": rows, "min_allowed": min_allowed, "max_allowed": max_allowed},
            suggested_action="Adjust extraction volume or update row_count bounds in the contract.",
        )
    ]
