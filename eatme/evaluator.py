from __future__ import annotations

from dataclasses import asdict
import re
from typing import Any, Callable, Dict, List, Optional

from .models import Decision, EvaluationReport, GatekeeperConfig, Mode, RubricAssessment

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
YEAR_NUM_RE = re.compile(r"\b(\d{4}|\d+[.,]?\d*)\b")
STEP_RE = re.compile(r"\b\d+\.\s")
QUESTION_RE = re.compile(r"\?")

LANGUAGE_KEYWORDS: Dict[str, Dict[str, List[str]]] = {
    "nl": {
        "uncertainty": ["mogelijk", "waarschijnlijk", "onzeker", "ik denk", "kan zijn", "volgens mij"],
        "generalization": ["altijd", "nooit", "iedereen", "niemand", "alle"],
        "understanding": ["begrijp", "snap", "duidelijk", "klopt dit"],
        "source_claim": [r"bron\s*:", r"volgens\s+bron", r"volgens\s+(onderzoek|studie)", r"\[[0-9]+\]"],
        "weak_attribution": ["volgens mij", "ik denk", "waarschijnlijk", "vermoedelijk"],
        "tooling": ["bron", "database", "docstore", "tool", "zoek"],
    },
    "en": {
        "uncertainty": ["possibly", "probably", "uncertain", "i think", "might be", "i believe"],
        "generalization": ["always", "never", "everyone", "nobody", "all"],
        "understanding": ["understand", "clear", "does that make sense", "make sense"],
        "source_claim": [r"source\s*:", r"according\s+to", r"research\s+shows", r"studies\s+show", r"\[[0-9]+\]"],
        "weak_attribution": ["i think", "probably", "i believe", "presumably"],
        "tooling": ["source", "database", "docstore", "tool", "search"],
    },
}

KEYWORD_SIGNALS_BY_LANGUAGE: Dict[str, Dict[str, Dict[str, Any]]] = {
    "nl": {
    "C_CoRegulatie": {
        "reward": ["kies", "jij bepaalt", "opties", "waarom wil je", "welke optie"],
        "reward_weight": 0.08,
    },
    "TD_Taakdichtheid": {
        "penalize": ["antwoord is", "oplossing is", "dus het is", "het juiste antwoord"],
        "penalty_weight": 0.1,
        "reward": ["hint", "stap", "probeer eerst", "wil je een aanwijzing"],
        "reward_weight": 0.05,
    },
    "P_Procesfase": {
        "strict_context": ["toets", "examen", "beoordeling", "nakijken"],
        "strict_penalty": 0.12,
        "transparency": ["ik kan je begeleiden", "ik geef geen volledig antwoord", "stap voor stap"],
    },
    "L_LeercontinuiteitTransfer": {
        "reward": ["eerder", "zoals je net zei", "samenvatten", "vorige stap"],
        "reward_weight": 0.08,
    },
    "S_SocialeInteractie": {
        "reward": ["welk perspectief", "wat vind jij", "waarom denk je", "hoe zie jij"],
        "reward_weight": 0.1,
    },
    "V_Vaardigheidspotentieel": {
        "reward": ["wat werkte", "volgende keer", "ander vak", "wat neem je mee"],
        "reward_weight": 0.1,
    },
    },
    "en": {
        "C_CoRegulatie": {"reward": ["choose", "you decide", "options", "why do you want", "which option"], "reward_weight": 0.08},
        "TD_Taakdichtheid": {
            "penalize": ["the answer is", "solution is", "therefore it is", "the correct answer"],
            "penalty_weight": 0.1,
            "reward": ["hint", "step", "try first", "would you like a clue"],
            "reward_weight": 0.05,
        },
        "P_Procesfase": {
            "strict_context": ["test", "exam", "assessment", "grading"],
            "strict_penalty": 0.12,
            "transparency": ["i can guide you", "i will not give the full answer", "step by step"],
        },
        "L_LeercontinuiteitTransfer": {"reward": ["earlier", "as you just said", "summarize", "previous step"], "reward_weight": 0.08},
        "S_SocialeInteractie": {"reward": ["which perspective", "what do you think", "why do you think", "how do you see"], "reward_weight": 0.1},
        "V_Vaardigheidspotentieel": {"reward": ["what worked", "next time", "another subject", "what do you take away"], "reward_weight": 0.1},
    },
}
KEYWORD_SIGNALS = KEYWORD_SIGNALS_BY_LANGUAGE["nl"]


