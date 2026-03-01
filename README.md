# EAT Rubrics / EAT_me

## Format

- **EAT_me v2-rubrics zijn JSON-documenten met `.eat` extensie.**
- **Geen PyYAML dependency nodig.**

## Waarom JSON (niet YAML)

- Gebruikt standaard Python JSON-parsing, dus geen externe parser dependency in runtime-paden.
- Vermijdt ambigu YAML typing/coercion gedrag in validatie-kritieke stappen.
- Verhoogt reproduceerbaarheid voor migratie, validatie en runtime bundle-builds.

EAT bestaat hier uit twee complementaire profielen:

- **EAT (prompt-profiel):** richt zich op hoe een edu-chatbot inhoud en begeleiding formuleert.
- **EAT_me (rubric-profiel):** werkt als **Runtime Rubric Gatekeeper** die meeleest, beoordeelt en per mode kan ingrijpen.

## Runtime Gatekeeper modes

- `OBSERVE`: runtime beslist en handelt altijd `PASS`, maar logt `would_have_decided` als enforcement-prognose (`PASS`/`REWRITE`/`BLOCK`) + suggesties voor tuning.
- `NUDGE`: beperkte suggesties (1-2 micro-fixes).
- `CORRECT`: rewrite afdwingen bij fail (max `max_rewrite_iterations`), optioneel via rewrite hook.
- `GATEKEEP`: bij kritieke fail altijd blokkeren; met veilige rewrite-guidance in instructies.

Standaard kritieke rubrics:
- `E_EpistemischeBetrouwbaarheid`
- `B_BiasCorrectieFairness`
- `T_TechnologischeIntegratieVisibility`

## Rubric loading met `index.eat`

Als `rubric_dir/index.eat` aanwezig is:

- `index.files` bepaalt **exact** welke rubrics geladen worden.
- De volgorde in `index.files` wordt exact gerespecteerd (load order).
- Als `index.order` ook aanwezig is en niet dezelfde set rubrics benoemt als `index.files`, dan wordt dat als warning gemarkeerd; loading blijft `index.files`-gedreven.
- Overige `*.eat` bestanden in dezelfde map worden genegeerd.
- Verwijst `index.files` naar een ontbrekend bestand, dan faalt initialisatie met een duidelijke foutmelding.

Zonder `index.eat` valt runtime terug op glob-loading van alle `*.eat` (behalve `index.eat`).

## Rewrite hook (optioneel)

Je kunt een generieke rewrite callback meegeven in `EATRuntimeGatekeeper(...)` of per call in `evaluate_turn(..., rewrite_func=...)`.

Signature:

```python
rewrite_func(candidate_reply: str, rewrite_instructions: list[str], context: dict) -> str
```

`context` bevat:

- `transcript_window`
- `sources`
- `tool_usage`
- `mode`

Voorbeeld:

```python
from engine import EATRuntimeGatekeeper
from eatme.models import GatekeeperConfig, Mode


def my_rewriter(candidate_reply, rewrite_instructions, context):
    return "Ik kan dit niet hard claimen zonder bron. Wil je dat ik je met stappen help zoeken?"


gate = EATRuntimeGatekeeper(
    rubric_dir="rubrics",
    config=GatekeeperConfig(mode=Mode.CORRECT, max_rewrite_iterations=2),
    rewrite_func=my_rewriter,
)
```

## Tracing velden

Trace-entries bevatten o.a.:

- `decision`, `action_taken`, `rewrite_iterations`
- `would_have_decided` (indien mode `OBSERVE`)
- `rewrite_required` (indien rewrite nodig is maar geen hook beschikbaar)
- `final_reply` (indien rewrite-loop heeft plaatsgevonden)
- `rubrics[].evidence_snippets` (afgekapt op max 120 chars)

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

- Als je oude `yaml` errors ziet: update naar latest; YAML wordt niet meer gebruikt.

## Voorbeeld gatekeeper-run

```python
from engine import EATRuntimeGatekeeper
from eatme.models import GatekeeperConfig, Mode


gate = EATRuntimeGatekeeper(rubric_dir=".", config=GatekeeperConfig(mode=Mode.GATEKEEP))
report = gate.evaluate_turn(
    session_id="demo",
    turn_id="1",
    transcript_window=[{"role": "user", "text": "Leg mitose uit"}],
    candidate_reply="Volgens bron: ...",
    sources=[],
)
print(report)
```
