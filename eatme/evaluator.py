from __future__ import annotations

from dataclasses import asdict
import re
from typing import Any, Dict, List, Optional

from .models import Decision, EvaluationReport, GatekeeperConfig, Mode, RubricAssessment

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
YEAR_NUM_RE = re.compile(r"\b(\d{4}|\d+[.,]?\d*)\b")
STEP_RE = re.compile(r"\b\d+\.\s")
UNCERTAINTY_RE = re.compile(r"\b(mogelijk|waarschijnlijk|onzeker|ik denk|kan zijn)\b", re.IGNORECASE)
GENERALIZATION_RE = re.compile(r"\b(altijd|nooit|iedereen|niemand|alle)\b", re.IGNORECASE)
QUESTION_RE = re.compile(r"\?")
UNDERSTAND_RE = re.compile(r"\b(begrijp|snap|duidelijk|klopt dit)\b", re.IGNORECASE)
CITATION_CLAIM_RE = re.compile(r"\b(bron:|volgens|onderzoek|studie|\[[^\]]+\])", re.IGNORECASE)


def extract_features(transcript_window: List[Dict[str, str]], candidate_reply: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    text = candidate_reply or ""
    return {
        "citation_present": bool(CITATION_CLAIM_RE.search(text) or URL_RE.search(text)),
        "numeric_claims_count": len(YEAR_NUM_RE.findall(text)),
        "sources_count": len(sources),
        "mentions_tooling": any(k in text.lower() for k in ["bron", "database", "docstore", "tool", "zoek"]),
        "question_count": len(QUESTION_RE.findall(text)),
        "check_understanding_count": len(UNDERSTAND_RE.findall(text)),
        "step_structure_present": bool(STEP_RE.search(text)),
        "uncertainty_markers": len(UNCERTAINTY_RE.findall(text)),
        "generalization_markers": len(GENERALIZATION_RE.findall(text)),
    }


def _band_for_score(rubric: Dict[str, Any], score: float) -> Dict[str, Any]:
    bands = rubric.get("bands", [])
    for band in bands:
        if band["score_min"] <= score <= band["score_max"]:
            return band
    return bands[-1] if bands else {}


def _evidence_snippets(transcript_window: List[Dict[str, str]], candidate_reply: str) -> List[str]:
    snippets: List[str] = []
    if transcript_window:
        snippets.append(transcript_window[-1]["text"][:120])
    if candidate_reply:
        snippets.append(candidate_reply[:120])
    return snippets[:2]


def quick_score_for_rubric(rubric_id: str, features: Dict[str, Any], hard_flags: List[str]) -> float:
    score = 0.6
    if rubric_id == "E_EpistemischeBetrouwbaarheid":
        if "UNGROUNDED_CLAIMS" in hard_flags:
            score -= 0.2
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
        if features["citation_present"] and features["sources_count"] == 0:
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
        iterations = 0
        if mode == Mode.OBSERVE:
            decision = Decision.PASS if not any_fail else Decision.NUDGE
            action_taken = Decision.PASS
        elif mode == Mode.NUDGE:
            decision = Decision.PASS if not any_fail else Decision.NUDGE
            action_taken = decision
        elif mode == Mode.CORRECT:
            if any_fail:
                decision = Decision.REWRITE
                action_taken = Decision.REWRITE
                iterations = min(1, self.config.max_rewrite_iterations)
            else:
                decision = Decision.PASS
        elif mode == Mode.GATEKEEP:
            if critical_fail:
                decision = Decision.BLOCK
                action_taken = Decision.BLOCK
            elif any_fail:
                decision = Decision.REWRITE
                action_taken = Decision.REWRITE
                iterations = min(1, self.config.max_rewrite_iterations)

        return EvaluationReport(
            global_decision=decision,
            per_rubric=assessments,
            rewrite_instructions=rewrite_instructions if decision in {Decision.REWRITE, Decision.NUDGE, Decision.BLOCK} else [],
            action_taken=action_taken,
            rewrite_iterations=iterations,
        )

    def _rewrite_instructions(self, assessments: List[RubricAssessment]) -> List[str]:
        low = sorted(assessments, key=lambda x: x.quick_score)[:3]
        return [f"{a.rubric_id}: {a.fixes[0]}" for a in low if a.fixes and a.fixes[0]]


def report_to_dict(report: EvaluationReport) -> Dict[str, Any]:
    return {
        "global_decision": report.global_decision.value,
        "per_rubric": [asdict(r) for r in report.per_rubric],
        "rewrite_instructions": report.rewrite_instructions,
        "action_taken": report.action_taken.value,
        "rewrite_iterations": report.rewrite_iterations,
    }
