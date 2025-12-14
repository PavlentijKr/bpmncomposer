import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class GigaChatError(Exception):
    pass


class GigaChatClient:
    def __init__(self, api_url: str, token: str, timeout: float = 30.0):
        self.api_url = api_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    async def _post_with_retry(self, payload: dict) -> str:
        backoff = 1.0
        last_exc: Optional[Exception] = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.api_url,
                        headers={
                            "Authorization": f"Bearer {self.token}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict) or "content" not in data:
                    raise GigaChatError("Unexpected response format from GigaChat")
                return data["content"]
            except (httpx.HTTPError, GigaChatError) as exc:
                last_exc = exc
                logger.warning(
                    "gigachat_request_failed",
                    extra={"error": str(exc), "attempt": attempt + 1},
                )
                time.sleep(backoff)
                backoff *= 2
        raise GigaChatError(str(last_exc))

    async def generate_bpmn(self, prompt: str, temperature: float) -> str:
        payload = {"prompt": prompt, "temperature": temperature}
        return await self._post_with_retry(payload)

    async def repair_bpmn(self, prompt: str, temperature: float) -> str:
        payload = {"prompt": prompt, "temperature": temperature}
        return await self._post_with_retry(payload)
