from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from eatme.evaluator import GatekeeperOrchestrator, report_to_dict
from eatme.models import Decision, GatekeeperConfig
from eatme.parser import load_eat
from eatme.tracing import TraceLogger
from eatme.validator import EATValidator

RewriteFunc = Callable[[str, List[str], Dict[str, Any]], str]


class EATRuntimeGatekeeper:
    def __init__(
        self,
        rubric_dir: str = ".",
        config: Optional[GatekeeperConfig] = None,
        trace_path: str = "trace/eat_trace.jsonl",
        rewrite_func: Optional[RewriteFunc] = None,
    ):
        self.rubric_dir = Path(rubric_dir)
        self.validator = EATValidator()
        self.index_warnings: List[str] = []
        self.rubrics = self._load_rubrics(self.rubric_dir)
        self.orchestrator = GatekeeperOrchestrator(self.rubrics, config=config)
        self.tracer = TraceLogger(trace_path)
        self.rewrite_func = rewrite_func

    def _load_rubrics(self, rubric_dir: Path) -> List[Dict[str, Any]]:
        rubrics: List[Dict[str, Any]] = []
        index_file = rubric_dir / "index.eat"
        rubric_files: List[Path]

        if index_file.exists():
            index_data = load_eat(index_file)
            files = index_data.get("index", {}).get("files", [])
            if not isinstance(files, list):
                raise ValueError(f"Invalid index.eat in {rubric_dir}: index.files must be a list")
            rubric_files = []
            order = index_data.get("index", {}).get("order", [])
            if isinstance(order, list) and files:
                file_rubric_ids = {Path(name).stem for name in files if isinstance(name, str)}
                order_ids = {rid for rid in order if isinstance(rid, str)}
                if file_rubric_ids != order_ids:
                    self.index_warnings.append(
                        "index.order and index.files refer to different rubric sets; loading follows index.files order"
                    )
            for file_name in files:
                target = rubric_dir / file_name
                if not target.exists():
                    raise ValueError(
                        f"Invalid index.eat in {rubric_dir}: referenced rubric '{file_name}' does not exist"
                    )
                rubric_files.append(target)
        else:
            rubric_files = [f for f in sorted(rubric_dir.glob("*.eat")) if f.name != "index.eat"]

        for rubric_file in rubric_files:
            data = load_eat(rubric_file)
            issues = self.validator.validate(data, source=str(rubric_file))
            if issues:
                joined = "; ".join(f"{i.path}: {i.message}" for i in issues)
                raise ValueError(f"Invalid rubric {rubric_file}: {joined}")
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
        rewrite_func: Optional[RewriteFunc] = None,
    ) -> Dict[str, Any]:
        active_rewrite_func = rewrite_func or self.rewrite_func
        context = {
            "transcript_window": transcript_window,
            "sources": sources,
            "tool_usage": tool_usage,
            "mode": self.orchestrator.config.mode.value,
        }

        report = self.orchestrator.evaluate(transcript_window, candidate_reply, sources, tool_usage=tool_usage)
        final_reply: Optional[str] = None
        used_iterations = 0

        if report.global_decision == Decision.REWRITE:
            if active_rewrite_func is None:
                report.rewrite_required = True
            else:
                current_reply = candidate_reply
                max_iter = max(1, self.orchestrator.config.max_rewrite_iterations)
                for iteration in range(1, max_iter + 1):
                    rewritten = active_rewrite_func(current_reply, report.rewrite_instructions, context)
                    if not isinstance(rewritten, str):
                        raise ValueError("rewrite_func must return a string")
                    current_reply = rewritten
                    used_iterations = iteration
                    reevaluated = self.orchestrator.evaluate(transcript_window, current_reply, sources, tool_usage=tool_usage)
                    report = reevaluated
                    if reevaluated.global_decision == Decision.PASS:
                        break
                    if reevaluated.global_decision == Decision.NUDGE:
                        break
                final_reply = current_reply

        report.rewrite_iterations = max(report.rewrite_iterations, used_iterations)
        report.final_reply = final_reply

        self.tracer.log_turn(
            session_id=session_id,
            turn_id=turn_id,
            mode=self.orchestrator.config.mode.value,
            report=report,
            sources=sources,
        )
        return report_to_dict(report)
