"""CLI entrypoint for the Data Contract Review Agent."""

from __future__ import annotations

import argparse

from data_contract_review_agent.contract_loader import load_contract
from data_contract_review_agent.intake import load_dataset


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


def main() -> int:
    """Run the CLI."""
    parser = build_parser()
    args = parser.parse_args()

    print("Data Contract Review Agent scaffold")
    print(f"mode: {args.mode}")

    if args.input and args.contract:
        dataframe, metadata = load_dataset(args.input, sheet=args.sheet)
        contract = load_contract(args.contract)
        print(f"dataset: {metadata.file_name}")
        print(f"rows: {metadata.row_count}")
        print(f"columns: {metadata.column_count}")
        print(f"contract: {contract.contract.name}")
        print(f"contract_version: {contract.contract.version}")
    else:
        print(f"input: {args.input}")
        print(f"contract: {args.contract}")

    print(f"output_dir: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
