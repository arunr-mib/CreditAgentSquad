"""Application settings, read from environment variables (and `.env` when present)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://squad:squad@localhost:5432/credit_agent_squad"
    test_database_url: str = "postgresql+psycopg://squad:squad@localhost:5432/credit_agent_squad_test"
    session_secret: str = "change-me"
    session_hours: int = 12
    file_store_dir: str = "./var/files"

    # Model access for the product's agents. The app never reads ANTHROPIC_BASE_URL from the
    # host environment: the base URL is set explicitly so a developer shell cannot redirect it.
    anthropic_api_key: str = ""
    squad_anthropic_base_url: str = "https://api.anthropic.com"
    squad_model: str = "claude-opus-5-5"
    squad_llm_mode: str = "recorded"  # recorded | live | record
    squad_recordings_dir: str = "./evals/recordings"


@lru_cache
def get_settings() -> Settings:
    return Settings()
