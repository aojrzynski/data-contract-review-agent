# Demo walkthrough

This walkthrough is copy/paste-friendly and shows the deterministic validate and review flows.

## 1) Install

```bash
python -m pip install -e ".[dev]"
```

## 2) Run tests

```bash
python -m pytest
```

## 3) Run passing validation

```bash
python -m data_contract_review_agent.cli --input sample_data/customers/customers_valid.csv --contract config/examples/customer_contract.yaml --mode validate --output-dir outputs/customers_valid
```

## 4) Inspect expected terminal output (conceptually)

You should see a successful validate run with no failing findings and output artifacts written to `outputs/customers_valid`.

## 5) Run failing validation with `--fail-on never`

```bash
python -m data_contract_review_agent.cli --input sample_data/customers/customers_contract_failures.csv --contract config/examples/customer_contract.yaml --mode validate --output-dir outputs/customers_failures --fail-on never
```

## 6) Open the markdown report

```bash
cat outputs/customers_failures/contract_validation_report.md
```

## 7) Open the CSV findings table

```bash
cat outputs/customers_failures/contract_failures.csv
```

## 8) Run review mode

```bash
python -m data_contract_review_agent.cli --input sample_data/customers/customers_contract_failures.csv --contract config/examples/customer_contract.yaml --mode review --output-dir outputs/customers_review --fail-on never
```

## 9) Open `agent_review_report.md`

```bash
cat outputs/customers_review/agent_review_report.md
```

## 10) What this demonstrates

- Deterministic contract validation is the authority layer.
- Failing evidence is exported in traceable artifacts.
- Review mode adds bounded orchestration and readable grouping, without using any LLM.
