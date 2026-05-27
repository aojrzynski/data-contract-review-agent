"""Build bounded LLM-polished summaries from deterministic evidence.

The payload is intentionally compact and excludes raw rows/row-level samples.
This keeps the LLM layer non-authoritative and scoped to wording polish.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass

from data_contract_review_agent.finding_classifier import ClassifiedValidationResult
from data_contract_review_agent.llm_client import DEFAULT_LLM_MODEL, call_openai_summary, create_openai_client
from data_contract_review_agent.review_mode import ReviewModeResult
from data_contract_review_agent.suggested_updates import SuggestedContractUpdates
from data_contract_review_agent.contract_models import ValidationResult


@dataclass(frozen=True)
class LLMSummaryResult:
    used_llm: bool
    provider: str
    model: str | None
    summary_markdown: str
    fallback_reason: str | None


def build_llm_summary_input(
    validation_result: ValidationResult,
    classified_result: ClassifiedValidationResult,
    suggested_updates: SuggestedContractUpdates,
    review_result: ReviewModeResult | None = None,
) -> dict[str, object]:
    severity_counts = dict(sorted(Counter(f.severity for f in validation_result.findings).items()))
    rule_type_counts = dict(sorted(Counter(f.rule_type for f in validation_result.findings).items()))
    compatibility_counts = dict(sorted(Counter(c.compatibility for c in classified_result.classifications).items()))
    priority_counts = dict(sorted(Counter(c.priority for c in classified_result.classifications).items()))

    payload: dict[str, object] = {
        "contract_name": validation_result.contract_name,
        "dataset_name": validation_result.dataset_name,
        "row_count": validation_result.row_count,
        "column_count": validation_result.column_count,
        "total_findings": len(validation_result.findings),
        "counts_by_severity": severity_counts,
        "counts_by_rule_type": rule_type_counts,
        "counts_by_compatibility": compatibility_counts,
        "counts_by_priority": priority_counts,
        "suggested_updates": [
            {
                "suggestion_id": s.suggestion_id,
                "suggestion_type": s.suggestion_type,
                "target_path": s.target_path,
                "confidence": s.confidence,
                "reason": s.reason,
            }
            for s in suggested_updates.suggestions
        ],
        "authority_boundary": "Deterministic validation artifacts remain the source of truth; this summary is optional wording polish only.",
        "artifact_names": [
            "contract_validation_report.md",
            "contract_validation_results.json",
            "contract_failures.csv",
            "contract_trace.json",
            "suggested_contract_updates.yaml",
            "llm_summary.md",
        ],
    }

    if review_result is not None:
        payload["review_recommendations"] = [
            {
                "recommendation_id": rec.recommendation_id,
                "priority": rec.priority,
                "category": rec.category,
                "recommendation": rec.recommendation,
            }
            for rec in review_result.recommendations
        ]

    return json.loads(json.dumps(payload, sort_keys=True))


def build_llm_summary_markdown(
    summary_payload: dict[str, object],
    model: str | None = None,
    client: object | None = None,
) -> LLMSummaryResult:
    chosen_model = model or DEFAULT_LLM_MODEL
    availability_reason: str | None = None
    if client is None:
        availability = create_openai_client()
        client = availability.client
        availability_reason = availability.reason

    if client is None:
        fallback_reason = "OpenAI client or OPENAI_API_KEY was not available; wrote deterministic fallback summary."
        if availability_reason:
            fallback_reason = f"{fallback_reason} ({availability_reason})"
        return LLMSummaryResult(
            used_llm=False,
            provider="openai",
            model=chosen_model,
            summary_markdown=_build_fallback_markdown(summary_payload, fallback_reason),
            fallback_reason=fallback_reason,
        )

    prompt = _build_prompt(summary_payload)
    try:
        markdown = call_openai_summary(client=client, prompt=prompt, model=chosen_model)
    except Exception as exc:
        fallback_reason = f"OpenAI client or OPENAI_API_KEY was not available; wrote deterministic fallback summary. ({exc})"
        return LLMSummaryResult(
            used_llm=False,
            provider="openai",
            model=chosen_model,
            summary_markdown=_build_fallback_markdown(summary_payload, fallback_reason),
            fallback_reason=fallback_reason,
        )

    return LLMSummaryResult(
        used_llm=True,
        provider="openai",
        model=chosen_model,
        summary_markdown=markdown,
        fallback_reason=None,
    )


def _build_prompt(summary_payload: dict[str, object]) -> str:
    payload_text = json.dumps(summary_payload, indent=2, sort_keys=True)
    return (
        "Write markdown with this exact structure:\n"
        "# LLM-Polished Summary\n"
        "## Non-authoritative note\n"
        "## Run overview\n"
        "## Main issues to review\n"
        "## Suggested next actions\n"
        "## Artifact pointers\n\n"
        "Rules: Use only the deterministic payload below. Do not invent findings. "
        "Do not propose automatic contract changes. Keep concise and operational.\n\n"
        f"Deterministic payload:\n{payload_text}"
    )


def _build_fallback_markdown(summary_payload: dict[str, object], reason: str) -> str:
    return (
        "# LLM-Polished Summary\n\n"
        "## Non-authoritative note\n"
        "This summary is wording polish only. Deterministic validation artifacts remain the source of truth.\n\n"
        "## Run overview\n"
        f"- Dataset: {summary_payload.get('dataset_name')}\n"
        f"- Contract: {summary_payload.get('contract_name')}\n"
        f"- Rows: {summary_payload.get('row_count')}\n"
        f"- Columns: {summary_payload.get('column_count')}\n"
        f"- Total findings: {summary_payload.get('total_findings')}\n"
        f"- Findings by severity: {summary_payload.get('counts_by_severity')}\n\n"
        "## Main issues to review\n"
        f"- Findings by rule type: {summary_payload.get('counts_by_rule_type')}\n"
        f"- Compatibility counts: {summary_payload.get('counts_by_compatibility')}\n"
        f"- Priority counts: {summary_payload.get('counts_by_priority')}\n\n"
        "## Suggested next actions\n"
        "- Review deterministic recommendations and suggested updates before changing contracts.\n"
        "- Do not apply suggested updates automatically.\n\n"
        "## Artifact pointers\n"
        f"- Artifacts: {summary_payload.get('artifact_names')}\n"
        f"- llm_fallback_reason: {reason}\n"
    )
