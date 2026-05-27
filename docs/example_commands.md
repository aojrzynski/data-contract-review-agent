# Example commands

## Validate mode: passing input

```bash
python -m data_contract_review_agent.cli \
  --input sample_data/customers/customers_valid.csv \
  --contract config/examples/customer_contract.yaml \
  --mode validate \
  --output-dir outputs/customers_valid
```

## Validate mode: failing input (non-blocking)

```bash
python -m data_contract_review_agent.cli \
  --input sample_data/customers/customers_contract_failures.csv \
  --contract config/examples/customer_contract.yaml \
  --mode validate \
  --output-dir outputs/customers_failures \
  --fail-on never
```

## Validate mode: failing input (blocking default)

```bash
python -m data_contract_review_agent.cli \
  --input sample_data/customers/customers_contract_failures.csv \
  --contract config/examples/customer_contract.yaml \
  --mode validate \
  --output-dir outputs/customers_failures_blocking
```

## Review mode: deterministic orchestration

```bash
python -m data_contract_review_agent.cli \
  --input sample_data/customers/customers_contract_failures.csv \
  --contract config/examples/customer_contract.yaml \
  --mode review \
  --output-dir outputs/customers_review \
  --fail-on never
```

## Artifacts written in output directories

- `contract_validation_report.md`: Human-readable validation summary.
- `contract_validation_results.json`: Machine-readable validation output.
- `contract_failures.csv`: Finding-level failures table (not row-level data export).
- `contract_trace.json`: Deterministic validate-mode run trace.
- `suggested_contract_updates.yaml`: Non-mutating suggestions requiring human review.
- `agent_review_report.md`: Human-readable deterministic review report.
- `agent_trace.json`: Deterministic review trace, including authority-boundary evidence.
