# EAT v2 — Educational Annotation Text
## Semantic Core Specification & Design Rationale
*(Nederlandstalig / English bilingual, met LaTeX-notatie)*

---

## 1 · Inleiding | Introduction

EAT (Educational Annotation Text) is een formele, semantisch gelaagde beschrijvingstaal ontworpen voor de representatie van leerprocessen, redeneringspatronen en cognitieve context. De taal is ontwikkeld om consistentie, betrouwbaarheid en uitlegbaarheid te garanderen bij mens-machine-interactie in educatieve en reflectieve domeinen.

**Core idea:**  
EAT definieert bounded reasoning spaces – semantische ruimten waarin een model vrij kan redeneren, maar binnen contextuele en didactische ankers blijft.

EAT combineert:
- de **menselijke leesbaarheid** van natuurlijke taal,
- de **deterministische betrouwbaarheid** van formele grammatica,
- en de **semantische flexibiliteit** van probabilistische redenering.

---

## 2 · Semantische Kern | Semantic Core

Een EAT-rubric bestaat uit een reeks bands (semantische intervallen) die elk een bereik van competentie, begrip of ontwikkeling representeren. Binnen elke band bevinden zich microdescriptors: observaties, flags en fixes die samen bepalen hoe betekenis wordt geïnterpreteerd.

### 2.1 Band

**Definitie | Definition**  
Een band definieert een semantisch continuüm met numerieke grenzen \([s_\min, s_\max]\). Binnen dat interval gelden de microdescriptors als contextuele regels.

```text
band 0.30–0.59:
  label: Groeiend / Emerging
  description: "Ziet eigen sterktes en zwaktes"
```

**Semantisch effect | Semantic effect**  
- Een band is geen discrete toestand maar een reasoning space.
- De interpreter leest grenzen als prior weights:
  - \(s_\min\) = meer begeleiding / scaffolding
  - \(s_\max\) = meer autonomie / agency

### 2.2 Microdescriptors

Microdescriptors zijn semantische ankers die de redenering binnen een band richting geven.

#### 2.2.1 Observaties

```text
learner_obs:
  - Reflecteert op fouten
ai_obs:
  - Matige taakvariatie
```

De elementen van *_obs* fungeren als vector-clusters in embedding-ruimte. Ze sturen aandacht: “zoek semantische nabijheid tot deze gedragingen”.

#### 2.2.2 Flag / Fix

```text
flag: "Ontwikkelingsfase / Development phase"
fix:  "Stimuleer feedbackloops / Encourage feedback loops"
```

- **Flag (if-condition)** = semantisch label van de toestand.
- **Fix (then-recommendation)** = aanbevolen interventie.

Formeel:

\[
\text{if } \mathrm{sim}(x,\,\text{flag}) > \tau 
\;\Rightarrow\;
\mathrm{recommend}(\text{fix})
\]

met \(\tau\) als fuzzy threshold (0 < τ < 1).

---

## 3 · Formele Representatie | Formal Representation

### 3.1 Band-object (JSON vorm)

```json
{
  "score_min": 0.30,
  "score_max": 0.59,
  "label": "Groeiend",
  "description": "Ziet eigen sterktes en zwaktes",
  "learner_obs": ["Reflecteert op fouten"],
  "ai_obs": ["Matige taakvariatie"],
  "flag": "Ontwikkelingsfase",
  "fix": "Stimuleer feedbackloops"
}
```

### 3.2 Interpretatiemodel | Interpretation Model

Voor een invoer \(x\):

\[
b^* = \arg\max_{b \in B} 
      \mathrm{sim}\!\left(
        \mathbf{E}(x),
        \mathbf{E}(b_{\text{learner\_obs}} \cup b_{\text{ai\_obs}})
      \right)
\]

waar \(\mathbf{E}\) de embedding-functie is.

Daarna:

\[
\text{response} = f(b^*_{\text{flag}}, b^*_{\text{fix}}, x)
\]

met \(f\) een natuurlijke-taaltransformatie (de LLM zelf).

---

## 4 · Semantische Regels | Semantic Rules

| ID | Regel / Rule | Betekenis / Meaning |
|----|--------------|--------------------|
| R1 | **Continuïteit / Continuity** | Bands vormen een gesloten interval [0, 1]; elke waarde hoort bij exact één band. |
| R2 | **Compositionaliteit / Compositionality** | Bands mogen overlappen; gedeelde descriptors krijgen gewichten. |
| R3 | **Fuzzy Causality** | Flags en fixes zijn probabilistische aanbevelingen. |
| R4 | **Non-Mutation** | Een model mag geen descriptors wijzigen binnen een locked rubric. |
| R5 | **Traceability** | Elke uitspraak wordt gelogd met de band + descriptor die hem beïnvloedde. |
| R6 | **Cycliciteit / Cyclicity** | Interpretatie herhaalt zich totdat geen contextverandering meer optreedt. |

---

## 5 · Wiskundige Formulering | Mathematical Formulation

### 5.1 Redeneerfunctie / Reasoning Function

