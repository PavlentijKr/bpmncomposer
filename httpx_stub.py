import json
from typing import Any, Dict


class HTTPError(Exception):
    pass


class HTTPStatusError(HTTPError):
    def __init__(self, message: str, request=None, response=None):
        super().__init__(message)
        self.request = request
        self.response = response


class Response:
    def __init__(self, status_code: int = 200, json: Dict[str, Any] | None = None, content: bytes | None = None):
        self.status_code = status_code
        self._json = json
        self.content = content

    def json(self) -> Dict[str, Any]:
        if self._json is None:
            raise ValueError("No json provided")
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPStatusError(f"HTTP {self.status_code}", response=self)


class AsyncClient:
    def __init__(self, timeout: float | None = None):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(
        self,
        url: str,
        headers: Dict[str, str] | None = None,
        json: Dict[str, Any] | None = None,
        content: bytes | None = None,
        data: Dict[str, Any] | None = None,
        **kwargs,
    ):
        raise HTTPError("No network available in stub AsyncClient")
