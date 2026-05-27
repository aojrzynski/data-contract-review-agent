from copy import deepcopy
from pathlib import Path

import pandas as pd

from data_contract_review_agent.contract_models import (
    ColumnContract,
    ContractMetadata,
    DataContract,
    DatasetExpectation,
    DatasetMetadata,
    SchemaExpectation,
    ValidationFinding,
    ValidationResult,
)
from data_contract_review_agent.profiling import build_dataset_profile
from data_contract_review_agent.suggested_updates import build_suggested_contract_updates


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


def _contract() -> DataContract:
    return DataContract(
        contract=ContractMetadata(name="contract_a"),
        dataset=DatasetExpectation(),
        schema=SchemaExpectation(),
        columns={"id": ColumnContract(type="integer", nullable=False)},
    )


def test_suggested_updates_for_supported_finding_types_and_contract_immutability():
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "new_col": ["a", "b", None],
            "status": ["ok", "bad", "ok"],
            "event_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        }
    )
    profile = _profile(df)
    contract = _contract()
    contract_snapshot = deepcopy(contract)

    result = ValidationResult(
        contract_name="contract_a",
        dataset_name="test.csv",
        row_count=3,
        column_count=4,
        findings=[
            ValidationFinding("u", "unexpected_column", "new_col", evidence={}),
            ValidationFinding("av", "allowed_values_violation", "status", evidence={"unexpected_values": {"bad": 1}}),
            ValidationFinding("n", "nullability_violation", "id", evidence={"null_count": 1}),
            ValidationFinding("t", "type_mismatch", "id", evidence={"observed_type": "string"}),
            ValidationFinding("f", "freshness_violation", "event_date", evidence={"age_days": 30}),
            ValidationFinding("r", "row_count_violation", None, evidence={"row_count": 3, "min_allowed": 4, "max_allowed": 10}),
            ValidationFinding("x", "pattern_violation", "id", evidence={}),
        ],
    )

    suggestions = build_suggested_contract_updates(result, contract, profile)
    by_type = {item.suggestion_type: item for item in suggestions.suggestions}

    assert "add_unexpected_column" in by_type
    add_col = by_type["add_unexpected_column"]
    assert add_col.proposed_change["type"] == profile.columns["new_col"].observed_logical_type
    assert "sample_values" in add_col.evidence

    assert by_type["review_allowed_values"].proposed_change["candidate_values"] == ["bad"]

    nullability = by_type["review_nullability"]
    assert nullability.confidence == "low"
    assert nullability.human_decision_required is True

    type_review = by_type["review_type"]
    assert type_review.confidence == "low"
    assert type_review.target_path == "columns.id.type"

    freshness = by_type["review_refresh_process"]
    assert freshness.proposed_change == {}

    row_count = by_type["review_row_count_bounds"]
    assert row_count.target_path == "row_count"
    assert row_count.proposed_change["observed_row_count"] == 3

    assert "pattern_violation" not in [item.suggestion_type for item in suggestions.suggestions]
    assert contract == contract_snapshot
