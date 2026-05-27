from __future__ import annotations

from pathlib import Path

import pytest

from data_contract_review_agent.cli import build_parser, run_cli


def _write_csv(path: Path, rows: list[str]) -> None:
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _write_contract(path: Path, *, nullable_email: bool = True, id_unique: bool = True) -> None:
    path.write_text(
        "\n".join(
            [
                "contract:",
                "  name: customer_master_contract",
                "  version: 1.0.0",
                "columns:",
                "  customer_id:",
                "    type: integer",
                "    required: true",
                f"    unique: {'true' if id_unique else 'false'}",
                "    nullable: false",
                "  email:",
                "    type: string",
                "    required: true",
                f"    nullable: {'true' if nullable_email else 'false'}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_cli_defaults_to_validate_mode() -> None:
    parser = build_parser()

    args = parser.parse_args([])

    assert args.mode == "validate"
    assert args.output_dir == "outputs"
    assert args.fail_on == "error"
    assert args.max_failure_examples == 20
    assert args.llm_summary is False


def test_cli_accepts_review_mode() -> None:
    parser = build_parser()

    args = parser.parse_args(["--mode", "review"])

    assert args.mode == "review"


def test_validate_mode_writes_artifacts_and_returns_zero_for_clean_data(tmp_path: Path, capsys) -> None:
    csv_path = tmp_path / "customers_valid.csv"
    contract_path = tmp_path / "contract.yaml"
    output_dir = tmp_path / "outputs"

    _write_csv(csv_path, ["customer_id,email", "1,a@example.com", "2,b@example.com"])
    _write_contract(contract_path)

    code = run_cli(
        [
            "--mode",
            "validate",
            "--input",
            str(csv_path),
            "--contract",
            str(contract_path),
            "--output-dir",
            str(output_dir),
            "--fail-on",
            "error",
        ]
    )

    assert code == 0
    assert (output_dir / "contract_validation_report.md").exists()
    assert (output_dir / "contract_validation_results.json").exists()
    assert (output_dir / "contract_failures.csv").exists()
    assert (output_dir / "contract_trace.json").exists()
    assert (output_dir / "suggested_contract_updates.yaml").exists()

    captured = capsys.readouterr()
    assert "mode: validate" in captured.out
    assert "dataset: customers_valid.csv" in captured.out
    assert "contract: customer_master_contract" in captured.out
    assert "findings_total: 0" in captured.out
    assert "overall_status: Passed" in captured.out
    assert "- report:" in captured.out


def test_validate_mode_returns_one_for_error_findings_on_fail_on_error(tmp_path: Path) -> None:
    csv_path = tmp_path / "customers_error.csv"
    contract_path = tmp_path / "contract.yaml"

    _write_csv(csv_path, ["customer_id,email", "1,a@example.com", "1,b@example.com"])
    _write_contract(contract_path, id_unique=True)

    code = run_cli(["--input", str(csv_path), "--contract", str(contract_path), "--fail-on", "error"])

    assert code == 1


def test_validate_mode_returns_one_for_warning_findings_on_fail_on_warning(tmp_path: Path) -> None:
    csv_path = tmp_path / "customers_warning.csv"
    contract_path = tmp_path / "contract.yaml"

    _write_csv(csv_path, ["customer_id,email", "1,a@example.com", "2,"])
    _write_contract(contract_path, nullable_email=False)

    code = run_cli(["--input", str(csv_path), "--contract", str(contract_path), "--fail-on", "warning"])

    assert code == 1


def test_validate_mode_returns_zero_on_fail_on_never_even_with_findings(tmp_path: Path) -> None:
    csv_path = tmp_path / "customers_error.csv"
    contract_path = tmp_path / "contract.yaml"

    _write_csv(csv_path, ["customer_id,email", "1,a@example.com", "1,b@example.com"])
    _write_contract(contract_path, id_unique=True)

    code = run_cli(["--input", str(csv_path), "--contract", str(contract_path), "--fail-on", "never"])

    assert code == 0


def test_validate_mode_requires_input_and_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "contract.yaml"
    _write_contract(contract_path)

    with pytest.raises(SystemExit) as missing_input:
        run_cli(["--contract", str(contract_path)])
    with pytest.raises(SystemExit) as missing_contract:
        run_cli(["--input", str(tmp_path / "data.csv")])

    assert missing_input.value.code == 2
    assert missing_contract.value.code == 2


def test_validate_mode_llm_summary_writes_artifact_with_fallback(tmp_path: Path, capsys, monkeypatch) -> None:
    csv_path = tmp_path / "customers_valid.csv"
    contract_path = tmp_path / "contract.yaml"

    _write_csv(csv_path, ["customer_id,email", "1,a@example.com"])
    _write_contract(contract_path)

    # Ensure fallback path is deterministic and does not depend on local env credentials.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    code = run_cli(["--input", str(csv_path), "--contract", str(contract_path), "--llm-summary"])

    assert code == 0
    out = capsys.readouterr().out
    assert "llm_summary:" in out
    assert "llm_used: false" in out
