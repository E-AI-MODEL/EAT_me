from __future__ import annotations

from dataclasses import asdict
import re
from typing import Any, Dict, List, Optional

from .models import Decision, EvaluationReport, GatekeeperConfig, Mode, RubricAssessment

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
YEAR_NUM_RE = re.compile(r"\b(\d{4}|\d+[.,]?\d*)\b")
STEP_RE = re.compile(r"\b\d+\.\s")
UNCERTAINTY_RE = re.compile(r"\b(mogelijk|waarschijnlijk|onzeker|ik denk|kan zijn|volgens mij)\b", re.IGNORECASE)
GENERALIZATION_RE = re.compile(r"\b(altijd|nooit|iedereen|niemand|alle)\b", re.IGNORECASE)
QUESTION_RE = re.compile(r"\?")
UNDERSTAND_RE = re.compile(r"\b(begrijp|snap|duidelijk|klopt dit)\b", re.IGNORECASE)
EXPLICIT_SOURCE_CLAIM_RE = re.compile(
    r"(bron\s*:|volgens\s+bron|volgens\s+(onderzoek|studie)|\[[0-9]+\])",
    re.IGNORECASE,
)
WEAK_ATTRIBUTION_RE = re.compile(r"\b(volgens mij|ik denk|waarschijnlijk|vermoedelijk)\b", re.IGNORECASE)

KEYWORD_SIGNALS: Dict[str, Dict[str, Any]] = {
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
}


def extract_features(transcript_window: List[Dict[str, str]], candidate_reply: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    text = candidate_reply or ""
    explicit_source_claim = bool(EXPLICIT_SOURCE_CLAIM_RE.search(text) or URL_RE.search(text))
    weak_attribution = bool(WEAK_ATTRIBUTION_RE.search(text))
    return {
        "explicit_source_claim": explicit_source_claim,
        "weak_attribution": weak_attribution,
        "citation_present": explicit_source_claim,
        "numeric_claims_count": len(YEAR_NUM_RE.findall(text)),
        "sources_count": len(sources),
        "mentions_tooling": any(k in text.lower() for k in ["bron", "database", "docstore", "tool", "zoek"]),
        "question_count": len(QUESTION_RE.findall(text)),
        "check_understanding_count": len(UNDERSTAND_RE.findall(text)),
        "step_structure_present": bool(STEP_RE.search(text)),
        "uncertainty_markers": len(UNCERTAINTY_RE.findall(text)),
        "generalization_markers": len(GENERALIZATION_RE.findall(text)),
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


def quick_score_for_rubric(rubric_id: str, features: Dict[str, Any], hard_flags: List[str]) -> float:
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

    signals = KEYWORD_SIGNALS.get(rubric_id, {})
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
        features = extract_features(transcript_window, candidate_reply, sources)
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
            rid = rubric.get("rubric", {}).get("rubric_id", "unknown")
            score = quick_score_for_rubric(rid, features, hard_flags)
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
