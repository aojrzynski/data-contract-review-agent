# Portfolio summary

## What it is

A local-first CLI data agent that reviews tabular data against data contracts using deterministic validation.

## Why it exists

Teams need repeatable contract checks, not only one-off manual review or opaque AI outputs.

## What problem it solves

It creates a practical, inspectable workflow for contract conformance checks and review-ready findings.

## How it works

It loads dataset + contract, profiles observed evidence, runs deterministic validators, classifies findings, suggests review actions, and writes traceable artifacts.

## What makes it agentic

It includes bounded review orchestration that turns deterministic findings into grouped recommendations and run traces.

## Why the deterministic-first design matters

Deterministic evidence is reproducible and auditable. Review orchestration adds usability without weakening trust.

## What I would improve next

I would add optional LLM-polished summaries, richer domain samples, and explicit contract diff/apply workflows with human approval gates.


In the included failing demo, validation reports 8 findings (5 errors, 3 warnings), including one uniqueness violation.
