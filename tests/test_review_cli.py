from __future__ import annotations

import json
from pathlib import Path

from data_contract_review_agent.cli import run_cli


ROOT = Path(__file__).resolve().parents[1]


def test_review_mode_writes_validation_and_agent_artifacts(tmp_path: Path, capsys) -> None:
    output_dir = tmp_path / 'review_outputs'
    code = run_cli(
        [
            '--mode', 'review',
            '--input', str(ROOT / 'sample_data/customers/customers_contract_failures.csv'),
            '--contract', str(ROOT / 'config/examples/customer_contract.yaml'),
            '--output-dir', str(output_dir),
            '--fail-on', 'never',
        ]
    )
    assert code == 0
    assert (output_dir / 'contract_validation_report.md').exists()
    assert (output_dir / 'contract_validation_results.json').exists()
    assert (output_dir / 'contract_failures.csv').exists()
    assert (output_dir / 'contract_trace.json').exists()
    assert (output_dir / 'suggested_contract_updates.yaml').exists()
    assert (output_dir / 'agent_review_report.md').exists()
    assert (output_dir / 'agent_trace.json').exists()

    out = capsys.readouterr().out
    assert 'mode: review' in out
    assert 'recommendations_total:' in out


def test_review_mode_exit_code_respects_fail_on_error(tmp_path: Path) -> None:
    output_dir = tmp_path / 'review_outputs'
    code = run_cli(
        [
            '--mode', 'review',
            '--input', str(ROOT / 'sample_data/customers/customers_contract_failures.csv'),
            '--contract', str(ROOT / 'config/examples/customer_contract.yaml'),
            '--output-dir', str(output_dir),
        ]
    )
    assert code == 1


def test_review_artifact_map_includes_agent_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / 'review_outputs'
    code = run_cli(
        [
            '--mode', 'review',
            '--input', str(ROOT / 'sample_data/customers/customers_contract_failures.csv'),
            '--contract', str(ROOT / 'config/examples/customer_contract.yaml'),
            '--output-dir', str(output_dir),
            '--fail-on', 'never',
        ]
    )
    assert code == 0

    report_text = (output_dir / 'agent_review_report.md').read_text(encoding='utf-8')
    assert '- agent_review_report:' in report_text
    assert '- agent_trace_json:' in report_text

    trace_payload = json.loads((output_dir / 'agent_trace.json').read_text(encoding='utf-8'))
    assert 'artifacts' in trace_payload
    assert 'agent_review_report' in trace_payload['artifacts']
    assert 'agent_trace_json' in trace_payload['artifacts']


def test_llm_summary_still_not_implemented() -> None:
    code = run_cli(['--llm-summary'])
    assert code == 2
