# Rubric authoring guide

This guide describes how to write JSON-based EAT_me runtime rubrics.

## Required shape

A rubric file should contain `meta`, `rubric`, `bands`, and `links` fields. Runtime files are JSON even though the extension is `.eat`.

## Rubric metadata

Use stable `rubric_id` values such as `E_EpistemischeBetrouwbaarheid`. Set `language` to the language used by the observations and expected answer cues, for example `nl` or `en`.

## Bands

Each rubric should define five ordered bands covering the full score range from `0.0` to `1.0`. For every band, provide:

- `score_min` and `score_max`.
- `label` and `description`.
- non-empty `learner_obs`.
- non-empty `ai_obs`.
- a non-empty `flag`.
- a non-empty `fix`.

## Observations

Write `learner_obs` for learner behavior or state, and `ai_obs` for answer behavior that the evaluator should recognize. Prefer concrete, observable language over abstract ideals.

## Flags and fixes

Flags should name the problem or state. Fixes should be actionable rewrite or teaching guidance. The runtime uses fixes when constructing rewrite instructions.

## Links

The `links` object may reference related `rubric_id` values. Directory validation checks that referenced IDs exist in the same rubric set.

## Validate locally

Run:

```bash
python -m eatme validate rubrics
```

Fix every reported issue before using a rubric at runtime.
