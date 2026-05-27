from data_contract_review_agent.cli import build_parser


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
