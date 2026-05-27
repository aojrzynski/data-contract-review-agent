# Architecture

This project is a deterministic pipeline for evaluating a tabular dataset against a declared data contract.

## Pipeline overview

1. **Dataset intake**
   - Load CSV/XLSX/XLSM input into a normalized internal form.
2. **Contract loading**
   - Load YAML/YML/JSON contract into typed contract models.
3. **Dataset profiling**
   - Compute deterministic observed evidence (schema, nulls, ranges, categories, etc.).
4. **Deterministic validation**
   - Compare observed evidence against contract rules and produce pass/fail findings.
5. **Finding classification**
   - Label findings so triage is faster and output is consistent.
6. **Suggested contract updates**
   - Generate review suggestions when observed evidence indicates potential contract drift.
7. **Output writing**
   - Write markdown/JSON/CSV/YAML artifacts for people and automation.
8. **Review mode orchestration**
   - Group and explain deterministic findings into a concise review report.

## Simple flow diagram

```text
Dataset + Contract
  -> Intake + Contract Loader
  -> Dataset Profile
  -> Deterministic Validators
  -> Findings + Classifications + Suggestions
  -> Artifacts + Review Mode
```

## Authority boundary

- Validators produce the authoritative pass/fail evidence.
- Review mode explains and groups findings; it does not override validators.
- Suggested updates are prompts for human review, not automatic mutations.
- LLMs are not used in the current version.
