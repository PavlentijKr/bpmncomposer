from functools import lru_cache
from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    gigachat_api_url: str = Field("", env="GIGACHAT_API_URL")
    gigachat_token: str = Field("", env="GIGACHAT_TOKEN")
    validator_url: str = Field("http://validator:9000/validate", env="VALIDATOR_URL")
    max_attempts_default: int = Field(3, env="MAX_ATTEMPTS_DEFAULT")
    max_attempts_hard_limit: int = Field(10, env="MAX_ATTEMPTS_HARD_LIMIT")
    max_text_len: int = Field(4000, env="MAX_TEXT_LEN")
    llm_timeout_sec: float = Field(30.0, env="LLM_TIMEOUT_SEC")
    validator_timeout_sec: float = Field(10.0, env="VALIDATOR_TIMEOUT_SEC")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    @validator("max_attempts_default", "max_attempts_hard_limit")
    def validate_attempts(cls, value: int) -> int:
        if value < 1:
            raise ValueError("Attempts must be positive")
        return value


@lru_cache()
def get_settings() -> Settings:
    return Settings()
