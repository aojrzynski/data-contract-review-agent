# Artifacts

This project writes traceable artifacts so both humans and automation can inspect results.

## `contract_validation_report.md`
- **What it is:** Human-readable markdown summary of validation results.
- **Who it is for:** Data producers/consumers, reviewers, and demo audiences.
- **When to use it:** First-pass review of contract conformance.

## `contract_validation_results.json`
- **What it is:** Full machine-readable validation payload.
- **Who it is for:** Scripts, CI tooling, and downstream automation.
- **When to use it:** Programmatic checks and integrations.

## `contract_failures.csv`
- **What it is:** Tabular findings output for failed checks.
- **Who it is for:** Analysts and reviewers doing issue triage.
- **When to use it:** Sorting/filtering findings; this file is **finding-level, not row-level**.

## `contract_trace.json`
- **What it is:** Deterministic execution trace for validate-mode flow.
- **Who it is for:** Auditors, maintainers, and debugging workflows.
- **When to use it:** Verifying execution path and validating reproducibility.

## `suggested_contract_updates.yaml`
- **What it is:** Candidate contract changes inferred from deterministic evidence.
- **Who it is for:** Contract owners and data governance reviewers.
- **When to use it:** Review discussions about contract evolution. This file is non-mutating and requires explicit human review.

## `agent_review_report.md`
- **What it is:** Human-readable report from deterministic review-mode orchestration.
- **Who it is for:** Stakeholders who want grouped recommendations and plain-English context.
- **When to use it:** Decision meetings and portfolio demos.

## `agent_trace.json`
- **What it is:** Structured trace of review-mode orchestration steps.
- **Who it is for:** Auditors, reviewers, and maintainers.
- **When to use it:** Demonstrating that review mode is bounded and deterministic; this trace proves no LLM was used.

## `llm_summary.md`
- **What it is:** Optional markdown wording polish generated from deterministic summary inputs.
- **Who it is for:** Stakeholders who want a concise narrative overview.
- **When to use it:** As a readability aid only; deterministic artifacts remain the source of truth. If OpenAI or `OPENAI_API_KEY` is unavailable, a deterministic fallback summary is written instead.