def _keyword_regex(language: str, key: str) -> re.Pattern[str]:
    terms = LANGUAGE_KEYWORDS.get(language, LANGUAGE_KEYWORDS["nl"])[key]
    return re.compile(r"\b(" + "|".join(terms) + r")\b", re.IGNORECASE)


def extract_features(
    transcript_window: List[Dict[str, str]],
    candidate_reply: str,
    sources: List[Dict[str, Any]],
    language: str = "nl",
) -> Dict[str, Any]:
    text = candidate_reply or ""
    lang = language if language in LANGUAGE_KEYWORDS else "nl"
    source_claim_re = re.compile("|".join(LANGUAGE_KEYWORDS[lang]["source_claim"]), re.IGNORECASE)
    weak_attribution = bool(_keyword_regex(lang, "weak_attribution").search(text))
    explicit_source_claim = bool(source_claim_re.search(text) or URL_RE.search(text))
    return {
        "explicit_source_claim": explicit_source_claim,
        "weak_attribution": weak_attribution,
        "citation_present": explicit_source_claim,
        "numeric_claims_count": len(YEAR_NUM_RE.findall(text)),
        "sources_count": len(sources),
        "mentions_tooling": any(k in text.lower() for k in LANGUAGE_KEYWORDS[lang]["tooling"]),
        "question_count": len(QUESTION_RE.findall(text)),
        "check_understanding_count": len(_keyword_regex(lang, "understanding").findall(text)),
        "step_structure_present": bool(STEP_RE.search(text)),
        "uncertainty_markers": len(_keyword_regex(lang, "uncertainty").findall(text)),
        "generalization_markers": len(_keyword_regex(lang, "generalization").findall(text)),
        "language": lang,
        "text_lc": text.lower(),
    }


def _band_for_score(rubric: Dict[str, Any], score: float) -> Dict[str, Any]:
    bands = rubric.get("bands", [])
    for band in bands:
        if band["score_min"] <= score <= band["score_max"]:
            return band
    return bands[-1] if bands else {}


def _safe_snippet(text: str, limit: int = 120) -> str:
    return (text or "")[:limit]


def _evidence_snippets(transcript_window: List[Dict[str, str]], candidate_reply: str) -> List[str]:
    snippets: List[str] = []
    if transcript_window:
        snippets.append(_safe_snippet(transcript_window[-1].get("text", "")))
    if candidate_reply:
        snippets.append(_safe_snippet(candidate_reply))
    return snippets[:2]


def _keyword_hits(text_lc: str, keywords: List[str]) -> int:
    return sum(1 for kw in keywords if kw in text_lc)


