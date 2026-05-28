# Architecture

## Overview

This project is a deterministic data contract validation pipeline with bounded review orchestration layered on top.

## Layer responsibilities

1. **Intake + contract loading**: Load local dataset files and local contract definitions.
2. **Profiling**: Compute deterministic observed evidence from the dataset.
3. **Validation**: Run deterministic validators to produce findings.
4. **Classification + suggestions**: Add triage metadata and advisory contract-review prompts.
5. **Artifact writing**: Persist traceable markdown/JSON/CSV/YAML outputs.
6. **Review mode**: Group deterministic findings into concise recommendations and step traces.
7. **Optional LLM summary**: Generate `llm_summary.md` from bounded deterministic summary payloads.

## Runtime flow: `validate` mode

1. Load dataset.
2. Load contract.
3. Build dataset profile.
4. Run validators.
5. Classify findings.
6. Build suggested updates.
7. Write deterministic artifacts.
8. Compute exit code from `--fail-on` policy.

## Runtime flow: `review` mode

`review` mode includes the full `validate` flow, then:
1. Build grouped deterministic recommendations.
2. Build review step trace.
3. Write `agent_review_report.md` and `agent_trace.json`.

## Optional LLM summary flow

When `--llm-summary` is enabled:
1. Build a compact deterministic payload (counts, recommendations, suggestion metadata).
2. Attempt OpenAI summary generation.
3. If OpenAI is unavailable, write a deterministic fallback markdown summary.

The LLM flow only writes `llm_summary.md` and does not alter deterministic outputs.

## Authority boundary

- Validators create authoritative findings.
- LLMs are optional and non-authoritative.
- LLMs do **not** create validation findings.
- LLMs do **not** alter recommendations, traces, suggested updates, or exit codes.

## Why no heavyweight agent framework

The orchestration is bounded and deterministic, so plain Python modules are enough for this v1. This keeps behavior inspectable, dependency-light, and easy to run locally.
