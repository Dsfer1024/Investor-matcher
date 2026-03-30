from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:4173"]
    data_cache_dir: str = "./data"
    cache_ttl_hours: int = 24
    claude_model: str = "claude-sonnet-4-6"
    max_investors_to_score: int = 150
    scoring_batch_size: int = 10
    max_concurrent_batches: int = 3

    # Public data source URLs — verify these are live before deploy
    openvc_csv_url: str = "https://raw.githubusercontent.com/dvdblk/openvc/main/openvc.csv"
    github_vc_list_urls: list[str] = [
        "https://raw.githubusercontent.com/SimpleVC/open-source-vc-list/main/vc-list.json",
    ]

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
