from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_eat(path: str | Path) -> Dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    return json.loads(text)


def dump_eat(data: Dict[str, Any], path: str | Path) -> None:
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
