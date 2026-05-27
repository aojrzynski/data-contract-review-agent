"""CLI entrypoint for the Data Contract Review Agent."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from data_contract_review_agent.contract_loader import load_contract
from data_contract_review_agent.contract_validation import validate_contract
from data_contract_review_agent.finding_classifier import ClassifiedValidationResult, classify_validation_result
from data_contract_review_agent.intake import load_dataset
from data_contract_review_agent.output_writers import write_validation_outputs
from data_contract_review_agent.profiling import build_dataset_profile
from data_contract_review_agent.suggested_updates import build_suggested_contract_updates


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="data-contract-review-agent",
        description="Validate a dataset against a declared data contract.",
    )

    parser.add_argument("--input", help="Path to the input CSV/XLSX dataset.")
    parser.add_argument("--contract", help="Path to the YAML/JSON contract file.")
    parser.add_argument("--sheet", help="Optional Excel sheet name.", default=None)
    parser.add_argument(
        "--mode",
        choices=["validate", "review"],
        default="validate",
        help="validate = deterministic validation; review = bounded agent review.",
    )
    parser.add_argument("--output-dir", default="outputs", help="Directory for output artifacts.")
    parser.add_argument(
        "--fail-on",
        choices=["error", "warning", "never"],
        default="error",
        help="Controls when the CLI should return a failing exit code.",
    )
    parser.add_argument(
        "--max-failure-examples",
        type=int,
        default=20,
        help="Maximum number of example failures to include in outputs.",
    )
    parser.add_argument(
        "--llm-summary",
        action="store_true",
        help="Write an optional non-authoritative LLM-polished summary.",
    )
    parser.add_argument("--llm-model", default=None, help="Optional LLM model name.")

    return parser


def determine_overall_status(classified_result: ClassifiedValidationResult) -> str:
    """Determine a concise overall status label from classified findings."""
    has_failed_error = any(
        item.status == "failed" and item.severity == "error" for item in classified_result.classifications
    )
    if has_failed_error:
        return "Failed"

    if classified_result.classifications:
        return "Review needed"

    return "Passed"


def _should_fail(fail_on: str, classified_result: ClassifiedValidationResult) -> bool:
    if fail_on == "never":
        return False

    if fail_on == "error":
        return any(item.status == "failed" and item.severity == "error" for item in classified_result.classifications)

    return any(
        item.status == "failed" and item.severity in {"error", "warning"}
        for item in classified_result.classifications
    )


def run_cli(argv: list[str] | None = None) -> int:
    """Run CLI with explicit argv list."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.mode == "review":
        print("review mode is not implemented yet; use --mode validate")
        return 2

    if args.llm_summary:
        print("LLM summaries are not implemented yet")
        return 2

    if not args.input:
        parser.error("--input is required when --mode validate")
    if not args.contract:
        parser.error("--contract is required when --mode validate")

    try:
        dataframe, metadata = load_dataset(args.input, sheet=args.sheet)
        contract = load_contract(args.contract)
        profile = build_dataset_profile(dataframe, metadata)
        validation_result = validate_contract(
            dataframe=dataframe,
            profile=profile,
            contract=contract,
            max_examples=args.max_failure_examples,
        )
        classified_result = classify_validation_result(validation_result)
        suggested_updates = build_suggested_contract_updates(validation_result, contract, profile)
        outputs = write_validation_outputs(
            output_dir=args.output_dir,
            validation_result=validation_result,
            classified_result=classified_result,
            suggested_updates=suggested_updates,
            profile=profile,
            contract=contract,
        )
    except (FileNotFoundError, ValueError, TypeError, OSError) as exc:
        print(f"Error: {exc}")
        return 1

    severity_counts = Counter(finding.severity for finding in validation_result.findings)
    output_dir = Path(args.output_dir)

    print("Data Contract Review Agent")
    print("mode: validate")
    print(f"dataset: {metadata.file_name}")
    print(f"rows: {metadata.row_count}")
    print(f"columns: {metadata.column_count}")
    print(f"contract: {contract.contract.name}")
    print(f"contract_version: {contract.contract.version}")
    print(f"profiled_columns: {len(profile.columns)}")
    print(f"findings_total: {len(validation_result.findings)}")
    print(
        "findings_by_severity: "
        f"error={severity_counts.get('error', 0)}, "
        f"warning={severity_counts.get('warning', 0)}, "
        f"info={severity_counts.get('info', 0)}"
    )
    print(f"overall_status: {determine_overall_status(classified_result)}")
    print(f"output_dir: {output_dir}")
    print("artifacts:")
    print(f"- report: {outputs['report']}")
    print(f"- results_json: {outputs['results_json']}")
    print(f"- failures_csv: {outputs['failures_csv']}")
    print(f"- trace_json: {outputs['trace_json']}")
    print(f"- suggested_updates_yaml: {outputs['suggested_updates_yaml']}")

    return 1 if _should_fail(args.fail_on, classified_result) else 0


def main() -> int:
    """Run the CLI."""
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())
