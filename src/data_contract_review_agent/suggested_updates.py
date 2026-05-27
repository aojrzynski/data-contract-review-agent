"""Build structured suggested contract updates from validation findings."""

from __future__ import annotations

from dataclasses import dataclass, field

from data_contract_review_agent.contract_models import DataContract, ValidationFinding, ValidationResult
from data_contract_review_agent.profiling import DatasetProfile
from data_contract_review_agent.serialization import make_json_safe


@dataclass(slots=True)
class SuggestedContractUpdate:
    suggestion_id: str
    suggestion_type: str
    target_path: str
    column: str | None
    proposed_change: dict[str, object]
    confidence: str
    reason: str
    evidence: dict[str, object]
    human_decision_required: bool = True


@dataclass(slots=True)
class SuggestedContractUpdates:
    contract_name: str
    dataset_name: str
    suggestions: list[SuggestedContractUpdate] = field(default_factory=list)


def _build_update_from_finding(finding: ValidationFinding, profile: DatasetProfile) -> SuggestedContractUpdate | None:
    column = finding.column
    suggestion_id = f"{finding.rule_type}:{column or 'dataset'}"

    if finding.rule_type == "unexpected_column" and column and column in profile.columns:
        observed = profile.columns[column]
        evidence = {
            "observed_type": observed.observed_logical_type,
            "null_count": observed.null_count,
            "non_null_count": observed.non_null_count,
            "sample_values": observed.sample_values,
            "top_values": [{"value": item.value, "count": item.count} for item in observed.top_values],
        }
        proposed_change = {
            "required": False,
            "type": observed.observed_logical_type,
            "nullable": observed.null_count > 0,
            "description": "Suggested from observed dataset column. Review before accepting.",
        }
        return SuggestedContractUpdate(
            suggestion_id=suggestion_id,
            suggestion_type="add_unexpected_column",
            target_path=f"columns.{column}",
            column=column,
            proposed_change=make_json_safe(proposed_change),  # type: ignore[arg-type]
            confidence="medium",
            reason="Column appeared in the dataset but is not declared in the contract.",
            evidence=make_json_safe(evidence),  # type: ignore[arg-type]
        )

    if finding.rule_type == "allowed_values_violation" and column:
        unexpected_values = finding.evidence.get("unexpected_values", {})
        candidates = list(unexpected_values.keys()) if isinstance(unexpected_values, dict) else []
        return SuggestedContractUpdate(
            suggestion_id=suggestion_id,
            suggestion_type="review_allowed_values",
            target_path=f"columns.{column}.allowed_values",
            column=column,
            proposed_change=make_json_safe({"candidate_values": candidates}),  # type: ignore[arg-type]
            confidence="medium",
            reason="Dataset contains values outside the declared allowed_values.",
            evidence=make_json_safe(finding.evidence),  # type: ignore[arg-type]
        )

    if finding.rule_type == "nullability_violation" and column:
        return SuggestedContractUpdate(
            suggestion_id=suggestion_id,
            suggestion_type="review_nullability",
            target_path=f"columns.{column}.nullable",
            column=column,
            proposed_change={"nullable": True},
            confidence="low",
            reason="Nulls were observed in a column declared as non-nullable. Confirm data quality before loosening contract constraints.",
            evidence=make_json_safe({**finding.evidence, "note": "Not an automatic recommendation to relax the contract."}),  # type: ignore[arg-type]
        )

    if finding.rule_type == "type_mismatch" and column:
        return SuggestedContractUpdate(
            suggestion_id=suggestion_id,
            suggestion_type="review_type",
            target_path=f"columns.{column}.type",
            column=column,
            proposed_change=make_json_safe({"observed_type": finding.evidence.get("observed_type")}),  # type: ignore[arg-type]
            confidence="low",
            reason="Observed type differs from declared type.",
            evidence=make_json_safe(finding.evidence),  # type: ignore[arg-type]
        )

    if finding.rule_type == "freshness_violation" and column:
        return SuggestedContractUpdate(
            suggestion_id=suggestion_id,
            suggestion_type="review_refresh_process",
            target_path=f"columns.{column}.freshness",
            column=column,
            proposed_change={},
            confidence="medium",
            reason="Latest observed value is older than the allowed freshness window.",
            evidence=make_json_safe(finding.evidence),  # type: ignore[arg-type]
        )

    if finding.rule_type == "row_count_violation":
        return SuggestedContractUpdate(
            suggestion_id=suggestion_id,
            suggestion_type="review_row_count_bounds",
            target_path="row_count",
            column=None,
            proposed_change=make_json_safe({"observed_row_count": finding.evidence.get("observed_row_count")}),  # type: ignore[arg-type]
            confidence="low",
            reason="Observed row volume is outside declared bounds; review extraction behavior or row_count expectations.",
            evidence=make_json_safe(finding.evidence),  # type: ignore[arg-type]
        )

    return None


def build_suggested_contract_updates(
    result: ValidationResult,
    contract: DataContract,
    profile: DatasetProfile,
    max_suggestions: int = 20,
) -> SuggestedContractUpdates:
    _ = contract
    suggestions: list[SuggestedContractUpdate] = []
    for finding in result.findings:
        suggestion = _build_update_from_finding(finding, profile)
        if suggestion is not None:
            suggestions.append(suggestion)
        if len(suggestions) >= max_suggestions:
            break

    return SuggestedContractUpdates(
        contract_name=result.contract_name,
        dataset_name=result.dataset_name,
        suggestions=suggestions,
    )
