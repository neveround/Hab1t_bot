from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str = Field(...)
    DATABASE_URL: str = "sqlite+aiosqlite:///habits.db"
    TIMEZONE: str = "Europe/Moscow"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


config = Settings()
