from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set

CYCLE_PHASES = ["P", "TD", "C", "V", "T", "E", "L"]

PHASE_PREFIX_MAP: Dict[str, str] = {
    "P": "P_Procesfase",
    "TD": "TD_Taakdichtheid",
    "C": "C_CoRegulatie",
    "V": "V_Vaardigheidspotentieel",
    "T": "T_TechnologischeIntegratieVisibility",
    "E": "E_EpistemischeBetrouwbaarheid",
    "L": "L_LeercontinuiteitTransfer",
}


@dataclass
class CycleManager:
    loop: bool = True
    start: str = "P"

    def __post_init__(self) -> None:
        if self.start not in CYCLE_PHASES:
            raise ValueError(f"Unknown cycle phase '{self.start}'. Expected one of {CYCLE_PHASES}.")
        self.index = CYCLE_PHASES.index(self.start)

    @property
    def current(self) -> str:
        return CYCLE_PHASES[self.index]

    def advance(self) -> str:
        if self.index == len(CYCLE_PHASES) - 1 and not self.loop:
            return self.current
        self.index = (self.index + 1) % len(CYCLE_PHASES)
        return self.current


def focused_rubric_ids(active_phase: str, neighbor_span: int = 1) -> Set[str]:
    if active_phase not in CYCLE_PHASES:
        return set()
    active_idx = CYCLE_PHASES.index(active_phase)
    focus_ids: Set[str] = set()
    for offset in range(-neighbor_span, neighbor_span + 1):
        phase = CYCLE_PHASES[(active_idx + offset) % len(CYCLE_PHASES)]
        focus_ids.add(PHASE_PREFIX_MAP[phase])
    return focus_ids