\[
\Phi : X \times R \rightarrow Y
\]

met  
- \(X\): invoer (observaties / tekst),  
- \(R\): rubric space = \{b_i, d_i\},  
- \(Y\): uitvoer (natuurlijke-taalrespons met trace).

De kerntransformatie:

\[
\Phi(x, R) = 
f\!\left(
  x, 
  \mathrm{flag}(b^*), 
  \mathrm{fix}(b^*), 
  \omega_t
\right)
\]

waar \(\omega_t\) de fase-vector van de cyclus is.

### 5.2 Cyclische Dynamiek

De semantische toestand ontwikkelt zich over tijd \(t\):

\[
R_{t+1} = 
\mathcal{C}\big(
  R_t,\,
  \Delta_{\text{context}}
\big)
\]

\(\mathcal{C}\) = cycle operator die faseovergangen activeert wanneer  
\(|\Delta_{\text{context}}| > \epsilon\).

De cyclusvector:

\[
\Omega = \{P, TD, C, V, T, E, L\}
\]
met transitie  
\(\omega_{t+1} = \mathrm{next}(\omega_t)\) mod 7.

---
---

## 6 · Taalstructuur | Language Structure

EAT-bestanden zijn indente-gebaseerde semantische documenten. Ze combineren YAML-achtige leesbaarheid met deterministische syntaxis. Elke regel behoort tot exact één hiërarchisch niveau.

### 6.1 Globale structuur

```text
meta:
  version: 2.0
  mode: knowledge | runtime
  locked: true | false

rubric:
  rubric_id: C_CoRegulatie
  name: "Co-Regulatie"
  dimension: "Sociaal"

bands:
  - band 0.00–0.29:
      label: "Beginfase"
      learner_obs: [...]
      ai_obs: [...]
      flag: ...
      fix: ...
  - band 0.30–0.59:
      ...
links:
  - supports: TD_Taakdichtheid
  - next: V_Vaardigheidspotentieel
cycle:
  phases: ["P","TD","C","V","T","E","L"]
  loop: true
```

De canonical ordering = **meta → rubric → bands → links → cycle → EOF**.

---

## 7 · EBNF — Formele Grammatica

```ebnf
document      = meta, rubric, bands, [links], [cycle] ;
meta          = "meta:" , indent , version , mode , locked ;
version       = "version:" , number ;
mode          = "mode:" , ("knowledge" | "runtime") ;
locked        = "locked:" , ("true" | "false") ;

rubric        = "rubric:" , indent ,
                 "rubric_id:" , id ,
                 "name:" , text ,
                 "dimension:" , text ;

bands         = "bands:" , indent , { band } ;
band          = "- band" , range , ":" , indent ,
                 "label:" , text ,
                 "description:" , text ,
                 "learner_obs:" , list ,
                 "ai_obs:" , list ,
                 "flag:" , text ,
                 "fix:" , text ;

range         = number , "-" , number ;
links         = "links:" , indent , { link } ;
link          = "-" , relation , ":" , id ;
relation      = "supports" | "next" | "reinforces" | "depends_on" ;

cycle         = "cycle:" , indent ,
                 "phases:" , list ,
                 "loop:" , boolean ;

number        = digit , { digit | "." } ;
boolean       = "true" | "false" ;
id            = letter , { letter | "_" | "-" } ;
text          = quoted_string | unquoted_text ;
list          = "[" , [ text , { "," , text } ] , "]" ;
indent        = newline , spaces(2..n) ;
```

---

## 8 · Canonical Schema | JSON Schema Overview

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "EAT v2 Rubric",
  "type": "object",
  "required": ["meta", "rubric", "bands"],
  "properties": {
    "meta": {
      "type": "object",
      "properties": {
        "version": {"type": "number"},
        "mode": {"enum": ["knowledge", "runtime"]},
        "locked": {"type": "boolean"}
      }
    },
    "rubric": {
      "type": "object",
      "properties": {
        "rubric_id": {"type": "string"},
        "name": {"type": "string"},
        "dimension": {"type": "string"}
      }
    },
    "bands": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "score_min": {"type": "number"},
          "score_max": {"type": "number"},
          "label": {"type": "string"},
          "description": {"type": "string"},
          "learner_obs": {"type": "array", "items": {"type": "string"}},
          "ai_obs": {"type": "array", "items": {"type": "string"}},
          "flag": {"type": "string"},
          "fix": {"type": "string"}
        },
        "required": ["score_min", "score_max", "label"]
      }
    }
  }
}
```

**Validatieregels**
1. 0 ≤ score_min < score_max ≤ 1  
2. Bands mogen niet overlappen tenzij `compositional:true` is gespecificeerd.  
3. Als `locked:true`, dan zijn mutaties via runtime verboden.

---

## 9 · Runtime-Logica | Interpreter Behaviour

De interpreter implementeert de reasoning-flow Φ:

```python
def eat_reason(input_text, rubric):
    v = embed(input_text)
    band = best_match(v, rubric.bands)
    prompt = f"Context: {band.label}\nFlag: {band.flag}\nFix: {band.fix}"
    result = llm(prompt + "\nUser: " + input_text)
    log_trace(band, result)
    if context_shift(result):
        advance_cycle()
    return result
