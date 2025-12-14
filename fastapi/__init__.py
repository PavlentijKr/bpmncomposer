import asyncio
from typing import Any, Callable, Dict, Tuple

from . import status
from .responses import JSONResponse


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: Any = None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class Depends:
    def __init__(self, dependency: Callable):
        self.dependency = dependency


class FastAPI:
    def __init__(self):
        self.routes: Dict[Tuple[str, str], Callable] = {}

    def post(self, path: str, response_model=None, responses=None):
        def decorator(func: Callable):
            self.routes[("POST", path)] = func
            return func

        return decorator

    async def __call__(self, method: str, path: str, json: Dict[str, Any]):
        handler = self.routes.get((method, path))
        if handler is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
        try:
            result = handler.__call__(**json) if not asyncio.iscoroutinefunction(handler) else await handler(**json)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        return result
