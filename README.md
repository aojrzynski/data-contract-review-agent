# data-contract-review-agent
Local-first data contract review agent for validating datasets against declared expectations.

## Current development status
This repo supports deterministic:
- loading tabular datasets from CSV/XLSX/XLSM
- loading contract files from YAML/JSON
- dataset profiling / observed evidence extraction
- dataset-vs-contract validation
- finding classification
- suggested contract updates (non-mutating)
- output artifact writing

## Quick start
Install editable with dev dependencies:
`python -m pip install -e ".[dev]"`

Run tests:
`python -m pytest`

Run validate mode:
`python -m data_contract_review_agent.cli --input sample_data/customers/customers_valid.csv --contract config/examples/customer_contract.yaml --mode validate --output-dir outputs/customers_valid`

Validation artifacts are written to the selected output directory.
