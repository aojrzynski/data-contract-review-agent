import csv
import json
from pathlib import Path

import pandas as pd
import yaml

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
from data_contract_review_agent.output_writers import write_validation_outputs
from data_contract_review_agent.profiling import build_dataset_profile
from data_contract_review_agent.suggested_updates import build_suggested_contract_updates


def _sample_bundle(findings: list[ValidationFinding]):
    df = pd.DataFrame({"id": [1, 2, None], "status": ["ok", "bad", "ok"], "extra": ["x", "y", "z"]})
    metadata = DatasetMetadata(Path("/tmp/customers.csv"), "customers.csv", ".csv", None, 3, 3, ["id", "status", "extra"])
    profile = build_dataset_profile(df, metadata)
    contract = DataContract(
        contract=ContractMetadata(name="customer_contract"),
        dataset=DatasetExpectation(),
        schema=SchemaExpectation(),
        columns={"id": ColumnContract(type="integer", nullable=False), "status": ColumnContract(type="string")},
    )
    validation_result = ValidationResult("customer_contract", "customers.csv", 3, 3, findings)
    classified = classify_validation_result(validation_result)
    suggestions = build_suggested_contract_updates(validation_result, contract, profile)
    return validation_result, classified, suggestions, profile, contract


def test_write_validation_outputs_creates_artifacts_and_content(tmp_path: Path):
    findings = [
        ValidationFinding("f1", "unexpected_column", "extra", severity="warning", status="failed", message="unexpected"),
        ValidationFinding(
            "f2",
            "uniqueness_violation",
            "id",
            columns=["id", "status"],
            severity="error",
            status="failed",
            message="duplicates",
            suggested_action="dedupe",
        ),
        ValidationFinding("f3", "row_count_violation", None, severity="warning", status="skipped", message="skipped for setup"),
    ]
    result, classified, suggestions, profile, contract = _sample_bundle(findings)

    outputs = write_validation_outputs(tmp_path / "nested" / "outputs", result, classified, suggestions, profile, contract)

    assert set(outputs.keys()) == {"report", "results_json", "failures_csv", "trace_json", "suggested_updates_yaml"}
    for path in outputs.values():
        assert path.exists()

    results_payload = json.loads(outputs["results_json"].read_text(encoding="utf-8"))
    assert set(results_payload.keys()) == {
        "contract_name",
        "dataset_name",
        "row_count",
        "column_count",
        "summary",
        "findings",
        "classifications",
        "suggested_updates",
    }
    assert results_payload["summary"]["total_findings"] == 3
    assert results_payload["summary"]["by_severity"] == {"error": 1, "warning": 2}

    with outputs["failures_csv"].open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0].keys() == {
        "finding_id",
        "rule_type",
        "column",
        "columns",
        "severity",
        "status",
        "compatibility",
        "priority",
        "review_category",
        "message",
        "suggested_action",
        "recommended_human_action",
    }
    assert len(rows) == 3
    assert rows[1]["columns"] == "id|status"

    yaml_payload = yaml.safe_load(outputs["suggested_updates_yaml"].read_text(encoding="utf-8"))
    assert yaml_payload["human_review_required"] is True
    assert "not applied automatically" in yaml_payload["note"]
    assert isinstance(yaml_payload["suggestions"], list)


def test_write_validation_outputs_with_empty_findings_reports_passed(tmp_path: Path):
    result, classified, suggestions, profile, contract = _sample_bundle([])
    outputs = write_validation_outputs(tmp_path / "new_out", result, classified, suggestions, profile, contract)

    report = outputs["report"].read_text(encoding="utf-8")
    assert "- Passed" in report
    assert outputs["results_json"].exists()
