# EAT formats in this repository

EAT_me uses JSON documents with the `.eat` extension for runtime rubrics. This differs from plain-text EAT profile formats used in some starter-kit material.

## JSON rubric `.eat` files

Runtime rubrics live in `rubrics/` and are parsed with `json.loads()` through `eatme.parser.load_eat`. Each rubric contains:

- `meta`: schema/version and locking metadata.
- `rubric`: identity, language, goal, and version metadata.
- `bands`: five score bands with observations, flags, and fixes.
- `links`: optional references to related rubric IDs.

Use these files with the validator and runtime gatekeeper.

## Plain-text EAT material

The semantic specification describes EAT as a broader educational annotation language. Plain-text examples are useful for design rationale and authoring discussions, but they are not the runtime format consumed by EAT_me.

## Practical rule

For this repository, treat `.eat` files under `rubrics/` as JSON runtime rubrics. If a future project needs both plain-text EAT profiles and JSON rubrics side by side, prefer a separate extension or an explicit `$schema` field before mixing formats.

## Legacy semantic note

The root-level `me` file is retained as a legacy semantic/design note because it contains bilingual EAT v2 rationale that predates the JSON runtime format. It is not imported by the package and is not part of runtime validation; treat it as archival documentation unless its contents are migrated into a named Markdown specification later.
