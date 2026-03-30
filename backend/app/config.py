from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    data_cache_dir: str = "./data"
    cache_ttl_hours: int = 24
    claude_model: str = "claude-sonnet-4-6"

    # Pipeline tuning
    longlist_target: int = 40           # investors per Claude call (keeps output under 8192 tokens)
    min_results_guarantee: int = 80     # gap-fill threshold
    max_per_call: int = 40              # hard cap per generate call to avoid token overflow
    max_concurrent_batches: int = 3     # parallel Claude calls

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
