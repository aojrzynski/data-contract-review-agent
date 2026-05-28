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
python -m pip install -e ".[dev]"
python -m pytest
```

Optional LLM setup:

```bash
python -m pip install -e ".[dev,llm]"
```

`OPENAI_API_KEY` is only required for a real OpenAI summary call. If it is missing and you run with `--llm-summary`, the tool writes a deterministic fallback `llm_summary.md`.

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

- `src/data_contract_review_agent/cli.py` — command-line entrypoint and pipeline orchestration.
- `src/data_contract_review_agent/intake.py` — dataset loading and intake metadata.
- `src/data_contract_review_agent/contract_loader.py` — contract file loading and parsing.
- `src/data_contract_review_agent/profiling.py` — deterministic dataset profiling evidence.
- `src/data_contract_review_agent/validators.py` — deterministic evidence-producing checks.
- `src/data_contract_review_agent/contract_validation.py` — orchestration of all deterministic validators.
- `src/data_contract_review_agent/finding_classifier.py` — triage metadata classification for findings.
- `src/data_contract_review_agent/suggested_updates.py` — advisory contract update suggestions.
- `src/data_contract_review_agent/output_writers.py` — validation artifact persistence.
- `src/data_contract_review_agent/reporting.py` — markdown report rendering for validation results.
- `src/data_contract_review_agent/trace_writer.py` — deterministic validate-mode trace artifact writing.
- `src/data_contract_review_agent/review_mode.py` — bounded review-mode recommendation orchestration.
- `src/data_contract_review_agent/review_reporting.py` — review-mode markdown report rendering.
- `src/data_contract_review_agent/llm_summary.py` — bounded payload construction and optional summary generation.
- `src/data_contract_review_agent/llm_client.py` — optional OpenAI client boundary wrappers.

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
