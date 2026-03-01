from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .evaluator import report_to_dict
from .models import EvaluationReport


class TraceLogger:
    def __init__(self, log_path: str = "trace/eat_trace.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_turn(
        self,
        session_id: str,
        turn_id: str,
        mode: str,
        report: EvaluationReport,
        sources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        entry = {
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
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry
