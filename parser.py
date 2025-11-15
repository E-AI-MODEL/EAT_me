import yaml
from typing import Dict, Any

class EATParser:
    def load(self, path: str) -> Dict[str, Any]:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        data = yaml.safe_load(content)
        return data
