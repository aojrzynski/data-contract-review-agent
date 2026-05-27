from data_contract_review_agent.contract_models import ValidationFinding, ValidationResult
from data_contract_review_agent.finding_classifier import classify_validation_result


def test_classification_core_mappings_and_summary_fields():
    result = ValidationResult(
        contract_name="contract_a",
        dataset_name="data.csv",
        row_count=10,
        column_count=2,
        findings=[
            ValidationFinding("f1", "missing_required_column", "id"),
            ValidationFinding("f2", "unexpected_column", "extra", severity="warning", status="warning"),
            ValidationFinding("f3", "uniqueness_violation", "id", status="skipped"),
        ],
    )

    classified = classify_validation_result(result)
    by_id = {item.finding_id: item for item in classified.classifications}
    assert classified.contract_name == "contract_a"
    assert classified.dataset_name == "data.csv"
    assert classified.row_count == 10
    assert classified.column_count == 2

    assert by_id["f1"].compatibility == "breaking"
    assert by_id["f1"].priority == "high"
    assert by_id["f1"].review_category == "schema_drift"

    assert by_id["f2"].compatibility == "review_needed"
    assert by_id["f2"].priority == "medium"
    assert by_id["f2"].review_category == "schema_drift"

    assert by_id["f3"].compatibility == "not_applicable"
    assert by_id["f3"].priority == "medium"
    assert by_id["f3"].review_category == "validation_setup"


def test_severity_affected_classifications_for_nullability_and_range():
    result = ValidationResult(
        contract_name="c",
        dataset_name="d",
        row_count=1,
        column_count=1,
        findings=[
            ValidationFinding("n1", "nullability_violation", "col", severity="error"),
            ValidationFinding("n2", "nullability_violation", "col", severity="warning"),
            ValidationFinding("r1", "range_violation", "col", severity="error"),
            ValidationFinding("r2", "range_violation", "col", severity="warning"),
        ],
    )

    classified = classify_validation_result(result)
    by_id = {item.finding_id: item for item in classified.classifications}
    assert by_id["n1"].compatibility == "breaking"
    assert by_id["n1"].priority == "high"
    assert by_id["n2"].compatibility == "review_needed"
    assert by_id["n2"].priority == "medium"
    assert by_id["r1"].compatibility == "breaking"
    assert by_id["r1"].priority == "high"
    assert by_id["r2"].compatibility == "review_needed"
    assert by_id["r2"].priority == "medium"
