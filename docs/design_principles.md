# Design principles

## Deterministic validation comes before AI interpretation

Contract conformance is pass/fail evidence. Deterministic checks provide reproducible outcomes teams can trust in CI, governance, and audits.

## Local-first matters

Local execution keeps the workflow practical for development, demos, and sensitive data handling. It also reduces setup complexity.

## Outputs must be traceable

Each run writes human-readable and machine-readable artifacts so findings can be inspected, shared, and re-checked.

## Suggested updates are not auto-applied

Suggested updates are advisory prompts for review discussions. Contract governance still requires explicit human decisions.

## Bounded review mode

Review mode organizes deterministic findings into grouped recommendations. It improves usability without introducing open-ended autonomous behavior.

## LLM polish boundary

The LLM layer is optional wording polish only. It receives bounded summary inputs and no raw dataset rows. Deterministic artifacts remain authoritative.

## Why no agent framework is needed for this v1

This project needs transparent orchestration, not complex autonomous planning. Focused local modules keep behavior easier to understand and maintain.
