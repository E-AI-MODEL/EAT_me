from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from eatme.evaluator import GatekeeperOrchestrator, report_to_dict
from eatme.models import GatekeeperConfig
from eatme.parser import load_eat
from eatme.tracing import TraceLogger
from eatme.validator import EATValidator


class EATRuntimeGatekeeper:
    def __init__(self, rubric_dir: str = ".", config: Optional[GatekeeperConfig] = None, trace_path: str = "trace/eat_trace.jsonl"):
        self.rubric_dir = Path(rubric_dir)
        self.validator = EATValidator()
        self.rubrics = self._load_rubrics(self.rubric_dir)
        self.orchestrator = GatekeeperOrchestrator(self.rubrics, config=config)
        self.tracer = TraceLogger(trace_path)

    def _load_rubrics(self, rubric_dir: Path) -> List[Dict[str, Any]]:
        rubrics = []
        for f in sorted(rubric_dir.glob("*.eat")):
            if f.name == "index.eat":
                continue
            data = load_eat(f)
            issues = self.validator.validate(data, source=str(f))
            if issues:
                joined = "; ".join(f"{i.path}: {i.message}" for i in issues)
                raise ValueError(f"Invalid rubric {f}: {joined}")
            rubrics.append(data)
        return rubrics

    def evaluate_turn(
        self,
        session_id: str,
        turn_id: str,
        transcript_window: List[Dict[str, str]],
        candidate_reply: str,
        sources: List[Dict[str, Any]],
        tool_usage: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        report = self.orchestrator.evaluate(transcript_window, candidate_reply, sources, tool_usage=tool_usage)
        self.tracer.log_turn(
            session_id=session_id,
            turn_id=turn_id,
            mode=self.orchestrator.config.mode.value,
            report=report,
            sources=sources,
        )
        return report_to_dict(report)
