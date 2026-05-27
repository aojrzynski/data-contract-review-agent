import json
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
from data_contract_review_agent.finding_classifier import classify_validation_result
from data_contract_review_agent.profiling import build_dataset_profile
from data_contract_review_agent.suggested_updates import build_suggested_contract_updates
from data_contract_review_agent.trace_writer import write_contract_trace


def test_trace_json_contains_expected_sections(tmp_path: Path):
    df = pd.DataFrame({"id": [1, None, 3], "status": ["ok", "bad", "ok"]})
    metadata = DatasetMetadata(Path("/tmp/customers.csv"), "customers.csv", ".csv", None, 3, 2, ["id", "status"])
    profile = build_dataset_profile(df, metadata)
    contract = DataContract(
        contract=ContractMetadata(name="customer_contract", version="2.0.0"),
        dataset=DatasetExpectation(),
        schema=SchemaExpectation(),
        columns={"id": ColumnContract(type="integer", nullable=False)},
    )
    result = ValidationResult(
        "customer_contract",
        "customers.csv",
        3,
        2,
        [ValidationFinding("f1", "nullability_violation", "id", severity="error", status="failed")],
    )
    classified = classify_validation_result(result)
    suggestions = build_suggested_contract_updates(result, contract, profile)

    path = write_contract_trace(tmp_path / "contract_trace.json", result, classified, suggestions, profile, contract)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert "input_summary" in payload
    assert "profile_summary" in payload
    assert "validation_summary" in payload
    assert "classification_summary" in payload
    assert "suggested_update_summary" in payload
    assert "authority_boundary" in payload
    assert payload["authority_boundary"]["deterministic_validation_is_authoritative"] is True
    assert payload["authority_boundary"]["suggestions_are_applied_automatically"] is False
    assert payload["authority_boundary"]["llm_used"] is False
