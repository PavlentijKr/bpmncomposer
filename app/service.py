import json
import logging
import uuid
from typing import Dict, List

from .gigachat import GigaChatClient, GigaChatError
from .models import GenerateRequest, ValidationIssue, ValidationReport
from .validator_client import ValidatorClient, ValidatorError

logger = logging.getLogger(__name__)


def _build_initial_prompt(text: str, process_name: str, language: str) -> str:
    return f"""
Ты генератор BPMN 2.0 XML. Верни только валидный BPMN 2.0 XML без пояснений.
Требования: один процесс без pool и lane, используй префикс bpmn:, добавь BPMN DI (diagram, plane, shapes, edges).
Минимум: один <bpmn:process id> с именем '{process_name}', startEvent и endEvent соединенные sequenceFlow.
Уникальные id, простой линейный layout координатами (grid).
Описание процесса ({language}): {text}
"""


def _build_repair_prompt(
    text: str,
    language: str,
    current_xml: str,
    errors: List[ValidationIssue],
    process_name: str,
) -> str:
    error_lines = "\n".join(
        _format_error(err) for err in errors
    )
    return f"""
Описание процесса ({language}): {text}
Текущий BPMN XML:
{current_xml}
Ошибки валидации:
{error_lines}
Исправь минимально необходимое, сохрани смысл процесса, верни только BPMN 2.0 XML с DI, один процесс без pool/lane под именем '{process_name}'.
"""


def _format_error(err: ValidationIssue) -> str:
    if hasattr(err, "message"):
        return f"- id={getattr(err, 'id', '') or ''} rule={getattr(err, 'rule', '') or ''} message={getattr(err, 'message', '')}"
    if isinstance(err, dict):
        return f"- id={err.get('id', '')} rule={err.get('rule', '')} message={err.get('message', '')}"
    return f"- message={err}"


def _looks_like_xml(xml: str) -> bool:
    return xml.strip().startswith("<") and "<bpmn:definitions" in xml


def _safe_process_name(request: GenerateRequest) -> str:
    if request.process_name:
        return request.process_name
    return f"Process-{uuid.uuid4().hex[:8]}"


class GenerationService:
    def __init__(self, gigachat: GigaChatClient, validator: ValidatorClient):
        self.gigachat = gigachat
        self.validator = validator

    async def generate(self, request: GenerateRequest, max_attempts: int) -> Dict:
        process_name = _safe_process_name(request)
        debug_attempts: List[Dict] = []

        prompt = _build_initial_prompt(request.text, process_name, request.language)
        xml = None
        for attempt in range(1, max_attempts + 1):
            if attempt == 1:
                xml = await self._call_llm(prompt, request.temperature, repair=False)
            else:
                repair_prompt = _build_repair_prompt(
                    request.text,
                    request.language,
                    xml or "",
                    report.errors,
                    process_name,
                )
                xml = await self._call_llm(repair_prompt, request.temperature, repair=True)

            if not _looks_like_xml(xml):
                report = ValidationReport(errors=[ValidationIssue(message="Invalid XML format")])
            else:
                report = await self._validate(xml)

            debug_attempts.append({
                "attempt": attempt,
                "validation_report": json.loads(report.json()),
            })

            if not report.errors:
                response = {
                    "validated": True,
                    "attempts_used": attempt,
                    "bpmn_xml": xml,
                }
                if request.return_debug:
                    response["debug"] = {"attempts": debug_attempts}
                return response

        response = {
            "validated": False,
            "attempts_used": max_attempts,
            "last_validation_report": json.loads(report.json()),
        }
        if request.return_debug:
            response["debug"] = {"attempts": debug_attempts}
        return response

    async def _call_llm(self, prompt: str, temperature: float, repair: bool) -> str:
        try:
            if repair:
                xml = await self.gigachat.repair_bpmn(prompt, temperature)
            else:
                xml = await self.gigachat.generate_bpmn(prompt, temperature)
        except GigaChatError as exc:
            logger.error("gigachat_error", extra={"error": str(exc)})
            raise
        return xml

    async def _validate(self, xml: str) -> ValidationReport:
        try:
            return await self.validator.validate(xml)
        except ValidatorError as exc:
            logger.error("validator_error", extra={"error": str(exc)})
            raise
