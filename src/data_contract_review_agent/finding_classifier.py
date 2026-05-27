"""Classification of validation findings for practical contract review workflows."""

from __future__ import annotations

from dataclasses import dataclass, field

from data_contract_review_agent.contract_models import ValidationFinding, ValidationResult


@dataclass(slots=True)
class FindingClassification:
    finding_id: str
    rule_type: str
    severity: str
    status: str
    compatibility: str
    priority: str
    review_category: str
    rationale: str
    recommended_human_action: str


@dataclass(slots=True)
class ClassifiedValidationResult:
    contract_name: str
    dataset_name: str
    row_count: int
    column_count: int
    classifications: list[FindingClassification] = field(default_factory=list)


def _classify_finding(finding: ValidationFinding) -> FindingClassification:
    if finding.status == "skipped":
        return FindingClassification(
            finding_id=finding.finding_id,
            rule_type=finding.rule_type,
            severity=finding.severity,
            status=finding.status,
            compatibility="not_applicable",
            priority="medium",
            review_category="validation_setup",
            rationale="Validation was skipped and needs setup or prerequisite fixes before interpretation.",
            recommended_human_action="Resolve setup prerequisites, then rerun validation.",
        )

    mapping = {
        "missing_required_column": ("breaking", "high", "schema_drift"),
        "type_mismatch": ("breaking", "high", "schema_drift"),
        "unexpected_column": ("review_needed", "medium", "schema_drift"),
        "pattern_violation": ("review_needed", "medium", "format"),
        "length_violation": ("review_needed", "medium", "format"),
        "freshness_violation": ("review_needed", "medium", "timeliness"),
        "row_count_violation": ("review_needed", "medium", "volume"),
    }

    if finding.rule_type == "nullability_violation":
        compatibility = "breaking" if finding.severity == "error" else "review_needed"
        priority = "high" if finding.severity == "error" else "medium"
        category = "data_quality"
    elif finding.rule_type == "uniqueness_violation":
        compatibility = "breaking" if finding.status == "failed" else "review_needed"
        priority = "high" if finding.status == "failed" else "medium"
        category = "data_quality"
    elif finding.rule_type == "allowed_values_violation":
        compatibility = "review_needed"
        priority = "high" if finding.severity == "error" else "medium"
        category = "domain_values"
    elif finding.rule_type == "range_violation":
        compatibility = "breaking" if finding.severity == "error" else "review_needed"
        priority = "high" if finding.severity == "error" else "medium"
        category = "data_quality"
    elif finding.rule_type in mapping:
        compatibility, priority, category = mapping[finding.rule_type]
    else:
        compatibility, priority, category = "review_needed", "low", "validation_setup"

    return FindingClassification(
        finding_id=finding.finding_id,
        rule_type=finding.rule_type,
        severity=finding.severity,
        status=finding.status,
        compatibility=compatibility,
        priority=priority,
        review_category=category,
        rationale=f"Rule '{finding.rule_type}' was classified as {compatibility} with {priority} priority.",
        recommended_human_action=finding.suggested_action or "Review finding evidence and determine next contract or data action.",
    )


def classify_validation_result(result: ValidationResult) -> ClassifiedValidationResult:
    classifications = [_classify_finding(finding) for finding in result.findings]
    return ClassifiedValidationResult(
        contract_name=result.contract_name,
        dataset_name=result.dataset_name,
        row_count=result.row_count,
        column_count=result.column_count,
        classifications=classifications,
    )
