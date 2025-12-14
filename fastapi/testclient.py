import asyncio
from typing import Any, Dict

from . import HTTPException


class Response:
    def __init__(self, status_code: int, json_data: Any):
        self.status_code = status_code
        self._json = json_data

    def json(self):
        return self._json


class TestClient:
    def __init__(self, app):
        self.app = app

    def post(self, path: str, json: Dict[str, Any]):
        coro = self.app.__call__("POST", path, json)
        try:
            result = asyncio.get_event_loop().run_until_complete(coro)
        except RuntimeError:
            result = asyncio.run(coro)
        if isinstance(result, Response):
            return result
        status_code = getattr(result, "status_code", 200)
        content = getattr(result, "content", result)
        return Response(status_code=status_code, json_data=content)
