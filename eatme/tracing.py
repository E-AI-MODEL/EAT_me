from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .models import EvaluationReport


class TraceLogger:
    def __init__(self, log_path: str = "trace/eat_trace.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _clip(self, text: str, limit: int = 120) -> str:
        return (text or "")[:limit]

    def log_turn(
        self,
        session_id: str,
        turn_id: str,
        mode: str,
        report: EvaluationReport,
        sources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        entry: Dict[str, Any] = {
            "session_id": session_id,
            "turn_id": turn_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "decision": report.global_decision.value,
            "rubrics": [
                {
                    "rubric_id": r.rubric_id,
                    "score": r.quick_score,
                    "band": r.selected_band,
                    "confidence": r.confidence,
                    "flags": r.flags,
                    "evidence_snippets": [self._clip(s) for s in r.evidence_snippets[:2]],
                }
                for r in report.per_rubric
            ],
            "action_taken": report.action_taken.value,
            "rewrite_iterations": report.rewrite_iterations,
            "sources": [
                {
                    "type": s.get("type"),
                    "title": s.get("title"),
                    "url": s.get("url"),
                    "retrieved_at": s.get("retrieved_at"),
                    "reliability_hint": s.get("reliability_hint"),
                }
                for s in sources
            ],
            "suggested_fixes": report.rewrite_instructions,
            "rewrite_required": report.rewrite_required,
        }
        if report.would_have_decided is not None:
            entry["would_have_decided"] = report.would_have_decided.value
        if report.final_reply is not None:
            entry["final_reply"] = self._clip(report.final_reply)

        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry


class TraceAggregator:
    def __init__(self, trace_path: str = "trace/eat_trace.jsonl"):
        self.trace_path = Path(trace_path)

    def _load_entries(self) -> List[Dict[str, Any]]:
        if not self.trace_path.exists():
            return []
        entries: List[Dict[str, Any]] = []
        for line in self.trace_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entries.append(json.loads(line))
        return entries

    def session_summary(self, session_id: str) -> Dict[str, Any]:
        return self._summarize([e for e in self._load_entries() if e.get("session_id") == session_id], session_id=session_id)

    def global_summary(self) -> Dict[str, Any]:
        return self._summarize(self._load_entries(), session_id=None)

    def _summarize(self, entries: List[Dict[str, Any]], session_id: str | None) -> Dict[str, Any]:
        if not entries:
            return {"session_id": session_id, "turns": 0} if session_id is not None else {"turns": 0}
        rubric_scores: Dict[str, List[float]] = {}
        decisions: Dict[str, int] = {}
        total_rewrites = 0
        blocks = 0
        rewrites = 0
        for entry in entries:
            decision = entry.get("decision", "unknown")
            decisions[decision] = decisions.get(decision, 0) + 1
            total_rewrites += int(entry.get("rewrite_iterations", 0) or 0)
            if entry.get("action_taken") == "BLOCK":
                blocks += 1
            if entry.get("action_taken") == "REWRITE":
                rewrites += 1
            for rubric in entry.get("rubrics", []):
                rid = rubric.get("rubric_id", "unknown")
                score = float(rubric.get("score", 0.0) or 0.0)
                rubric_scores.setdefault(rid, []).append(score)
        rubric_averages = {rid: sum(scores) / len(scores) for rid, scores in rubric_scores.items() if scores}
        weakest = min(rubric_averages.items(), key=lambda item: item[1]) if rubric_averages else None
        summary: Dict[str, Any] = {
            "turns": len(entries),
            "decisions": decisions,
            "total_rewrites": total_rewrites,
            "blocks": blocks,
            "rewrites": rewrites,
            "rubric_averages": rubric_averages,
            "weakest_rubric": weakest,
        }
        if session_id is not None:
            summary["session_id"] = session_id
        return summary
