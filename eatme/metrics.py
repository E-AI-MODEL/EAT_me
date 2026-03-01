from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict


def compute_metrics(trace_path: str | Path) -> Dict[str, Any]:
    path = Path(trace_path)
    lines = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    total = len(lines) or 1
    rewrite_rate = sum(1 for l in lines if l.get("action_taken") == "REWRITE") / total
    block_rate = sum(1 for l in lines if l.get("action_taken") == "BLOCK") / total

    fails = Counter()
    totals = Counter()
    session_scores = defaultdict(list)
    for l in lines:
        sid = l.get("session_id", "unknown")
        for r in l.get("rubrics", []):
            rid = r.get("rubric_id", "unknown")
            score = float(r.get("score", 0.0))
            totals[rid] += 1
            if score < 0.5:
                fails[rid] += 1
            session_scores[sid].append(score)

    fail_rate_per_rubric = {rid: (fails[rid] / totals[rid]) for rid in totals}
    average_score_trend = {sid: (sum(vals) / len(vals) if vals else 0.0) for sid, vals in session_scores.items()}
    return {
        "rewrite_rate": rewrite_rate,
        "block_rate": block_rate,
        "fail_rate_per_rubric": fail_rate_per_rubric,
        "average_score_trend": average_score_trend,
    }
