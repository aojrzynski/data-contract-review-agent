from __future__ import annotations

import json

from pathlib import Path

from data_contract_review_agent.contract_models import DatasetMetadata, ValidationFinding, ValidationResult
from data_contract_review_agent.finding_classifier import classify_validation_result
from data_contract_review_agent.llm_summary import build_llm_summary_input, build_llm_summary_markdown
from data_contract_review_agent.profiling import build_dataset_profile
from data_contract_review_agent.review_mode import run_review_mode
from data_contract_review_agent.suggested_updates import build_suggested_contract_updates
from data_contract_review_agent.contract_loader import load_contract


class _FakeClient:
    class responses:
        @staticmethod
        def create(*, model: str, input: str):
            class _R:
                output_text = "# LLM-Polished Summary\n\n## Non-authoritative note\nok"
            return _R()


def _sample_validation() -> ValidationResult:
    return ValidationResult(
        contract_name="customer_contract",
        dataset_name="customers.csv",
        row_count=10,
        column_count=2,
        findings=[
            ValidationFinding(
                finding_id="f1",
                rule_type="type_mismatch",
                column="email",
                severity="error",
                status="failed",
                message="bad",
                evidence={"sample_failed_values": ["a@example.com"]},
            )
        ],
    )


def test_build_llm_summary_input_excludes_raw_samples_and_is_json_safe() -> None:
    validation = _sample_validation()
    classified = classify_validation_result(validation)
    import pandas as pd
    metadata = DatasetMetadata(
        source_path=Path("customers.csv"),
        file_name="customers.csv",
        file_extension=".csv",
        sheet_name=None,
        row_count=2,
        column_count=2,
        columns=["id", "email"],
    )
    profile = build_dataset_profile(pd.DataFrame({"id":[1,2],"email":["a@example.com","b@example.com"]}), metadata)
    updates = build_suggested_contract_updates(validation, load_contract("config/examples/customer_contract.yaml"), profile)
    payload = build_llm_summary_input(validation, classified, updates)
    serialized = json.dumps(payload)
    assert "sample_failed_values" not in serialized
    assert "a@example.com" not in serialized
    assert "counts_by_severity" in payload


def test_build_llm_summary_markdown_fallback_without_client() -> None:
    result = build_llm_summary_markdown({"dataset_name": "d", "contract_name": "c", "row_count": 1, "column_count": 1, "total_findings": 0, "counts_by_severity": {}, "counts_by_rule_type": {}, "counts_by_compatibility": {}, "counts_by_priority": {}, "artifact_names": []}, client=None)
    assert result.used_llm is False
    assert "Non-authoritative note" in result.summary_markdown


def test_build_llm_summary_markdown_with_fake_client() -> None:
    result = build_llm_summary_markdown({"dataset_name": "d"}, client=_FakeClient(), model="gpt-x")
    assert result.used_llm is True
    assert result.model == "gpt-x"
    assert "LLM-Polished Summary" in result.summary_markdown
