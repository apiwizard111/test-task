from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    openai_base_url: str | None = None
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    data_dir: Path = BACKEND_ROOT / "data"
    sample_repo_dir: Path = REPO_ROOT / "sample_repo"
    log_level: str = "INFO"
    debug_retrieval: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
