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

    # Chutes.ai — OpenAI-compatible inference (takes priority over OpenAI when set)
    CHUTES_API_KEY: str | None = None
    CHUTES_API_KEY_1: str | None = None
    CHUTES_API_KEY_2: str | None = None
    CHUTES_BASE_URL: str = "https://llm.chutes.ai/v1"
    CHUTES_MODEL: str = "deepseek-ai/DeepSeek-V3-0324"

    @property
    def active_llm_api_key(self) -> str | None:
        """Returns the active LLM API key: Chutes first, then OpenAI."""
        return self.CHUTES_API_KEY or self.OPENAI_API_KEY

    @property
    def active_llm_base_url(self) -> str | None:
        """Returns the base URL override for Chutes; None falls back to OpenAI default."""
        return self.CHUTES_BASE_URL if self.CHUTES_API_KEY else None

    @property
    def active_llm_model(self) -> str:
        """Returns the model name to use: Chutes model if Chutes key is set, else OpenAI model."""
        return self.CHUTES_MODEL if self.CHUTES_API_KEY else self.OPENAI_MODEL

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
