import json
import logging
from typing import Dict

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from .config import Settings, get_settings
from .gigachat import GigaChatClient, GigaChatError
from .models import GenerateFailureResponse, GenerateRequest, GenerateSuccessResponse
from .service import GenerationService
from .validator_client import ValidatorClient, ValidatorError


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, object] = {
            "level": record.levelname.lower(),
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
            }:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False)


settings = get_settings()
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=settings.log_level, handlers=[handler], force=True)
logger = logging.getLogger(__name__)

app = FastAPI()


def _build_service(settings: Settings) -> GenerationService:
    gigachat_client = GigaChatClient(
        api_url=settings.gigachat_api_url,
        token=settings.gigachat_token,
        timeout=settings.llm_timeout_sec,
    )
    validator_client = ValidatorClient(settings.validator_url, timeout=settings.validator_timeout_sec)
    return GenerationService(gigachat_client, validator_client)


def _resolve_max_attempts(request_max: int, settings: Settings) -> int:
    max_attempts = request_max or settings.max_attempts_default
    if max_attempts > settings.max_attempts_hard_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="max_attempts exceeds hard limit",
        )
    return max_attempts


@app.post(
    "/generate-bpmn",
    response_model=GenerateSuccessResponse,
    responses={
        422: {"model": GenerateFailureResponse},
        400: {"description": "Invalid request"},
        502: {"description": "Upstream error"},
        503: {"description": "Upstream unavailable"},
    },
)
async def generate_bpmn(
    request: GenerateRequest,
    settings: Settings = Depends(get_settings),
):
    if len(request.text) > settings.max_text_len:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="text too long")

    try:
        max_attempts = _resolve_max_attempts(request.max_attempts, settings)
    except HTTPException:
        raise

    service = _build_service(settings)

    try:
        result = await service.generate(request, max_attempts)
    except ValidatorError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="validator error")
    except GigaChatError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="gigachat error")

    if result.get("validated"):
        return JSONResponse(status_code=200, content=result)
    return JSONResponse(status_code=422, content=result)
