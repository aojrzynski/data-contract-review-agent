from __future__ import annotations

import json
from pathlib import Path

from data_contract_review_agent.cli import run_cli


VALID_INPUT = Path("sample_data/customers/customers_valid.csv")
FAILING_INPUT = Path("sample_data/customers/customers_contract_failures.csv")
CONTRACT = Path("config/examples/customer_contract.yaml")
EXPECTED_ARTIFACTS = [
    "contract_validation_report.md",
    "contract_validation_results.json",
    "contract_failures.csv",
    "contract_trace.json",
    "suggested_contract_updates.yaml",
]


def test_valid_customer_example_passes_and_writes_expected_artifacts(tmp_path: Path, capsys) -> None:
    output_dir = tmp_path / "customers_valid"

    exit_code = run_cli(
        [
            "--input",
            str(VALID_INPUT),
            "--contract",
            str(CONTRACT),
            "--mode",
            "validate",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    for artifact in EXPECTED_ARTIFACTS:
        assert (output_dir / artifact).exists()

    captured = capsys.readouterr()
    assert "overall_status: Passed" in captured.out
    assert "findings_total: 0" in captured.out


def test_failing_customer_example_fails_with_default_fail_on_error(tmp_path: Path) -> None:
    output_dir = tmp_path / "customers_failures_error"

    exit_code = run_cli(
        [
            "--input",
            str(FAILING_INPUT),
            "--contract",
            str(CONTRACT),
            "--mode",
            "validate",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 1


def test_failing_customer_example_non_blocking_with_fail_on_never(tmp_path: Path) -> None:
    output_dir = tmp_path / "customers_failures_never"

    exit_code = run_cli(
        [
            "--input",
            str(FAILING_INPUT),
            "--contract",
            str(CONTRACT),
            "--mode",
            "validate",
            "--output-dir",
            str(output_dir),
            "--fail-on",
            "never",
        ]
    )

    assert exit_code == 0
    for artifact in EXPECTED_ARTIFACTS:
        assert (output_dir / artifact).exists()

    results = json.loads((output_dir / "contract_validation_results.json").read_text(encoding="utf-8"))
    assert results["summary"]["total_findings"] > 0

    report = (output_dir / "contract_validation_report.md").read_text(encoding="utf-8")
    assert "Overall status" in report
    assert "Authority boundary" in report
