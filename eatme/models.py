from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Mode(str, Enum):
    OBSERVE = "OBSERVE"
    NUDGE = "NUDGE"
    CORRECT = "CORRECT"
    GATEKEEP = "GATEKEEP"


class Decision(str, Enum):
    PASS = "PASS"
    NUDGE = "NUDGE"
    REWRITE = "REWRITE"
    BLOCK = "BLOCK"


@dataclass
class Thresholds:
    pass_threshold: float = 0.5
    gate_threshold: float = 0.5


@dataclass
class GatekeeperConfig:
    mode: Mode = Mode.OBSERVE
    thresholds: Thresholds = field(default_factory=Thresholds)
    critical_rubrics: List[str] = field(
        default_factory=lambda: [
            "E_EpistemischeBetrouwbaarheid",
            "B_BiasCorrectieFairness",
            "T_TechnologischeIntegratieVisibility",
        ]
    )
    llm_judge_enabled: bool = False
    llm_gray_zone: float = 0.05
    max_rewrite_iterations: int = 2


@dataclass
class RubricAssessment:
    rubric_id: str
    selected_band: Dict[str, Any]
    confidence: float
    flags: List[str]
    fixes: List[str]
    evidence_snippets: List[str]
    quick_score: float


@dataclass
class EvaluationReport:
    global_decision: Decision
    per_rubric: List[RubricAssessment]
    rewrite_instructions: List[str]
    action_taken: Decision
    rewrite_iterations: int = 0
    would_have_decided: Optional[Decision] = None
    rewrite_required: bool = False
    final_reply: Optional[str] = None
