"""Output artifact writing for validation results.

Writers emit both human-readable and machine-readable artifacts from the same
deterministic evidence.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import yaml

from data_contract_review_agent.contract_models import DataContract, ValidationResult
from data_contract_review_agent.finding_classifier import ClassifiedValidationResult
from data_contract_review_agent.profiling import DatasetProfile
from data_contract_review_agent.reporting import build_markdown_validation_report
from data_contract_review_agent.serialization import make_json_safe, validation_finding_to_json_safe_dict
from data_contract_review_agent.suggested_updates import SuggestedContractUpdates
from data_contract_review_agent.trace_writer import write_contract_trace


def write_validation_outputs(
    output_dir: str | Path,
    validation_result: ValidationResult,
    classified_result: ClassifiedValidationResult,
    suggested_updates: SuggestedContractUpdates,
    profile: DatasetProfile,
    contract: DataContract,
) -> dict[str, Path]:
    """Persist the complete validate-mode artifact set in one output directory."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    report_path = output_path / "contract_validation_report.md"
    results_json_path = output_path / "contract_validation_results.json"
    failures_csv_path = output_path / "contract_failures.csv"
    trace_json_path = output_path / "contract_trace.json"
    suggested_updates_yaml_path = output_path / "suggested_contract_updates.yaml"

    report_content = build_markdown_validation_report(
        validation_result=validation_result,
        classified_result=classified_result,
        suggested_updates=suggested_updates,
        profile=profile,
        contract=contract,
    )
    report_path.write_text(report_content, encoding="utf-8")

    _write_results_json(results_json_path, validation_result, classified_result, suggested_updates)
    _write_failures_csv(failures_csv_path, validation_result, classified_result)
    write_contract_trace(trace_json_path, validation_result, classified_result, suggested_updates, profile, contract)
    _write_suggested_updates_yaml(suggested_updates_yaml_path, suggested_updates)

    return {
        "report": report_path,
        "results_json": results_json_path,
        "failures_csv": failures_csv_path,
        "trace_json": trace_json_path,
        "suggested_updates_yaml": suggested_updates_yaml_path,
    }


def _write_results_json(
    output_path: Path,
    validation_result: ValidationResult,
    classified_result: ClassifiedValidationResult,
    suggested_updates: SuggestedContractUpdates,
) -> None:
    """Write the full machine-readable validation result payload for automation."""
    payload = {
        "contract_name": validation_result.contract_name,
        "dataset_name": validation_result.dataset_name,
        "row_count": validation_result.row_count,
        "column_count": validation_result.column_count,
        "summary": {
            "total_findings": len(validation_result.findings),
            "by_severity": dict(sorted(Counter(f.severity for f in validation_result.findings).items())),
            "by_status": dict(sorted(Counter(f.status for f in validation_result.findings).items())),
            "by_rule_type": dict(sorted(Counter(f.rule_type for f in validation_result.findings).items())),
            "by_compatibility": dict(sorted(Counter(c.compatibility for c in classified_result.classifications).items())),
            "by_priority": dict(sorted(Counter(c.priority for c in classified_result.classifications).items())),
        },
        "findings": [validation_finding_to_json_safe_dict(finding) for finding in validation_result.findings],
        "classifications": [make_json_safe(asdict(item)) for item in classified_result.classifications],
        "suggested_updates": [make_json_safe(asdict(item)) for item in suggested_updates.suggestions],
    }
    output_path.write_text(json.dumps(make_json_safe(payload), indent=2, sort_keys=True), encoding="utf-8")


def _write_failures_csv(output_path: Path, validation_result: ValidationResult, classified_result: ClassifiedValidationResult) -> None:
    """Write finding-level triage rows for spreadsheet-style review workflows."""
    headers = [
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
    ]
    by_id = {item.finding_id: item for item in classified_result.classifications}

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for finding in validation_result.findings:
            classification = by_id.get(finding.finding_id)
            writer.writerow(
                {
                    "finding_id": finding.finding_id,
                    "rule_type": finding.rule_type,
                    "column": finding.column or "",
                    "columns": "|".join(finding.columns),
                    "severity": finding.severity,
                    "status": finding.status,
                    "compatibility": classification.compatibility if classification else "",
                    "priority": classification.priority if classification else "",
                    "review_category": classification.review_category if classification else "",
                    "message": finding.message,
                    "suggested_action": finding.suggested_action or "",
                    "recommended_human_action": classification.recommended_human_action if classification else "",
                }
            )


def _write_suggested_updates_yaml(output_path: Path, suggested_updates: SuggestedContractUpdates) -> None:
    """Write advisory, non-mutating contract update suggestions for human governance."""
    payload = {
        "contract_name": suggested_updates.contract_name,
        "dataset_name": suggested_updates.dataset_name,
        "human_review_required": True,
        "note": "Suggested contract updates are not applied automatically.",
        "suggestions": [make_json_safe(asdict(item)) for item in suggested_updates.suggestions],
    }
    output_path.write_text(yaml.safe_dump(make_json_safe(payload), sort_keys=True), encoding="utf-8")
