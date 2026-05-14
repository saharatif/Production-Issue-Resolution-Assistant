"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    pinecone_api_key: str = ""
    pinecone_index: str = "manufacturing-kb"
    database_url: str = ""
    report_dir: str = "/tmp/reports"
    langchain_tracing_v2: str = "false"
    langchain_api_key: str = ""
    langchain_project: str = "mfg-issue-resolution"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
