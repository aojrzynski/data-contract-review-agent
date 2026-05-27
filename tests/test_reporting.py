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
from data_contract_review_agent.reporting import build_markdown_validation_report
from data_contract_review_agent.suggested_updates import build_suggested_contract_updates


def _build_inputs(findings: list[ValidationFinding]):
    df = pd.DataFrame({"id": [1, 2], "status": ["ok", "bad"]})
    metadata = DatasetMetadata(Path("/tmp/customers.csv"), "customers.csv", ".csv", None, 2, 2, ["id", "status"])
    profile = build_dataset_profile(df, metadata)
    contract = DataContract(
        contract=ContractMetadata(name="customer_contract", version="1.0.0"),
        dataset=DatasetExpectation(),
        schema=SchemaExpectation(),
        columns={"id": ColumnContract(type="integer", nullable=False)},
    )
    result = ValidationResult("customer_contract", "customers.csv", 2, 2, findings)
    classified = classify_validation_result(result)
    suggestions = build_suggested_contract_updates(result, contract, profile)
    return result, classified, suggestions, profile, contract


def test_markdown_report_contains_expected_sections_and_status():
    findings = [
        ValidationFinding("f1", "type_mismatch", "id", severity="error", status="failed", message="bad type"),
        ValidationFinding("f2", "allowed_values_violation", "status", severity="warning", status="failed", message="bad value"),
    ]
    result, classified, suggestions, profile, contract = _build_inputs(findings)

    report = build_markdown_validation_report(result, classified, suggestions, profile, contract)

    assert "# Data Contract Validation Report" in report
    assert "Contract: customer_contract" in report
    assert "Dataset: customers.csv" in report
    assert "## Overall status" in report
    assert "- Failed" in report
    assert "## Authority boundary" in report
    assert "source of truth for pass/fail evidence" in report


def test_markdown_report_passed_when_no_findings():
    result, classified, suggestions, profile, contract = _build_inputs([])

    report = build_markdown_validation_report(result, classified, suggestions, profile, contract)

    assert "- Passed" in report
