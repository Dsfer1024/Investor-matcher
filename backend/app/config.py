from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    data_cache_dir: str = "./data"
    cache_ttl_hours: int = 24
    claude_model: str = "claude-sonnet-4-6"

    # Pipeline tuning
    longlist_target: int = 50           # investors per single Claude call
    max_concurrent_batches: int = 3

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
