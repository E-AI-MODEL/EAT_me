# EAT_me architecture

EAT_me is a runtime gatekeeper for educational AI responses. It evaluates a candidate answer against pedagogical rubrics, decides whether to pass, nudge, rewrite, or block, and writes trace data for later analysis.

## Runtime flow

1. `EATRuntimeGatekeeper` loads JSON `.eat` rubrics from a directory or `index.eat`.
2. `EATValidator` checks rubric structure and content before use.
3. `GatekeeperOrchestrator` extracts features from the transcript, candidate reply, and sources.
4. Each rubric receives a score and selected band.
5. The configured mode maps failures to `PASS`, `NUDGE`, `REWRITE`, or `BLOCK`.
6. `TraceLogger` appends a JSONL trace entry.
7. Optional rewrite hooks can repair an answer and trigger re-evaluation.

## Core modules

- `eatme.parser`: JSON loading and dumping for runtime `.eat` files.
- `eatme.validator`: schema/content validation and cross-rubric link checks.
- `eatme.evaluator`: feature extraction, heuristic scoring, optional LLM judge, mode decisions.
- `eatme.engine`: high-level runtime API and rewrite loop.
- `eatme.cycle`: pedagogical cycle phase definitions and focus-rubric helpers.
- `eatme.tracing`: per-turn logging and session/global aggregation.
- `eatme.metrics`: aggregate metrics from trace logs.

## Modes

- `OBSERVE`: always returns `PASS`, while recording what would have happened.
- `NUDGE`: surfaces guidance without blocking the answer.
- `CORRECT`: requests or performs a rewrite when rubrics fail.
- `GATEKEEP`: blocks critical failures and rewrites non-critical failures.

## Pedagogical cycle

The optional cycle follows `P → TD → C → V → T → E → L`. When enabled, the active phase and its neighbors receive a configurable focus weight during scoring. The engine advances the active phase after successful `PASS` or `NUDGE` turns.

## RAG integration

A RAG system should pass the generated answer as `candidate_reply` and retrieval results as `sources`. EAT_me uses source presence and explicit source claims to detect misleading or ungrounded answers before the final response is shown to the learner.
