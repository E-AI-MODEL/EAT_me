# EAT Rubrics / EAT_me

## Format

- **EAT_me v2 rubrics are JSON documents stored with a `.eat` extension.**
- **No PyYAML dependency required.**

## Why JSON (not YAML)

- Uses Python standard library JSON parsing, so no external parser dependency is required.
- Avoids ambiguous YAML typing/coercion behavior in validation-critical runtime paths.
- Improves reproducibility for migration, validation, and runtime bundle builds.

EAT bestaat hier uit twee complementaire profielen:

- **EAT (prompt-profiel):** richt zich op hoe een edu-chatbot inhoud en begeleiding formuleert.
- **EAT_me (rubric-profiel):** werkt als **Rubric Gatekeeper** die meeleest, beoordeelt, en per mode kan ingrijpen.

## Runtime Gatekeeper modes

- `OBSERVE`: alleen rapporteren + tracen (geen directe ingreep).
- `NUDGE`: beperkte suggesties (1-2 micro-fixes).
- `CORRECT`: rewrite afdwingen bij fail (max 2 iteraties).
- `GATEKEEP`: blokkeren of veilige rewrite bij kritieke rubric-fails.

Standaard kritieke rubrics:
- `E_EpistemischeBetrouwbaarheid`
- `B_BiasCorrectieFairness`
- `T_TechnologischeIntegratieVisibility`

## CLI

Valideer één rubric of map:

```bash
python -m eatme validate .
```

Migreer legacy rubrics naar canonical v2 JSON-schema (`.eat` = JSON):

```bash
python -m eatme migrate .
```

Bereken trace-metrics:

```bash
python -m eatme metrics trace/eat_trace.jsonl
```

## Build runtime bundle

Run:

```bash
python scripts/build_runtime_bundle.py
```

Output:

- `dist/EAT_v2_runtime_ready_FULL.zip`

## Runtime bundle

- Canonical rubrics (source of truth): `rubrics/*.eat`
- Runtime index: `rubrics/index.eat`
- Generated runtime zip: `dist/EAT_v2_runtime_ready_FULL.zip`

## Troubleshooting

- If you see old `yaml` errors, update to latest; YAML is no longer used.

## Voorbeeld gatekeeper-run

```python
from engine import EATRuntimeGatekeeper
from eatme.models import GatekeeperConfig, Mode

gate = EATRuntimeGatekeeper(rubric_dir=".", config=GatekeeperConfig(mode=Mode.GATEKEEP))
report = gate.evaluate_turn(
    session_id="demo",
    turn_id="1",
    transcript_window=[{"role":"user", "text":"Leg mitose uit"}],
    candidate_reply="Volgens bron: ...",
    sources=[]
)
print(report)
```
