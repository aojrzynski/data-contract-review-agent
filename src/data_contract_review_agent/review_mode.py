"""Deterministic, bounded review-mode orchestration.

Review mode coordinates deterministic findings into grouped recommendations and
trace steps. It is intentionally authority-bounded: validators decide truth,
while review mode organizes how humans consume that truth.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from data_contract_review_agent.contract_models import DataContract, ValidationResult
from data_contract_review_agent.finding_classifier import ClassifiedValidationResult
from data_contract_review_agent.profiling import DatasetProfile
from data_contract_review_agent.serialization import make_json_safe
from data_contract_review_agent.suggested_updates import SuggestedContractUpdates


@dataclass(frozen=True)
class ReviewStep:
    step_name: str
    status: str
    summary: str
    evidence: dict[str, object]


@dataclass(frozen=True)
class ReviewRecommendation:
    recommendation_id: str
    priority: str
    category: str
    recommendation: str
    rationale: str
    linked_finding_ids: list[str]


@dataclass(frozen=True)
class ReviewModeResult:
    contract_name: str
    dataset_name: str
    overall_status: str
    findings_total: int
    recommendations: list[ReviewRecommendation]
    steps: list[ReviewStep]
    artifacts: dict[str, str]
    authority_boundary: dict[str, object]


def run_review_mode(
    validation_result: ValidationResult,
    classified_result: ClassifiedValidationResult,
    suggested_updates: SuggestedContractUpdates,
    profile: DatasetProfile,
    contract: DataContract,
    validation_artifacts: dict[str, Path],
) -> ReviewModeResult:
    recommendations = _build_recommendations(classified_result, suggested_updates)
    findings_total = len(validation_result.findings)

    steps = [
        ReviewStep("dataset_loaded", "completed", "Dataset was loaded for deterministic validation.", {"dataset_name": validation_result.dataset_name}),
        ReviewStep("contract_loaded", "completed", "Data contract was loaded from local configuration.", {"contract_name": contract.contract.name, "contract_version": contract.contract.version}),
        ReviewStep("profile_built", "completed", "Dataset profile was built for contract checks.", {"profiled_columns": len(profile.columns)}),
        ReviewStep("validation_completed", "completed", "Deterministic validators completed.", {"findings_total": findings_total}),
        ReviewStep("findings_classified", "completed", "Findings were classified for triage.", {"classified_findings": len(classified_result.classifications)}),
        ReviewStep("suggestions_generated", "completed", "Suggested contract updates were generated for human review.", {"suggestions_total": len(suggested_updates.suggestions)}),
        ReviewStep("artifacts_written", "completed", "Validation artifacts were written.", {"artifact_count": len(validation_artifacts)}),
        ReviewStep("review_completed", "completed", "Deterministic review summary and guidance completed.", {"recommendations_total": len(recommendations)}),
    ]

    authority_boundary = {
        "deterministic_validation_is_authoritative": True,
        "review_mode_is_orchestration_only": True,
        "suggestions_are_applied_automatically": False,
        "llm_used": False,
        "llm_used_for_validation": False,
        "llm_used_for_review_recommendations": False,
        "llm_summary_requested": "llm_summary" in validation_artifacts,
        "llm_summary_artifact": str(validation_artifacts["llm_summary"]) if "llm_summary" in validation_artifacts else None,
    }

    return ReviewModeResult(
        contract_name=validation_result.contract_name,
        dataset_name=validation_result.dataset_name,
        overall_status=_determine_overall_status(classified_result),
        findings_total=findings_total,
        recommendations=recommendations,
        steps=steps,
        artifacts={key: str(value) for key, value in validation_artifacts.items()},
        authority_boundary=authority_boundary,
    )


def review_mode_to_json_safe_dict(review_result: ReviewModeResult) -> dict[str, object]:
    return make_json_safe(asdict(review_result))


def _build_recommendations(
    classified_result: ClassifiedValidationResult,
    suggested_updates: SuggestedContractUpdates,
) -> list[ReviewRecommendation]:
    by_rule_type: dict[str, list[str]] = {}
    for finding in classified_result.classifications:
        by_rule_type.setdefault(finding.rule_type, []).append(finding.finding_id)

    recommendations: list[ReviewRecommendation] = []

    schema_ids = _collect_ids(by_rule_type, {"missing_required_column", "type_mismatch"})
    if schema_ids:
        recommendations.append(
            ReviewRecommendation(
                "rec_schema_drift",
                "high",
                "schema_drift",
                "Review upstream schema changes before accepting this dataset.",
                "Schema-level contract mismatches can break downstream assumptions.",
                schema_ids,
            )
        )

    dq_rule_types = {
        "nullability_violation",
        "uniqueness_violation",
        "range_violation",
        "pattern_violation",
        "length_violation",
        "allowed_values_violation",
    }
    dq_ids = _collect_ids(by_rule_type, dq_rule_types)
    if dq_ids:
        has_error = any(
            item.status == "failed" and item.severity == "error" and item.finding_id in dq_ids
            for item in classified_result.classifications
        )
        recommendations.append(
            ReviewRecommendation(
                "rec_data_quality",
                "high" if has_error else "medium",
                "data_quality",
                "Triage data quality issues and decide whether the source data or contract needs correction.",
                "Data quality findings indicate value-level drift against explicit constraints.",
                dq_ids,
            )
        )

    unexpected_ids = _collect_ids(by_rule_type, {"unexpected_column"})
    if unexpected_ids:
        recommendations.append(
            ReviewRecommendation(
                "rec_contract_review",
                "medium",
                "contract_review",
                "Review unexpected columns and decide whether they represent valid contract evolution.",
                "Unexpected columns may indicate useful evolution or accidental schema drift.",
                unexpected_ids,
            )
        )

    operational_ids = _collect_ids(by_rule_type, {"freshness_violation", "row_count_violation"})
    if operational_ids:
        recommendations.append(
            ReviewRecommendation(
                "rec_operational_review",
                "medium",
                "operational_review",
                "Check extraction freshness, completeness, or volume expectations.",
                "Operational findings can indicate ingestion or scheduling issues.",
                operational_ids,
            )
        )

    if suggested_updates.suggestions:
        recommendations.append(
            ReviewRecommendation(
                "rec_contract_governance",
                "medium",
                "contract_governance",
                "Review suggested contract updates. They are not applied automatically.",
                "Suggested updates are assistive and require explicit human governance.",
                [],
            )
        )

    if not classified_result.classifications:
        recommendations.append(
            ReviewRecommendation(
                "rec_no_findings",
                "low",
                "validation_result",
                "No validation issues found. Keep existing contract controls in place.",
                "No failed validations were detected in this deterministic run.",
                [],
            )
        )

    return recommendations


def _collect_ids(by_rule_type: dict[str, list[str]], rule_types: set[str]) -> list[str]:
    collected: list[str] = []
    for rule_type in sorted(rule_types):
        collected.extend(by_rule_type.get(rule_type, []))
    return collected


def _determine_overall_status(classified_result: ClassifiedValidationResult) -> str:
    has_failed_error = any(
        item.status == "failed" and item.severity == "error" for item in classified_result.classifications
    )
    if has_failed_error:
        return "Failed"
    if classified_result.classifications:
        return "Review needed"
    return "Passed"
