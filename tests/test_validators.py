from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from data_contract_review_agent.contract_models import (
    ColumnContract,
    ContractMetadata,
    DataContract,
    DatasetExpectation,
    DatasetMetadata,
    FreshnessRule,
    RowCountRule,
    SchemaExpectation,
    UniquenessRule,
)
from data_contract_review_agent.profiling import build_dataset_profile
from data_contract_review_agent.validators import (
    validate_allowed_values,
    validate_freshness,
    validate_length,
    validate_nullability,
    validate_numeric_range,
    validate_pattern,
    validate_required_columns,
    validate_row_count,
    validate_type_expectations,
    validate_uniqueness,
    validate_unexpected_columns,
)


def _profile(df: pd.DataFrame):
    metadata = DatasetMetadata(
        source_path=Path("/tmp/test.csv"),
        file_name="test.csv",
        file_extension=".csv",
        sheet_name=None,
        row_count=len(df),
        column_count=len(df.columns),
        columns=[str(c) for c in df.columns],
    )
    return build_dataset_profile(df, metadata)


def _contract(columns: dict[str, ColumnContract], **kwargs) -> DataContract:
    return DataContract(
        contract=ContractMetadata(name="contract_a"),
        dataset=kwargs.get("dataset", DatasetExpectation()),
        schema=kwargs.get("schema", SchemaExpectation()),
        columns=columns,
        row_count=kwargs.get("row_count"),
        uniqueness=kwargs.get("uniqueness", []),
    )


def test_required_column_missing():
    df = pd.DataFrame({"id": [1]})
    c = _contract({"id": ColumnContract(required=True), "email": ColumnContract(required=True)})
    findings = validate_required_columns(df, _profile(df), c)
    assert len(findings) == 1
    assert findings[0].rule_type == "missing_required_column"


def test_unexpected_column_when_not_allowed_and_ignored_when_allowed():
    df = pd.DataFrame({"id": [1], "extra": ["x"]})
    c_block = _contract({"id": ColumnContract()}, schema=SchemaExpectation(allow_unexpected_columns=False))
    assert len(validate_unexpected_columns(df, _profile(df), c_block)) == 1

    c_allow = _contract({"id": ColumnContract()}, schema=SchemaExpectation(allow_unexpected_columns=True))
    assert validate_unexpected_columns(df, _profile(df), c_allow) == []


def test_type_mismatch_and_number_accepts_integer():
    df = pd.DataFrame({"age": [1, 2], "name": ["a", "b"]})
    c = _contract({"age": ColumnContract(type="string"), "name": ColumnContract(type="string")})
    findings = validate_type_expectations(df, _profile(df), c)
    assert any(f.column == "age" and f.rule_type == "type_mismatch" for f in findings)

    c2 = _contract({"age": ColumnContract(type="number")})
    assert validate_type_expectations(df[["age"]], _profile(df[["age"]]), c2) == []


def test_nullability_violation():
    df = pd.DataFrame({"id": [1, None]})
    c = _contract({"id": ColumnContract(nullable=False)})
    findings = validate_nullability(df, _profile(df), c)
    assert len(findings) == 1
    assert findings[0].evidence["null_count"] == 1


def test_column_and_composite_uniqueness_and_missing_columns():
    df = pd.DataFrame({"id": [1, 1, 2], "a": ["x", "x", "y"], "b": [1, 1, 2]})
    c = _contract(
        {"id": ColumnContract(unique=True)},
        uniqueness=[UniquenessRule(name="ab_unique", columns=["a", "b"]), UniquenessRule(name="missing", columns=["c", "d"])],
    )
    findings = validate_uniqueness(df, _profile(df), c)
    assert sum(1 for f in findings if f.status == "failed") == 2
    assert any(f.status == "skipped" and f.evidence["missing_columns"] == ["c", "d"] for f in findings)


def test_allowed_values_violation():
    df = pd.DataFrame({"status": ["ok", "bad", "ok"]})
    c = _contract({"status": ColumnContract(allowed_values=["ok", "pending"])})
    findings = validate_allowed_values(df, _profile(df), c)
    assert len(findings) == 1
    assert findings[0].evidence["failed_row_count"] == 1


def test_numeric_range_violation():
    df = pd.DataFrame({"score": [0, 50, 120]})
    c = _contract({"score": ColumnContract(min=1, max=100)})
    findings = validate_numeric_range(df, _profile(df), c)
    assert len(findings) == 1
    assert findings[0].evidence["below_min_count"] == 1
    assert findings[0].evidence["above_max_count"] == 1


def test_pattern_violation_and_invalid_regex_skipped():
    df = pd.DataFrame({"zip": ["12345", "ABCDE"]})
    c_bad = _contract({"zip": ColumnContract(pattern=r"^[0-9]{5}$")})
    findings_bad = validate_pattern(df, _profile(df), c_bad)
    assert len(findings_bad) == 1 and findings_bad[0].status == "warning"

    c_invalid = _contract({"zip": ColumnContract(pattern=r"[")})
    findings_invalid = validate_pattern(df, _profile(df), c_invalid)
    assert len(findings_invalid) == 1 and findings_invalid[0].status == "skipped"


def test_length_violation():
    df = pd.DataFrame({"code": ["A", "ABCDE", "AB"]})
    c = _contract({"code": ColumnContract(min_length=2, max_length=4)})
    findings = validate_length(df, _profile(df), c)
    assert len(findings) == 1
    assert findings[0].evidence["too_short_count"] == 1
    assert findings[0].evidence["too_long_count"] == 1


def test_freshness_violation_with_reference_date():
    df = pd.DataFrame({"event_date": ["2025-01-01", "2025-01-15"]})
    c = _contract({"event_date": ColumnContract(freshness=FreshnessRule(max_age_days=30), type="date")})
    findings = validate_freshness(df, _profile(df), c, reference_date=date(2025, 3, 1))
    assert len(findings) == 1
    assert findings[0].rule_type == "freshness_violation"


def test_row_count_violation():
    df = pd.DataFrame({"id": [1, 2, 3]})
    c = _contract({"id": ColumnContract()}, row_count=RowCountRule(min=4, max=10))
    findings = validate_row_count(df, _profile(df), c)
    assert len(findings) == 1
    assert findings[0].rule_type == "row_count_violation"
