"""Trace artifact writer for deterministic validation review context."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from data_contract_review_agent.contract_models import DataContract, ValidationResult
from data_contract_review_agent.finding_classifier import ClassifiedValidationResult
from data_contract_review_agent.profiling import DatasetProfile
from data_contract_review_agent.serialization import make_json_safe
from data_contract_review_agent.suggested_updates import SuggestedContractUpdates


def write_contract_trace(
    output_path: str | Path,
    validation_result: ValidationResult,
    classified_result: ClassifiedValidationResult,
    suggested_updates: SuggestedContractUpdates,
    profile: DatasetProfile,
    contract: DataContract,
) -> Path:
    """Write a compact trace payload that makes validate-mode orchestration auditable."""
    trace_payload = {
        "input_summary": {
            "contract_name": contract.contract.name,
            "dataset_name": validation_result.dataset_name,
            "row_count": validation_result.row_count,
            "column_count": validation_result.column_count,
            "contract_version": contract.contract.version,
        },
        "profile_summary": {
            "columns": [
                {
                    "name": name,
                    "observed_logical_type": column.observed_logical_type,
                    "null_count": column.null_count,
                    "distinct_count": column.distinct_count,
                }
                for name, column in sorted(profile.columns.items())
            ]
        },
        "validation_summary": {
            "total_findings": len(validation_result.findings),
            "by_rule_type": dict(sorted(Counter(item.rule_type for item in validation_result.findings).items())),
            "by_severity": dict(sorted(Counter(item.severity for item in validation_result.findings).items())),
            "by_status": dict(sorted(Counter(item.status for item in validation_result.findings).items())),
        },
        "classification_summary": {
            "by_compatibility": dict(sorted(Counter(item.compatibility for item in classified_result.classifications).items())),
            "by_priority": dict(sorted(Counter(item.priority for item in classified_result.classifications).items())),
            "by_review_category": dict(sorted(Counter(item.review_category for item in classified_result.classifications).items())),
        },
        "suggested_update_summary": {
            "total_suggestions": len(suggested_updates.suggestions),
            "by_suggestion_type": dict(sorted(Counter(item.suggestion_type for item in suggested_updates.suggestions).items())),
        },
        "authority_boundary": {
            "deterministic_validation_is_authoritative": True,
            "suggestions_are_applied_automatically": False,
            "llm_used": False,
        },
    }

    output = Path(output_path)
    output.write_text(json.dumps(make_json_safe(trace_payload), indent=2, sort_keys=True), encoding="utf-8")
    return output
