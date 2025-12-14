import logging
import time
import uuid
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class GigaChatError(Exception):
    pass


class GigaChatClient:
    def __init__(
        self,
        api_url: str,
        auth_url: str,
        credentials: str,
        scope: str,
        model: str,
        timeout: float = 30.0,
        token: str = "",
    ):
        self.api_url = api_url.rstrip("/")
        self.auth_url = auth_url
        self.credentials = credentials
        self.scope = scope
        self.model = model
        self.timeout = timeout
        self._access_token = token
        self._token_expires_at: Optional[float] = None

    async def _get_access_token(self) -> str:
        if self._access_token and (
            self._token_expires_at is None or self._token_expires_at > time.time() + 30
        ):
            return self._access_token

        if not self.auth_url or not self.credentials:
            raise GigaChatError("GigaChat credentials are not configured")

        headers = {
            "Authorization": f"Bearer {self.credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
        }
        data = {"scope": self.scope}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.auth_url, headers=headers, data=data)
        response.raise_for_status()

        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise GigaChatError("Failed to obtain GigaChat access token")

        expires_at_raw = payload.get("expires_at")
        expires_in = payload.get("expires_in")
        expires_at = self._parse_expiry(expires_at_raw, expires_in)

        self._access_token = token
        self._token_expires_at = expires_at
        return token

    def _parse_expiry(self, expires_at: object, expires_in: object) -> Optional[float]:
        now = time.time()
        if isinstance(expires_at, (int, float)):
            return float(expires_at)
        if isinstance(expires_at, str):
            try:
                parsed = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                return parsed.timestamp()
            except ValueError:
                pass
            try:
                return float(expires_at)
            except ValueError:
                pass
        if isinstance(expires_in, (int, float)):
            return now + float(expires_in)
        return now + 25 * 60

    async def _post_completion_with_retry(self, payload: dict) -> str:
        backoff = 1.0
        last_exc: Optional[Exception] = None
        for attempt in range(3):
            try:
                token = await self._get_access_token()
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.api_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                response.raise_for_status()
                return self._extract_content(response.json())
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code == 401:
                    self._access_token = ""
                    self._token_expires_at = None
                logger.warning(
                    "gigachat_request_failed",
                    extra={"error": str(exc), "attempt": attempt + 1},
                )
                time.sleep(backoff)
                backoff *= 2
            except (httpx.HTTPError, GigaChatError) as exc:
                last_exc = exc
                logger.warning(
                    "gigachat_request_failed",
                    extra={"error": str(exc), "attempt": attempt + 1},
                )
                time.sleep(backoff)
                backoff *= 2
        raise GigaChatError(str(last_exc))

    @staticmethod
    def _extract_content(data: dict) -> str:
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise GigaChatError("Unexpected response format from GigaChat")

    async def generate_bpmn(self, prompt: str, temperature: float) -> str:
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        return await self._post_completion_with_retry(payload)

    async def repair_bpmn(self, prompt: str, temperature: float) -> str:
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        return await self._post_completion_with_retry(payload)