def quick_score_for_rubric(rubric_id: str, features: Dict[str, Any], hard_flags: List[str], language: Optional[str] = None) -> float:
    score = 0.6
    if rubric_id == "E_EpistemischeBetrouwbaarheid":
        if "UNGROUNDED_CLAIMS" in hard_flags:
            penalty = 0.2
            if features["uncertainty_markers"] > 0:
                penalty -= min(0.1, 0.03 * features["uncertainty_markers"])
            score -= max(0.08, penalty)
        if "MISLEADING_SOURCES" in hard_flags:
            score -= 0.3
        if features["citation_present"] and features["sources_count"] > 0:
            score += 0.2
        score += min(0.15, 0.05 * features["uncertainty_markers"])
    elif rubric_id == "T_TechnologischeIntegratieVisibility":
        if features["sources_count"] > 0 and features["mentions_tooling"]:
            score += 0.2
        if features["sources_count"] == 0 and features["citation_present"]:
            score -= 0.25
    elif rubric_id == "B_BiasCorrectieFairness":
        score -= min(0.3, 0.1 * features["generalization_markers"])
        if features["question_count"] > 0:
            score += 0.05
    elif rubric_id in {"P_Procesfase", "C_CoRegulatie", "TD_Taakdichtheid"}:
        if features["step_structure_present"]:
            score += 0.1
        if features["check_understanding_count"] > 0:
            score += 0.1
    else:
        if features["question_count"] > 0:
            score += 0.05

    lang = language or features.get("language", "nl")
    signals = KEYWORD_SIGNALS_BY_LANGUAGE.get(lang, KEYWORD_SIGNALS_BY_LANGUAGE["nl"]).get(rubric_id, {})
    text_lc = features.get("text_lc", "")
    if signals:
        reward_keywords = signals.get("reward", [])
        if reward_keywords:
            score += min(0.15, _keyword_hits(text_lc, reward_keywords) * signals.get("reward_weight", 0.05))

        penalize_keywords = signals.get("penalize", [])
        if penalize_keywords:
            score -= min(0.15, _keyword_hits(text_lc, penalize_keywords) * signals.get("penalty_weight", 0.05))

        if rubric_id == "P_Procesfase":
            strict_hits = _keyword_hits(text_lc, signals.get("strict_context", []))
            if strict_hits > 0:
                if _keyword_hits(text_lc, signals.get("transparency", [])) == 0:
                    score -= min(0.15, signals.get("strict_penalty", 0.1))

    return max(0.0, min(1.0, score))


def _llm_score_rubric(
    rubric: Dict[str, Any],
    candidate_reply: str,
    transcript_window: List[Dict[str, str]],
    sources: List[Dict[str, Any]],
    llm_func: Callable[[str], Any],
) -> float:
    """Score a rubric via a caller-provided LLM function, clamped to [0, 1]."""
    bands_text = "\n".join(
        f"Band {band.get('score_min', 0):.2f}-{band.get('score_max', 1):.2f} ({band.get('label', '')}): "
        f"AI observaties: {', '.join(band.get('ai_obs', []))}; flag: {band.get('flag', 'none')}"
        for band in rubric.get("bands", [])
    )
    rub = rubric.get("rubric", {})
    prompt = (
        "Je bent een pedagogisch evaluator. Beoordeel alleen met een getal tussen 0.0 en 1.0.\n"
        f"Rubric: {rub.get('rubric_id', 'unknown')}\n"
        f"Doel: {rub.get('goal', '')}\n"
        f"Bands:\n{bands_text}\n"
        f"Laatste transcript: {transcript_window[-1] if transcript_window else {}}\n"
        f"Bronnen aanwezig: {len(sources)}\n"
        f"AI-antwoord: {candidate_reply}\n"
        "Score:"
    )
    try:
        raw = llm_func(prompt)
        return max(0.0, min(1.0, float(str(raw).strip())))
    except (TypeError, ValueError):
        return 0.3


