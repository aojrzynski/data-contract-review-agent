from pathlib import Path

import pandas as pd

from data_contract_review_agent.contract_models import (
    ColumnContract,
    ContractMetadata,
    DataContract,
    DatasetExpectation,
    DatasetMetadata,
    RowCountRule,
    SchemaExpectation,
)
from data_contract_review_agent.contract_validation import validate_contract
from data_contract_review_agent.profiling import build_dataset_profile


def test_validate_contract_returns_validation_result_summary_fields():
    dataframe = pd.DataFrame({"id": [1, 1], "status": ["ok", "bad"]})
    metadata = DatasetMetadata(
        source_path=Path("/tmp/test.csv"),
        file_name="test.csv",
        file_extension=".csv",
        sheet_name=None,
        row_count=2,
        column_count=2,
        columns=["id", "status"],
    )
    profile = build_dataset_profile(dataframe, metadata)
    contract = DataContract(
        contract=ContractMetadata(name="customer_contract"),
        dataset=DatasetExpectation(),
        schema=SchemaExpectation(allow_unexpected_columns=False),
        columns={
            "id": ColumnContract(unique=True),
            "status": ColumnContract(allowed_values=["ok"]),
        },
        row_count=RowCountRule(min=3),
        uniqueness=[],
    )

    result = validate_contract(dataframe, profile, contract)

    assert result.contract_name == "customer_contract"
    assert result.dataset_name == "test.csv"
    assert result.row_count == 2
    assert result.column_count == 2
    assert len(result.findings) >= 3
    assert {f.rule_type for f in result.findings}.issuperset(
        {"uniqueness_violation", "allowed_values_violation", "row_count_violation"}
    )
