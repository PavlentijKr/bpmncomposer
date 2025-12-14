import asyncio
import inspect
import json
from typing import Any, Callable, Dict, Tuple

from pydantic import BaseModel

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

    async def __call__(self, scope: Dict[str, Any], receive, send):
        if scope.get("type") != "http":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "unsupported scope")
        body_bytes = await self._receive_body(receive)
        data: Dict[str, Any] = {}
        if body_bytes:
            try:
                data = json.loads(body_bytes.decode("utf-8"))
            except json.JSONDecodeError:
                data = {}
        response = await self._dispatch_request(scope["method"], scope["path"], data)
        await self._send_response(send, response)

    async def _dispatch_request(self, method: str, path: str, payload: Dict[str, Any]):
        handler = self.routes.get((method, path))
        if handler is None:
            return JSONResponse(status.HTTP_404_NOT_FOUND, {"detail": "not found"})
        try:
            kwargs = await self._resolve_parameters(handler, payload)
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**kwargs)
            else:
                result = handler(**kwargs)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        except ValueError as exc:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": str(exc)},
            )
        return self._ensure_response(result)

    async def _resolve_parameters(self, handler: Callable, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = payload or {}
        kwargs: Dict[str, Any] = {}
        signature = inspect.signature(handler)
        for name, parameter in signature.parameters.items():
            default = parameter.default
            if isinstance(default, Depends):
                dependency = default.dependency
                value = dependency()
                if asyncio.iscoroutine(value):
                    value = await value
                kwargs[name] = value
                continue

            annotation = parameter.annotation
            if (
                isinstance(annotation, type)
                and issubclass(annotation, BaseModel)
            ):
                kwargs[name] = annotation(**payload)
            else:
                kwargs[name] = payload.get(name)
        return kwargs

    def _ensure_response(self, result: Any) -> JSONResponse:
        if isinstance(result, JSONResponse):
            return result
        if hasattr(result, "status_code") and hasattr(result, "content"):
            return JSONResponse(status_code=result.status_code, content=result.content)
        if hasattr(result, "dict"):
            content = result.dict()
        elif isinstance(result, dict):
            content = result
        else:
            content = {"result": result}
        return JSONResponse(status_code=200, content=content)

    async def _receive_body(self, receive) -> bytes:
        body = b""
        while True:
            message = await receive()
            if message["type"] != "http.request":
                continue
            body += message.get("body", b"")
            if not message.get("more_body"):
                break
        return body

    async def _send_response(self, send, response: JSONResponse) -> None:
        body = response.render()
        await send(
            {
                "type": "http.response.start",
                "status": response.status_code,
                "headers": list(response.headers()),
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body,
            }
        )
