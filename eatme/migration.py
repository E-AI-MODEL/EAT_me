from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Tuple

from .parser import dump_eat

BAND_RE = re.compile(r"band\s*([0-9.]+)\s*-\s*([0-9.]+)", re.IGNORECASE)


def _strip_value(v: str) -> Any:
    v = v.strip()
    if v.startswith('"') and v.endswith('"'):
        return v[1:-1]
    if v.startswith("'") and v.endswith("'"):
        return v[1:-1]
    if v.lower() in {"true", "false"}:
        return v.lower() == "true"
    return v


def parse_legacy_rubric_text(text: str) -> Dict[str, Any]:
    lines = text.splitlines()
    rubric: Dict[str, Any] = {}
    bands: Dict[str, Dict[str, Any]] = {}
    links: Dict[str, Any] = {}
    section = None
    current_band = None
    current_list = None

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("rubric:"):
            section = "rubric"
            continue
        if line.startswith("bands:"):
            section = "bands"
            continue
        if line.startswith("links:"):
            section = "links"
            continue

        if section == "rubric" and line.startswith("  ") and ":" in line:
            k, v = line.strip().split(":", 1)
            rubric[k.strip()] = _strip_value(v)
        elif section == "bands":
            if line.startswith("  band") and line.endswith(":"):
                current_band = line.strip()[:-1]
                bands[current_band] = {}
                current_list = None
            elif line.startswith("    ") and current_band and ":" in line:
                k, v = line.strip().split(":", 1)
                if v.strip() == "":
                    bands[current_band][k.strip()] = []
                    current_list = k.strip()
                else:
                    bands[current_band][k.strip()] = _strip_value(v)
                    current_list = None
            elif line.startswith("      - ") and current_band and current_list:
                bands[current_band][current_list].append(line.strip()[2:].strip())
        elif section == "links" and line.startswith("  ") and ":" in line:
            k, v = line.strip().split(":", 1)
            links[k.strip()] = _strip_value(v)

    return {"rubric": rubric, "bands": bands, "links": links}


def migrate_rubric(data: Dict[str, Any], lock: bool = True, add_updated: bool = True) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    out["meta"] = {"version": 2.0, "locked": lock}
    if add_updated:
        out["meta"]["updated"] = datetime.now(timezone.utc).isoformat()

    old_r = data.get("rubric", {})
    rubric = dict(old_r) if isinstance(old_r, dict) else {}
    if "version" in rubric:
        rubric["rubric_version"] = rubric.pop("version")
    out["rubric"] = rubric

    converted: List[Dict[str, Any]] = []
    bands_obj = data.get("bands", {})
    if isinstance(bands_obj, list):
        converted = bands_obj
    elif isinstance(bands_obj, dict):
        for k, v in bands_obj.items():
            m = BAND_RE.search(str(k))
            if not m:
                continue
            band = dict(v)
            converted.append(
                {
                    "score_min": float(m.group(1)),
                    "score_max": float(m.group(2)),
                    "label": band.get("label", ""),
                    "description": band.get("description", ""),
                    "learner_obs": band.get("learner_obs", []),
                    "ai_obs": band.get("ai_obs", []),
                    "flag": band.get("flag", ""),
                    "fix": band.get("fix", ""),
                }
            )
    converted.sort(key=lambda b: b["score_min"])
    out["bands"] = converted
    if "links" in data:
        out["links"] = data["links"]
    if "cycle" in data:
        out["cycle"] = data["cycle"]
    return out


def migrate_file(path: str | Path) -> None:
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = parse_legacy_rubric_text(raw)
    dump_eat(migrate_rubric(data), p)


def migrate_directory(path: str | Path) -> List[Tuple[Path, str]]:
    root = Path(path)
    changed: List[Tuple[Path, str]] = []
    for f in sorted(root.glob("*.eat")):
        if f.name == "index.eat":
            continue
        migrate_file(f)
        data = json.loads(f.read_text(encoding="utf-8"))
        changed.append((f, data.get("rubric", {}).get("rubric_id", f.stem)))
    return changed