class GatekeeperOrchestrator:
    def __init__(self, rubrics: List[Dict[str, Any]], config: Optional[GatekeeperConfig] = None):
        self.rubrics = rubrics
        self.config = config or GatekeeperConfig()

    def evaluate(
        self,
        transcript_window: List[Dict[str, str]],
        candidate_reply: str,
        sources: List[Dict[str, Any]],
        tool_usage: Optional[Dict[str, Any]] = None,
    ) -> EvaluationReport:
        default_language = self.rubrics[0].get("rubric", {}).get("language", "nl") if self.rubrics else "nl"
        features = extract_features(transcript_window, candidate_reply, sources, language=default_language)
        hard_flags: List[str] = []
        if features["explicit_source_claim"] and features["sources_count"] == 0:
            hard_flags.append("MISLEADING_SOURCES")
        if features["numeric_claims_count"] > 0 and features["sources_count"] == 0:
            hard_flags.append("UNGROUNDED_CLAIMS")

        assessments: List[RubricAssessment] = []
        pass_t = self.config.thresholds.pass_threshold
        gate_t = self.config.thresholds.gate_threshold

        critical_fail = False
        any_fail = False
        for rubric in self.rubrics:
            rubric_meta = rubric.get("rubric", {})
            rid = rubric_meta.get("rubric_id", "unknown")
            language = rubric_meta.get("language", features.get("language", "nl"))
            score = quick_score_for_rubric(rid, features, hard_flags, language=language)
            if self.config.llm_judge_enabled and self.config.llm_judge_func:
                threshold = self.config.thresholds.pass_threshold
                if abs(score - threshold) <= self.config.llm_gray_zone:
                    score = _llm_score_rubric(rubric, candidate_reply, transcript_window, sources, self.config.llm_judge_func)
            band = _band_for_score(rubric, score)
            flags = list(hard_flags)
            if score < pass_t:
                flags.append(band.get("flag", "LOW_SCORE"))
            if rid in self.config.critical_rubrics and score < gate_t:
                critical_fail = True
            if score < pass_t:
                any_fail = True
            assessments.append(
                RubricAssessment(
                    rubric_id=rid,
                    selected_band={
                        "score_min": band.get("score_min"),
                        "score_max": band.get("score_max"),
                        "label": band.get("label"),
                    },
                    confidence=max(0.3, min(0.95, 0.5 + abs(score - pass_t))),
                    flags=flags,
                    fixes=[band.get("fix", "")],
                    evidence_snippets=_evidence_snippets(transcript_window, candidate_reply),
                    quick_score=score,
                )
            )

        rewrite_instructions = self._rewrite_instructions(assessments)
        mode = self.config.mode
        decision = Decision.PASS
        action_taken = Decision.PASS
        would_have_decided: Optional[Decision] = None
        iterations = 0

        if mode == Mode.NUDGE:
            decision = Decision.PASS if not any_fail else Decision.NUDGE
            action_taken = decision
        elif mode == Mode.CORRECT:
            if any_fail:
                decision = Decision.REWRITE
                action_taken = Decision.REWRITE
        elif mode == Mode.GATEKEEP:
            if critical_fail:
                decision = Decision.BLOCK
                action_taken = Decision.BLOCK
                if not rewrite_instructions:
                    rewrite_instructions = ["Geef een veilige, niet-fabricerende reactie en vraag om verifieerbare bronnen."]
            elif any_fail:
                decision = Decision.REWRITE
                action_taken = Decision.REWRITE

        if mode == Mode.OBSERVE:
            if critical_fail:
                would_have_decided = Decision.BLOCK
            elif any_fail:
                would_have_decided = Decision.REWRITE
            else:
                would_have_decided = Decision.PASS
            decision = Decision.PASS
            action_taken = Decision.PASS

        include_instructions = decision in {Decision.REWRITE, Decision.NUDGE, Decision.BLOCK} or mode == Mode.OBSERVE
        return EvaluationReport(
            global_decision=decision,
            per_rubric=assessments,
            rewrite_instructions=rewrite_instructions if include_instructions else [],
            action_taken=action_taken,
            rewrite_iterations=iterations,
            would_have_decided=would_have_decided,
        )

    def _rewrite_instructions(self, assessments: List[RubricAssessment]) -> List[str]:
        low = sorted(assessments, key=lambda x: x.quick_score)[:3]
        return [f"{a.rubric_id}: {a.fixes[0]}" for a in low if a.fixes and a.fixes[0]]


def report_to_dict(report: EvaluationReport) -> Dict[str, Any]:
    data = {
        "global_decision": report.global_decision.value,
        "per_rubric": [asdict(r) for r in report.per_rubric],
        "rewrite_instructions": report.rewrite_instructions,
        "action_taken": report.action_taken.value,
        "rewrite_iterations": report.rewrite_iterations,
        "rewrite_required": report.rewrite_required,
    }
    if report.would_have_decided is not None:
        data["would_have_decided"] = report.would_have_decided.value
    if report.final_reply is not None:
        data["final_reply"] = report.final_reply
    return data
