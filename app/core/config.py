from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

Global_BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    APP_NAME: str = "Paper Agent LLM"
    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"
    CORS_ORIGINS: str = "http://localhost:5173"

    DATABASE_URL: str = "mysql+aiomysql://root:123456@127.0.0.1:3306/paper_agent_llm"
    DB_ECHO: bool = False
    BASE_DIR: Path = Global_BASE_DIR

    FILE_STORAGE_ROOT: str = ".data/storage"
    MAX_UPLOAD_FILES: int = 3
    MAX_UPLOAD_SIZE_MB: int = 25

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
