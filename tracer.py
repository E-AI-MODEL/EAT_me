import json
from datetime import datetime

class TraceLogger:
    def __init__(self, log_file="eat_trace.log"):
        self.log_file = log_file

    def log(self, **kwargs) -> dict:
        entry = {"timestamp": datetime.now().isoformat(), **kwargs}
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        return entry
