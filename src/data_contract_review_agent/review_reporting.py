"""Agent-style review reporting for deterministic review mode."""

from __future__ import annotations

from data_contract_review_agent.review_mode import ReviewModeResult


def build_agent_review_report(review_result: ReviewModeResult) -> str:
    lines = [
        "# Agent Review Report",
        "",
        "## Review summary",
        f"- Contract: {review_result.contract_name}",
        f"- Dataset: {review_result.dataset_name}",
        f"- Overall status: {review_result.overall_status}",
        f"- Total findings: {review_result.findings_total}",
        f"- Recommendations: {len(review_result.recommendations)}",
        "",
        "## Recommended next actions",
    ]
    for rec in review_result.recommendations:
        linked = ", ".join(rec.linked_finding_ids) if rec.linked_finding_ids else "none"
        lines.extend(
            [
                f"- **{rec.recommendation_id}**",
                f"  - priority: {rec.priority}",
                f"  - category: {rec.category}",
                f"  - recommendation: {rec.recommendation}",
                f"  - rationale: {rec.rationale}",
                f"  - linked_finding_ids: {linked}",
            ]
        )

    lines.extend(["", "## Review steps"])
    for step in review_result.steps:
        lines.append(f"- {step.step_name}: {step.status} — {step.summary}")

    lines.extend(["", "## Artifact map"])
    for key, value in sorted(review_result.artifacts.items()):
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "## Authority boundary",
            "Review mode is a deterministic orchestration layer. It does not replace the validation evidence. "
            "Suggested contract updates are not applied automatically. No LLM was used in this run.",
        ]
    )

    return "\n".join(lines) + "\n"
