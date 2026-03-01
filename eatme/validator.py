from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .parser import load_eat


@dataclass
class ValidationIssue:
    path: str
    message: str


class EATValidator:
    def __init__(self, tolerance: float = 0.02):
        self.tolerance = tolerance

    def validate(self, rubric: Dict[str, Any], source: str = "<memory>") -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        meta = rubric.get("meta")
        if not isinstance(meta, dict):
            issues.append(ValidationIssue(f"{source}.meta", "missing object 'meta'"))
        else:
            if meta.get("version") != 2.0:
                issues.append(ValidationIssue(f"{source}.meta.version", "must equal 2.0"))
            if not isinstance(meta.get("locked"), bool):
                issues.append(ValidationIssue(f"{source}.meta.locked", "must be boolean"))

        rub = rubric.get("rubric")
        required_rubric = ["rubric_id", "name", "dimension", "rubric_version", "language", "goal"]
        if not isinstance(rub, dict):
            issues.append(ValidationIssue(f"{source}.rubric", "missing object 'rubric'"))
            rubric_id = "<unknown>"
        else:
            rubric_id = str(rub.get("rubric_id", "<unknown>"))
            for key in required_rubric:
                if key not in rub or rub.get(key) in (None, ""):
                    issues.append(ValidationIssue(f"{source}.rubric.{key}", f"required for rubric_id={rubric_id}"))

        bands = rubric.get("bands")
        if not isinstance(bands, list):
            issues.append(ValidationIssue(f"{source}.bands", "must be a list of 5 bands"))
            return issues
        if len(bands) != 5:
            issues.append(ValidationIssue(f"{source}.bands", f"must contain exactly 5 bands, found {len(bands)}"))

        ranges: List[tuple[float, float, int]] = []
        for i, band in enumerate(bands):
            bpath = f"{source}.bands[{i}]"
            if not isinstance(band, dict):
                issues.append(ValidationIssue(bpath, f"must be object for rubric_id={rubric_id}"))
                continue
            mn, mx = band.get("score_min"), band.get("score_max")
            if not isinstance(mn, (int, float)) or not isinstance(mx, (int, float)):
                issues.append(ValidationIssue(bpath, "score_min and score_max must be numbers"))
                continue
            mnf, mxf = float(mn), float(mx)
            if not (0 <= mnf < mxf <= 1):
                issues.append(ValidationIssue(bpath, f"range invalid: {mnf}-{mxf}; expected 0<=min<max<=1"))
            ranges.append((mnf, mxf, i))
            for list_key in ["learner_obs", "ai_obs"]:
                val = band.get(list_key)
                if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
                    issues.append(ValidationIssue(f"{bpath}.{list_key}", "must be list[str]"))
            for key in ["label", "description", "flag", "fix"]:
                if not isinstance(band.get(key), str):
                    issues.append(ValidationIssue(f"{bpath}.{key}", "must be string"))

        if ranges:
            ranges.sort(key=lambda x: x[0])
            if abs(ranges[0][0] - 0.0) > self.tolerance:
                issues.append(ValidationIssue(f"{source}.bands[{ranges[0][2]}].score_min", "first band must start at 0.0"))
            if abs(ranges[-1][1] - 1.0) > self.tolerance:
                issues.append(ValidationIssue(f"{source}.bands[{ranges[-1][2]}].score_max", "last band must end at 1.0"))
            for (prev_min, prev_max, prev_i), (curr_min, curr_max, curr_i) in zip(ranges, ranges[1:]):
                if curr_min - prev_max > self.tolerance:
                    issues.append(ValidationIssue(
                        f"{source}.bands[{curr_i}].score_min",
                        f"gap detected after band[{prev_i}] ({prev_max} -> {curr_min})",
                    ))
                if prev_max - curr_min > self.tolerance:
                    issues.append(ValidationIssue(
                        f"{source}.bands[{curr_i}].score_min",
                        f"overlap detected with band[{prev_i}] ({prev_max} -> {curr_min})",
                    ))
        return issues

    def validate_path(self, path: str | Path) -> List[ValidationIssue]:
        p = Path(path)
        files: Iterable[Path]
        if p.is_dir():
            files = sorted(p.glob("*.eat"))
        else:
            files = [p]
        issues: List[ValidationIssue] = []
        for f in files:
            data = load_eat(f)
            issues.extend(self.validate(data, source=str(f)))
        return issues
