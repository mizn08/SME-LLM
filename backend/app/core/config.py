import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        extra="ignore",
    )

    UPLOAD_DIR: str = "data/uploads"

    PROJECT_NAME: str = "BNPL Advisor API"
    API_V1_STR: str = "/api/v1"

    # Set DATABASE_URL=sqlite:///./bnpl_local.db for local runs without Docker/Postgres
    DATABASE_URL: str | None = None

    POSTGRES_USER: str = "bnpl"
    POSTGRES_PASSWORD: str = "bnpl_secret"
    POSTGRES_DB: str = "bnpl_advisor"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    ML_MODELS_DIR: str = "app/ml_models"

    # v2: RAG + LangChain agents (optional OpenAI — works offline with BM25 + rules)
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Chutes.ai — OpenAI-compatible POST https://llm.chutes.ai/v1/chat/completions
    # Docs use CHUTES_API_TOKEN; we accept that or CHUTES_API_KEY in .env
    CHUTES_API_KEY: str | None = None
    CHUTES_API_TOKEN: str | None = None
    CHUTES_API_KEY_1: str | None = None
    CHUTES_API_KEY_2: str | None = None
    CHUTES_BASE_URL: str = "https://llm.chutes.ai/v1"
    CHUTES_MODEL: str = "deepseek-ai/DeepSeek-V3.2-TEE"
    CHUTES_CHAT_MODEL: str = "deepseek-ai/DeepSeek-V3.2-TEE"
    CHUTES_FALLBACK_MODEL: str | None = "deepseek-ai/DeepSeek-V3.2-TEE"
    CHUTES_MAX_RETRIES: int = 4
    CHUTES_CHAT_TIMEOUT_SEC: int = 90
    CHUTES_MAX_TOKENS: int = 1024
    CHUTES_TEMPERATURE: float = 0.7

    @property
    def chutes_api_keys(self) -> list[str]:
        seen: set[str] = set()
        keys: list[str] = []
        for key in (
            self.CHUTES_API_KEY,
            self.CHUTES_API_TOKEN,
            self.CHUTES_API_KEY_1,
            self.CHUTES_API_KEY_2,
        ):
            if key and key not in seen:
                seen.add(key)
                keys.append(key)
        return keys

    @property
    def active_llm_api_key(self) -> str | None:
        """Chutes first, then OpenAI."""
        keys = self.chutes_api_keys
        if keys:
            return keys[0]
        return self.OPENAI_API_KEY

    @property
    def active_llm_base_url(self) -> str | None:
        """Chutes OpenAI-compatible base URL (LangChain appends /chat/completions)."""
        return self.CHUTES_BASE_URL if self.chutes_api_keys else None

    @property
    def active_llm_model(self) -> str:
        return self.CHUTES_MODEL if self.chutes_api_keys else self.OPENAI_MODEL

    @property
    def uses_chutes(self) -> bool:
        return bool(self.chutes_api_keys)

    # AWS / production hints (used by deploy docs and health)
    AWS_REGION: str = "ap-southeast-1"
    APP_ENV: str = "development"

    # v3: vector RAG, bandit, RL
    USE_VECTOR_RAG: bool = True
    CHROMA_PERSIST_DIR: str = "data/chroma"
    RL_Q_TABLE_PATH: str = "data/rl_q_table.json"
    FINETUNE_ADAPTER_DIR: str = "data/finetune_adapter"
    FINETUNE_BASE_MODEL: str = "microsoft/Phi-3-mini-4k-instruct"

    # APC+ auth & rate limits (off by default for local demo)
    AUTH_REQUIRED: bool = False
    API_KEY: str | None = None
    JWT_SECRET: str = "change-me-in-production-sme-advisor"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    RATE_LIMIT: str = "120/minute"

    FCM_ENABLED: bool = True
    FIREBASE_CREDENTIALS_PATH: str | None = None
    FIREBASE_CREDENTIALS_JSON: str | None = None
    GUARDRAIL_ENABLED: bool = True
    BUDGET_TOLERANCE_PCT: float = 0.05

    @property
    def firebase_credentials_dict(self) -> dict[str, Any] | None:
        if self.FIREBASE_CREDENTIALS_JSON:
            try:
                return json.loads(self.FIREBASE_CREDENTIALS_JSON)
            except json.JSONDecodeError:
                return None
        if self.FIREBASE_CREDENTIALS_PATH:
            path = Path(self.FIREBASE_CREDENTIALS_PATH)
            if path.is_file():
                return json.loads(path.read_text(encoding="utf-8"))
        return None

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.DATABASE_URL:
            from app.db.url_normalize import normalize_database_url

            return normalize_database_url(self.DATABASE_URL)
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def is_sqlite(self) -> bool:
        return self.sqlalchemy_database_uri.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
