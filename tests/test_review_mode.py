from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from data_contract_review_agent.contract_models import (
    ColumnContract,
    ContractMetadata,
    DataContract,
    DatasetExpectation,
    DatasetMetadata,
    SchemaExpectation,
    ValidationFinding,
    ValidationResult,
)
from data_contract_review_agent.finding_classifier import classify_validation_result
from data_contract_review_agent.profiling import build_dataset_profile
from data_contract_review_agent.review_mode import run_review_mode, review_mode_to_json_safe_dict
from data_contract_review_agent.review_reporting import build_agent_review_report
from data_contract_review_agent.suggested_updates import build_suggested_contract_updates


def _bundle(findings: list[ValidationFinding]):
    df = pd.DataFrame({"id": [1, 2, None], "status": ["ok", "bad", "ok"], "extra": ["x", "y", "z"]})
    metadata = DatasetMetadata(Path('/tmp/customers.csv'), 'customers.csv', '.csv', None, 3, 3, ['id','status','extra'])
    profile = build_dataset_profile(df, metadata)
    contract = DataContract(
        contract=ContractMetadata(name='customer_contract'),
        dataset=DatasetExpectation(),
        schema=SchemaExpectation(),
        columns={"id": ColumnContract(type="integer", nullable=False), "status": ColumnContract(type="string")},
    )
    result = ValidationResult('customer_contract', 'customers.csv', 3, 3, findings)
    classified = classify_validation_result(result)
    suggestions = build_suggested_contract_updates(result, contract, profile)
    return result, classified, suggestions, profile, contract


def test_review_mode_recommendations_and_authority_boundary() -> None:
    findings = [
        ValidationFinding('f1', 'type_mismatch', 'id', severity='error', status='failed'),
        ValidationFinding('f2', 'unexpected_column', 'extra', severity='warning', status='failed'),
        ValidationFinding('f3', 'nullability_violation', 'id', severity='error', status='failed'),
        ValidationFinding('f4', 'row_count_violation', None, severity='warning', status='failed'),
    ]
    result, classified, suggestions, profile, contract = _bundle(findings)
    review = run_review_mode(result, classified, suggestions, profile, contract, {"report": Path("out/report.md")})

    assert review.contract_name == 'customer_contract'
    assert review.authority_boundary['llm_used'] is False
    assert review.authority_boundary['llm_used_for_validation'] is False
    assert review.authority_boundary['llm_used_for_review_recommendations'] is False
    assert review.authority_boundary['llm_summary_requested'] is False
    assert review.authority_boundary['llm_summary_artifact'] is None
    categories = {r.category for r in review.recommendations}
    assert 'schema_drift' in categories
    assert 'contract_review' in categories
    assert 'data_quality' in categories
    assert 'operational_review' in categories
    assert 'contract_governance' in categories


def test_review_mode_no_findings_creates_low_priority_recommendation() -> None:
    result, classified, suggestions, profile, contract = _bundle([])
    review = run_review_mode(result, classified, suggestions, profile, contract, {"report": Path("out/report.md")})

    assert any(r.category == 'validation_result' and r.priority == 'low' for r in review.recommendations)


def test_review_report_and_trace_are_stable_json_safe() -> None:
    result, classified, suggestions, profile, contract = _bundle([])
    review = run_review_mode(result, classified, suggestions, profile, contract, {"report": Path("out/report.md")})
    report = build_agent_review_report(review)

    assert '# Agent Review Report' in report
    assert '## Recommended next actions' in report
    assert '## Review steps' in report
    assert '## Authority boundary' in report
    assert 'does not use an LLM to create validation evidence or recommendations' in report

    payload = review_mode_to_json_safe_dict(review)
    dumped = json.dumps(payload, indent=2, sort_keys=True)
    loaded = json.loads(dumped)
    assert set(loaded.keys()) == {
        'contract_name', 'dataset_name', 'overall_status', 'findings_total', 'recommendations', 'steps', 'artifacts', 'authority_boundary'
    }
