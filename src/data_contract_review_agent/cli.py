"""CLI entrypoint for the Data Contract Review Agent."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from data_contract_review_agent.contract_loader import load_contract
from data_contract_review_agent.contract_models import DataContract, ValidationResult
from data_contract_review_agent.contract_validation import validate_contract
from data_contract_review_agent.finding_classifier import ClassifiedValidationResult, classify_validation_result
from data_contract_review_agent.intake import DatasetMetadata, load_dataset
from data_contract_review_agent.output_writers import write_validation_outputs
from data_contract_review_agent.profiling import DatasetProfile, build_dataset_profile
from data_contract_review_agent.review_mode import ReviewModeResult, review_mode_to_json_safe_dict, run_review_mode
from data_contract_review_agent.review_reporting import build_agent_review_report
from data_contract_review_agent.serialization import make_json_safe
from data_contract_review_agent.suggested_updates import SuggestedContractUpdates, build_suggested_contract_updates


@dataclass(frozen=True)
class PipelineResult:
    metadata: DatasetMetadata
    contract: DataContract
    profile: DatasetProfile
    validation_result: ValidationResult
    classified_result: ClassifiedValidationResult
    suggested_updates: SuggestedContractUpdates
    artifacts: dict[str, Path]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="data-contract-review-agent",
        description="Validate a dataset against a declared data contract.",
    )
    parser.add_argument("--input", help="Path to the input CSV/XLSX dataset.")
    parser.add_argument("--contract", help="Path to the YAML/JSON contract file.")
    parser.add_argument("--sheet", help="Optional Excel sheet name.", default=None)
    parser.add_argument("--mode", choices=["validate", "review"], default="validate")
    parser.add_argument("--output-dir", default="outputs", help="Directory for output artifacts.")
    parser.add_argument("--fail-on", choices=["error", "warning", "never"], default="error")
    parser.add_argument("--max-failure-examples", type=int, default=20)
    parser.add_argument("--llm-summary", action="store_true")
    parser.add_argument("--llm-model", default=None)
    return parser


def determine_overall_status(classified_result: ClassifiedValidationResult) -> str:
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


def run_validation_pipeline(args: argparse.Namespace) -> PipelineResult:
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
    artifacts = write_validation_outputs(
        output_dir=args.output_dir,
        validation_result=validation_result,
        classified_result=classified_result,
        suggested_updates=suggested_updates,
        profile=profile,
        contract=contract,
    )
    return PipelineResult(metadata, contract, profile, validation_result, classified_result, suggested_updates, artifacts)


def _expected_review_artifacts(output_dir: str | Path) -> dict[str, Path]:
    output_path = Path(output_dir)
    return {
        "agent_review_report": output_path / "agent_review_report.md",
        "agent_trace_json": output_path / "agent_trace.json",
    }


def _write_review_artifacts(review_result: ReviewModeResult) -> dict[str, Path]:
    report_path = Path(review_result.artifacts["agent_review_report"])
    trace_path = Path(review_result.artifacts["agent_trace_json"])
    report_path.write_text(build_agent_review_report(review_result), encoding="utf-8")
    trace_path.write_text(json.dumps(make_json_safe(review_mode_to_json_safe_dict(review_result)), indent=2, sort_keys=True), encoding="utf-8")
    return {"agent_review_report": report_path, "agent_trace_json": trace_path}


def run_cli(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.llm_summary:
        print("LLM summaries are not implemented yet")
        return 2

    if not args.input:
        parser.error(f"--input is required when --mode {args.mode}")
    if not args.contract:
        parser.error(f"--contract is required when --mode {args.mode}")

    try:
        pipeline = run_validation_pipeline(args)
    except (FileNotFoundError, ValueError, TypeError, OSError) as exc:
        print(f"Error: {exc}")
        return 1

    severity_counts = Counter(finding.severity for finding in pipeline.validation_result.findings)
    output_dir = Path(args.output_dir)

    print("Data Contract Review Agent")
    print(f"mode: {args.mode}")
    print(f"dataset: {pipeline.metadata.file_name}")
    print(f"rows: {pipeline.metadata.row_count}")
    print(f"columns: {pipeline.metadata.column_count}")
    print(f"contract: {pipeline.contract.contract.name}")
    print(f"contract_version: {pipeline.contract.contract.version}")
    print(f"profiled_columns: {len(pipeline.profile.columns)}")
    print(f"findings_total: {len(pipeline.validation_result.findings)}")
    print(
        "findings_by_severity: "
        f"error={severity_counts.get('error', 0)}, "
        f"warning={severity_counts.get('warning', 0)}, "
        f"info={severity_counts.get('info', 0)}"
    )
    print(f"overall_status: {determine_overall_status(pipeline.classified_result)}")

    artifacts = dict(pipeline.artifacts)
    if args.mode == "review":
        artifacts.update(_expected_review_artifacts(args.output_dir))
        review_result = run_review_mode(
            validation_result=pipeline.validation_result,
            classified_result=pipeline.classified_result,
            suggested_updates=pipeline.suggested_updates,
            profile=pipeline.profile,
            contract=pipeline.contract,
            validation_artifacts=artifacts,
        )
        _write_review_artifacts(review_result)
        print(f"recommendations_total: {len(review_result.recommendations)}")

    print(f"output_dir: {output_dir}")
    print("artifacts:")
    for key, value in artifacts.items():
        print(f"- {key}: {value}")

    return 1 if _should_fail(args.fail_on, pipeline.classified_result) else 0


def main() -> int:
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())
