import json
from typing import Any, Dict, Iterable, Tuple


class JSONResponse:
    media_type = "application/json"

    def __init__(self, status_code: int, content: Dict[str, Any]):
        self.status_code = status_code
        self.content = content

    def json(self) -> Dict[str, Any]:
        return self.content

    def render(self) -> bytes:
        return json.dumps(self.content, ensure_ascii=False).encode("utf-8")

    def headers(self) -> Iterable[Tuple[bytes, bytes]]:
        return [(b"content-type", self.media_type.encode())]

    def __iter__(self):
        yield self.render().decode("utf-8")
