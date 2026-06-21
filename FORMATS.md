# EAT formats

This document records the runtime file formats used by EAT.

## Rubric files

Rubrics use JSON in `.eat` files. Each rubric file contains:

- `meta`: format metadata such as version, mode and lock state.
- `rubric`: the rubric identity, language and pedagogical goal.
- `bands`: score ranges with labels, observations, flags and fixes.
- `links`: optional relations to other rubric ids.

## Index files

A runtime rubric directory can contain `index.eat`:

```json
{
  "meta": {"version": 2.0, "mode": "runtime", "locked": true},
  "index": {
    "order": ["P_Procesfase", "TD_Taakdichtheid"],
    "files": ["P_Procesfase.eat", "TD_Taakdichtheid.eat"]
  }
}
```

`index.files` controls which rubric files are loaded. `index.order` is checked for consistency and can be used by authoring tools.

## Trace files

Runtime traces are JSON Lines. Each line contains one evaluated turn with session id, turn id, decision, per-rubric scores, flags, action taken, sources and suggested fixes.
