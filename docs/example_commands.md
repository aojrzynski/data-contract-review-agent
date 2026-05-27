# Example validate commands

## Passing validation (quick start)
```bash
python -m data_contract_review_agent.cli \
  --input sample_data/customers/customers_valid.csv \
  --contract config/examples/customer_contract.yaml \
  --mode validate \
  --output-dir outputs/customers_valid
```

## Failing validation, non-blocking (`--fail-on never`)
```bash
python -m data_contract_review_agent.cli \
  --input sample_data/customers/customers_contract_failures.csv \
  --contract config/examples/customer_contract.yaml \
  --mode validate \
  --output-dir outputs/customers_failures \
  --fail-on never
```

## Failing validation, blocking (default `--fail-on error`)
```bash
python -m data_contract_review_agent.cli \
  --input sample_data/customers/customers_contract_failures.csv \
  --contract config/examples/customer_contract.yaml \
  --mode validate \
  --output-dir outputs/customers_failures_blocking
```

## Artifacts written to the output directory
- `contract_validation_report.md`: Human-readable markdown summary for quick review.
- `contract_validation_results.json`: Full machine-readable validation results.
- `contract_failures.csv`: Row-level failure evidence for triage.
- `contract_trace.json`: Deterministic run trace and execution metadata.
- `suggested_contract_updates.yaml`: Non-mutating contract update suggestions.
