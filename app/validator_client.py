import httpx
from .models import ValidationReport


class ValidatorError(Exception):
    pass


class ValidatorClient:
    def __init__(self, url: str, timeout: float = 10.0):
        self.url = url
        self.timeout = timeout

    async def validate(self, xml: str) -> ValidationReport:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.url, content=xml.encode("utf-8"), headers={"Content-Type": "text/xml"}
                )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise ValidatorError(str(exc)) from exc
        if not isinstance(data, dict):
            raise ValidatorError("Unexpected validator response format")
        return ValidationReport.parse_obj(data)
