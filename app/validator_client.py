import httpx
from typing import List, Tuple

from .models import ValidationIssue, ValidationReport


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
        try:
            return _parse_validation_response(data)
        except ValueError as exc:
            raise ValidatorError(str(exc)) from exc


def _parse_validation_response(data) -> ValidationReport:
    if not isinstance(data, dict):
        raise ValueError("Unexpected validator response format")

    if "errors" in data or "warnings" in data:
        return ValidationReport.parse_obj({
            "errors": data.get("errors", []),
            "warnings": data.get("warnings", []),
        })

    issues = _extract_bpmnlint_issues(data)
    if issues is None:
        raise ValueError("Unexpected validator response format")

    errors, warnings = issues
    return ValidationReport(errors=errors, warnings=warnings)


def _extract_bpmnlint_issues(data: dict) -> Tuple[List[ValidationIssue], List[ValidationIssue]] | None:
    """Support bpmnlint-style responses.

    bpmnlint typically returns an ``issues`` array or a single key
    containing a list of issues per file. Each issue entry carries a
    ``category``/``severity`` describing whether it is an error or a
    warning. Any unrecognized structure falls back to ``None``.
    """

    raw_issues = None

    if isinstance(data.get("issues"), list):
        raw_issues = data["issues"]
    elif len(data) == 1:
        maybe_list = next(iter(data.values()))
        if isinstance(maybe_list, list):
            raw_issues = maybe_list

    if raw_issues is None:
        return None

    errors: List[ValidationIssue] = []
    warnings: List[ValidationIssue] = []

    for issue in raw_issues:
        category = None
        if isinstance(issue, dict):
            category = issue.get("category") or issue.get("severity")
        target = warnings if str(category).lower() in {"warn", "warning"} else errors
        target.append(ValidationIssue.parse_obj(issue))

    return errors, warnings
