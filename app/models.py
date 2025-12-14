from typing import List, Optional
from pydantic import BaseModel, Field, validator


class ValidationIssue(BaseModel):
    id: Optional[str] = None
    message: str
    rule: Optional[str] = None


class ValidationReport(BaseModel):
    errors: List[ValidationIssue] = Field(default_factory=list)
    warnings: List[ValidationIssue] = Field(default_factory=list)


class GenerateRequest(BaseModel):
    text: str
    process_name: Optional[str] = None
    language: str = "ru"
    max_attempts: Optional[int] = None
    temperature: float = 0.2
    return_debug: bool = False

    @validator("text")
    def text_must_not_be_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("text must not be empty")
        return value

    @validator("language")
    def language_supported(cls, value: str) -> str:
        if value not in {"ru", "en"}:
            raise ValueError("language must be 'ru' or 'en'")
        return value

    @validator("temperature")
    def temperature_range(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("temperature must be between 0 and 1")
        return value

    @validator("max_attempts")
    def attempts_positive(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 1:
            raise ValueError("max_attempts must be positive")
        return value


class GenerateSuccessResponse(BaseModel):
    validated: bool = True
    attempts_used: int
    bpmn_xml: str
    debug: Optional[dict] = None


class GenerateFailureResponse(BaseModel):
    validated: bool = False
    attempts_used: int
    last_validation_report: ValidationReport
    debug: Optional[dict] = None
