from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", Path(".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "CareerPilot"
    careerpilot_testing: bool = False

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "careerpilot"
    mysql_password: str = "careerpilot"
    mysql_database: str = "careerpilot"
    database_url: str | None = None

    jwt_secret: str = "dev-only-change-me"
    jwt_access_minutes: int = 30
    jwt_refresh_days: int = 7

    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    upload_dir: str = "storage"
    max_upload_mb: int = 10
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
