import json
from typing import Any, Dict


class JSONResponse:
    def __init__(self, status_code: int, content: Dict[str, Any]):
        self.status_code = status_code
        self.content = content

    def json(self) -> Dict[str, Any]:
        return self.content

    def __iter__(self):
        yield json.dumps(self.content)