```

### 9.1 Locked-mechanisme

- Wanneer `locked:true`, zijn velden in `rubric` en `bands` read-only.
- Alleen `meta`-velden en `runtime`-outputs mogen veranderen.
- Parser-bevestiging: wijziging → foutmelding `E_LOCKED_MODIFICATION`.

---

## 10 · Cyclische Implementatie

De cyclus Ω = {P, TD, C, V, T, E, L} wordt als ringbuffer geïmplementeerd.

Voor elke iteratie t:

\[
\omega_{t+1} = 
\begin{cases}
\mathrm{next}(\omega_t) & 
\text{als } |\Delta_{\text{context}}| > \epsilon\\[4pt]
\omega_t & 
\text{anders}
\end{cases}
\]

Wanneer `loop:true`, dan next(L) = P. Bij `loop:false`, eindigt de interpretatie na L.

---

## 11 · Pedagogische en Epistemische Context

EAT is niet enkel een datataal; het is een semantische ethiek. Ze is ontworpen voor contexten waarin betekenisvorming, leren en reflectie samenvallen met machine-redenering.

EAT erkent drie lagen van betekenisvorming:

| Laag | Omschrijving | Functie |
|------|---------------|---------|
| Cognitief | Wat wordt waargenomen | learner_obs, ai_obs |
| Didactisch | Hoe betekenis verandert | bands, flags, fixes |
| Epistemisch | Waarom betekenis relevant is | rubric, links, cycle |

---

## 12 · Ontwerpfilosofie

EAT is ontworpen om semantische consistentie af te dwingen zonder de creatieve autonomie van taal te verliezen.

\[
\text{Reliability} = 
\frac{\text{Coherence} + \text{Traceability}}{2}
\]

Een betrouwbaar systeem is niet foutloos, maar voorspelbaar in zijn semantische structuur.

Het locked-mechanisme weerspiegelt pedagogische integriteit: een rubric mag niet door het systeem zelf worden aangepast.

---

## 13 · Appendix

### 13.1 Voorbeeldrubric

```text
meta:
  version: 2.0
  mode: knowledge
  locked: true

rubric:
  rubric_id: V_Vaardigheidspotentieel
  name: "Vaardigheidspotentieel / Skill Potential"
  dimension: "Cognitief"

bands:
  - band 0.00–0.29:
      label: "Initiatiefase / Initiation"
      description: "Beperkte zelfinschatting"
      learner_obs: ["Zoekt externe sturing", "Weinig zelfreflectie"]
      ai_obs: ["Onvolledige feedback", "Vermijdt meta-taal"]
      flag: "Laag autonomie-niveau"
      fix: "Introduceer begeleid zelfonderzoek"
  - band 0.30–0.59:
      label: "Groeiend / Developing"
      description: "Begint patronen te herkennen"
      learner_obs: ["Reflecteert op fouten", "Verbindt eigen ervaringen"]
      ai_obs: ["Consistente taakvariatie"]
      flag: "Ontwikkelingsfase"
      fix: "Stimuleer feedbackloops"
  - band 0.60–1.00:
      label: "Gevestigd / Established"
      description: "Toont zelfsturing en transfer"
      learner_obs: ["Integreert reflectie spontaan"]
      ai_obs: ["Gebruikt metataal adequaat"]
      flag: "Zelfregulerend"
      fix: "Versterk autonomie"

cycle:
  phases: ["P","TD","C","V","T","E","L"]
  loop: true
```

### 13.2 LLM-Tracevoorbeeld

Input (studenttekst):
> "Ik heb moeite met samenwerken omdat ik graag alles zelf doe, maar ik begin te begrijpen dat feedback helpt."

Interpreter reasoning (vereenvoudigd):

\[
b^* = \arg\max_b \mathrm{sim}(\mathbf{E}(x), b_{\text{learner\_obs}}) = 0.3–0.59
\]

Prompt Constructie:
```
Context: Groeiend
Flag: Ontwikkelingsfase
Fix: Stimuleer feedbackloops
```

LLM Output:
> "Je ontwikkelt een goed inzicht in hoe samenwerking bijdraagt aan groei. Probeer de feedback van anderen bewust toe te passen in je volgende project."

Trace Log:
```
band_used: 0.3–0.59
flag_triggered: Ontwikkelingsfase
fix_applied: Stimuleer feedbackloops
cycle_phase: V (Vaardigheidspotentieel)
```

Volgende iteratie:
|Δ_context| = 0.12 > ε ⇒ ω_{t+1} = T

---

## 14 · Slot

EAT v2 definieert niet enkel een taal maar een semantisch mechanisme dat menselijke leerlogica structureert op een manier die voor machines begrijpelijk én controleerbaar blijft.

> "EAT leert niet over kennis — het leert over leren."

---
