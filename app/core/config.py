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

    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100

    # Day5：Embedding model配置
    EMBEDDING_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-v4"
    EMBEDDING_VECTOR_SIZE: int = 256
    EMBEDDING_BATCH_SIZE: int = 8
    EMBEDDING_TIMEOUT_SECONDS: int = 60

    # Day5：Qdrant 配置
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_NAME: str = "paper_agent_chunks"

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
