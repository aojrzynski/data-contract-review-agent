# data-contract-review-agent
Local-first data contract review agent for validating datasets against declared expectations.

## Current development status
This early scaffold currently supports:
- loading tabular datasets from CSV/XLSX/XLSM
- loading contract files from YAML/JSON
- validating contract structure with clear fail-fast errors
- deterministic dataset profiling / observed evidence extraction

Deterministic dataset-vs-contract validation checks are now implemented.

## Testing
Tests run locally with:
`python -m pytest`

Pull requests are checked with GitHub Actions.
