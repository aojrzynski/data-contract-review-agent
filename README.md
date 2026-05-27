# data-contract-review-agent

A local-first CLI agent for reviewing tabular datasets against data contracts. It uses deterministic checks for pass/fail evidence, then adds bounded review-mode orchestration for human-readable recommendations.

## Why this exists

Data contracts are useful only when teams can check them consistently against real datasets.

Many AI agent demos overuse LLMs for work that should stay deterministic. This project demonstrates a safer pattern: deterministic validation is the source of truth, while interpretation/orchestration stays around that evidence.

Optional LLM-polished summaries are supported as a wording layer, never an authority layer.

## What it does

- Loads CSV/XLSX/XLSM data.
- Loads YAML/YML/JSON contracts.
- Profiles observed dataset evidence.
- Validates dataset evidence against a contract.
- Classifies findings for triage.
- Suggests possible contract review actions.
- Writes markdown/JSON/CSV/YAML traceable artifacts.
- Supports both `validate` mode and deterministic `review` mode.

## Quick start

Install editable with dev dependencies:

```bash
python -m pip install -e ".[dev,llm]"
```

Run tests:

```bash
python -m pytest
```

Passing validate command:

```bash
python -m data_contract_review_agent.cli --input sample_data/customers/customers_valid.csv --contract config/examples/customer_contract.yaml --mode validate --output-dir outputs/customers_valid
```

Failing validate command:

```bash
python -m data_contract_review_agent.cli --input sample_data/customers/customers_contract_failures.csv --contract config/examples/customer_contract.yaml --mode validate --output-dir outputs/customers_failures --fail-on never
```

Review mode command:

```bash
python -m data_contract_review_agent.cli --input sample_data/customers/customers_contract_failures.csv --contract config/examples/customer_contract.yaml --mode review --output-dir outputs/customers_review --fail-on never
```

## Output artifacts

- `contract_validation_report.md`: Human-readable validation summary for quick review.
- `contract_validation_results.json`: Full machine-readable validation payload.
- `contract_failures.csv`: Finding-level (not row-level) failure table for triage.
- `contract_trace.json`: Deterministic execution trace for validate-mode runs.
- `suggested_contract_updates.yaml`: Non-mutating contract change suggestions requiring review.
- `agent_review_report.md`: Human-readable grouped review recommendations.
- `agent_trace.json`: Deterministic review-mode trace showing bounded orchestration.

## Design principles

- Deterministic checks are authoritative.
- Review mode is orchestration only.
- Suggested contract updates are not applied automatically.
- LLM summary is optional (`--llm-summary`) and non-authoritative.
- Local-first and easy to run.

## Project status

This is a portfolio/demo project (Agent 4 in a staged suite) built to be practical, readable, and extensible rather than a toy. It is production-minded in structure, while still intentionally scoped as a v1.

## More docs

- [Architecture](docs/architecture.md)
- [Artifacts](docs/artifacts.md)
- [Demo walkthrough](docs/demo_walkthrough.md)
- [Design principles](docs/design_principles.md)
- [Roadmap](docs/roadmap.md)
- [Portfolio summary](docs/portfolio_summary.md)
- [Example commands](docs/example_commands.md)


Optional LLM summary command:

```bash
python -m data_contract_review_agent.cli --input sample_data/customers/customers_contract_failures.csv --contract config/examples/customer_contract.yaml --mode review --output-dir outputs/customers_review_llm --fail-on never --llm-summary
```

Without `OPENAI_API_KEY`, the CLI writes a deterministic fallback `llm_summary.md` and continues normally.
