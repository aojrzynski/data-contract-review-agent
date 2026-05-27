# data-contract-review-agent

A local-first CLI project for deterministic data contract validation and bounded review-mode orchestration.

## Why this exists

Data contracts are only useful when they can be checked consistently against real datasets. This project demonstrates a practical pattern:
- deterministic validation for pass/fail evidence,
- bounded orchestration for review readability,
- optional LLM polish that never becomes the authority layer.

## Why not just ask an LLM?

Contract conformance is a reproducibility problem, not just a summarization problem. If pass/fail outcomes are not deterministic, teams cannot rely on them for governance, CI, or audits.

## What this project demonstrates

- Deterministic dataset-vs-contract checks across schema, quality, and operational rules.
- Traceable artifacts for both humans and automation.
- Review mode that groups deterministic findings into actionable recommendations.
- Optional LLM-written `llm_summary.md` generated from bounded deterministic summary inputs.

## Why this is an agent

- `validate` mode runs a deterministic evidence pipeline.
- `review` mode coordinates findings, classifications, suggestions, and recommendations into a structured review outcome.
- The agent does **not** decide truth independently from deterministic validators.
- This is bounded orchestration, not open-ended autonomy.

## Quick start

```bash
python -m pip install -e ".[dev,llm]"
python -m pytest
```

## Example commands

```bash
python -m data_contract_review_agent.cli --input sample_data/customers/customers_valid.csv --contract config/examples/customer_contract.yaml --mode validate --output-dir outputs/customers_valid
python -m data_contract_review_agent.cli --input sample_data/customers/customers_contract_failures.csv --contract config/examples/customer_contract.yaml --mode validate --output-dir outputs/customers_failures --fail-on never
python -m data_contract_review_agent.cli --input sample_data/customers/customers_contract_failures.csv --contract config/examples/customer_contract.yaml --mode review --output-dir outputs/customers_review --fail-on never
python -m data_contract_review_agent.cli --input sample_data/customers/customers_contract_failures.csv --contract config/examples/customer_contract.yaml --mode review --output-dir outputs/customers_review_llm --fail-on never --llm-summary
```

## Output artifacts

- `contract_validation_report.md`
- `contract_validation_results.json`
- `contract_failures.csv`
- `contract_trace.json`
- `suggested_contract_updates.yaml`
- `agent_review_report.md`
- `agent_trace.json`
- `llm_summary.md` (optional, non-authoritative)

## Authority boundary

- Deterministic validation findings are authoritative.
- Review recommendations are derived from deterministic outputs.
- Suggested contract updates are review prompts, not automatic edits.
- `llm_summary.md` is optional wording polish only.
- No raw dataset rows are sent to the LLM summary input.

## Project structure

- `cli.py`
- `intake.py`
- `contract_loader.py`
- `profiling.py`
- `validators.py`
- `contract_validation.py`
- `finding_classifier.py`
- `suggested_updates.py`
- `output_writers.py`
- `reporting.py`
- `trace_writer.py`
- `review_mode.py`
- `review_reporting.py`
- `llm_summary.py`
- `llm_client.py`

## Run tests

```bash
python -m pytest
```

## Limitations and non-goals

- No automatic contract mutation.
- No row-level export to LLM prompts.
- No attempt to replace deterministic validators with model inference.
- Intentionally scoped as a practical educational v1.

## Further reading

- [Architecture](docs/architecture.md)
- [Design principles](docs/design_principles.md)
- [Artifacts](docs/artifacts.md)
- [Demo walkthrough](docs/demo_walkthrough.md)
- [Example commands](docs/example_commands.md)
- [Portfolio summary](docs/portfolio_summary.md)
- [Roadmap](docs/roadmap.md)
