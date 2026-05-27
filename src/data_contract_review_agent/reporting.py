"""Markdown report generation for deterministic validation outputs."""

from __future__ import annotations

from collections import Counter

from data_contract_review_agent.contract_models import DataContract, ValidationResult
from data_contract_review_agent.finding_classifier import ClassifiedValidationResult
from data_contract_review_agent.profiling import DatasetProfile
from data_contract_review_agent.suggested_updates import SuggestedContractUpdates


def _markdown_table(title: str, counts: Counter[str]) -> list[str]:
    lines = [f"## {title}", "| category | count |", "|---|---:|"]
    for key in sorted(counts):
        lines.append(f"| {key} | {counts[key]} |")
    if not counts:
        lines.append("| none | 0 |")
    lines.append("")
    return lines


def build_markdown_validation_report(
    validation_result: ValidationResult,
    classified_result: ClassifiedValidationResult,
    suggested_updates: SuggestedContractUpdates,
    profile: DatasetProfile,
    contract: DataContract,
) -> str:
    _ = profile
    severity_counts: Counter[str] = Counter(f.severity for f in validation_result.findings)
    compatibility_counts: Counter[str] = Counter(c.compatibility for c in classified_result.classifications)

    has_failed = any(f.status == "failed" and f.severity == "error" for f in validation_result.findings)
    has_review_needed = any(
        f.severity in {"warning"} or f.status in {"skipped", "review_needed"}
        for f in validation_result.findings
    )

    if has_failed:
        overall_status = "Failed"
    elif has_review_needed:
        overall_status = "Review needed"
    else:
        overall_status = "Passed"

    lines = [
        "# Data Contract Validation Report",
        "",
        "## Run summary",
        f"- Contract: {contract.contract.name}",
        f"- Dataset: {validation_result.dataset_name}",
        f"- Rows: {validation_result.row_count}",
        f"- Columns: {validation_result.column_count}",
        f"- Total findings: {len(validation_result.findings)}",
        f"- Errors: {severity_counts.get('error', 0)}",
        f"- Warnings: {severity_counts.get('warning', 0)}",
        f"- Skipped: {sum(1 for finding in validation_result.findings if finding.status == 'skipped')}",
        "",
        "## Overall status",
        f"- {overall_status}",
        "",
    ]

    lines.extend(_markdown_table("Findings by severity", severity_counts))
    lines.extend(_markdown_table("Findings by compatibility", compatibility_counts))

    lines.extend(["## High-priority findings"])
    high_priority = [c for c in classified_result.classifications if c.priority == "high"]
    if not high_priority:
        lines.append("No high-priority findings.")
    else:
        for classification in high_priority:
            finding = next((f for f in validation_result.findings if f.finding_id == classification.finding_id), None)
            message = finding.message if finding else ""
            column = finding.column if finding else None
            lines.extend(
                [
                    f"- Rule: {classification.rule_type}",
                    f"  - Column: {column or '-'}",
                    f"  - Message: {message}",
                    f"  - Recommended action: {classification.recommended_human_action}",
                ]
            )
    lines.append("")

    lines.append("## Suggested contract review actions")
    if not suggested_updates.suggestions:
        lines.append("No contract update suggestions were generated.")
    else:
        for suggestion in suggested_updates.suggestions:
            lines.extend(
                [
                    f"- Type: {suggestion.suggestion_type}",
                    f"  - Target: {suggestion.target_path}",
                    f"  - Confidence: {suggestion.confidence}",
                    f"  - Reason: {suggestion.reason}",
                ]
            )
    lines.extend(
        [
            "",
            "## Authority boundary",
            "The deterministic validators are the source of truth for pass/fail evidence. Suggested contract updates are review prompts only and are not applied automatically.",
            "",
        ]
    )

    return "\n".join(lines)
