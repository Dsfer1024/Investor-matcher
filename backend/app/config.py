from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    data_cache_dir: str = "./data"
    cache_ttl_hours: int = 24
    claude_model: str = "claude-sonnet-4-6"
    max_investors_to_score: int = 150
    scoring_batch_size: int = 10
    max_concurrent_batches: int = 3

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
