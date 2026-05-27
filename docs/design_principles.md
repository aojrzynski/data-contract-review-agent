# Design principles

## Deterministic validation comes before AI interpretation

Contract conformance is a pass/fail question that should be reproducible. Deterministic validators provide the trust anchor.

## Local-first matters

Local execution keeps data handling simple, fast to iterate, and easier to reason about during development and demos.

## Outputs must be traceable

Each run writes artifacts for both people and automation so evidence can be inspected, shared, and re-checked.

## Suggested updates are not auto-applied

Contract changes affect governance and downstream systems. Suggestions are prompts only and require explicit human approval.

## Bounded review mode

Review mode is intentionally constrained: it organizes and explains deterministic findings, but does not invent or replace validation evidence.

## Where LLM support could fit later

An optional LLM layer can improve narrative clarity (for example, polished summaries), as long as deterministic outputs remain authoritative and unchanged.
