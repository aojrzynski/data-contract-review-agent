"""Deterministic orchestration point for contract validators."""

from __future__ import annotations

from datetime import date

import pandas as pd

from data_contract_review_agent.contract_models import DataContract, ValidationResult
from data_contract_review_agent.profiling import DatasetProfile
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


def validate_contract(
    dataframe: pd.DataFrame,
    profile: DatasetProfile,
    contract: DataContract,
    reference_date: date | None = None,
    max_examples: int = 20,
) -> ValidationResult:
    """Run deterministic validation checks against a loaded dataset and contract."""
    as_of_date = reference_date or date.today()

    findings = []
    findings.extend(validate_required_columns(dataframe, profile, contract))
    findings.extend(validate_unexpected_columns(dataframe, profile, contract))
    findings.extend(validate_type_expectations(dataframe, profile, contract))
    findings.extend(validate_nullability(dataframe, profile, contract))
    findings.extend(validate_uniqueness(dataframe, profile, contract, max_examples=max_examples))
    findings.extend(validate_allowed_values(dataframe, profile, contract, max_examples=max_examples))
    findings.extend(validate_numeric_range(dataframe, profile, contract))
    findings.extend(validate_pattern(dataframe, profile, contract, max_examples=max_examples))
    findings.extend(validate_length(dataframe, profile, contract))
    findings.extend(validate_freshness(dataframe, profile, contract, reference_date=as_of_date))
    findings.extend(validate_row_count(dataframe, profile, contract))

    return ValidationResult(
        contract_name=contract.contract.name,
        dataset_name=profile.file_name,
        row_count=profile.row_count,
        column_count=profile.column_count,
        findings=findings,
    )
