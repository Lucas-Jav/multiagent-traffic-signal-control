from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnvironment = Literal["development", "test", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: AppEnvironment = Field(default="development", validation_alias="APP_ENV")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    sumo_binary: str = Field(default="sumo", validation_alias="SUMO_BINARY")
    sumo_home: Path | None = Field(default=None, validation_alias="SUMO_HOME")
    artifacts_dir: Path = Field(default=Path("artifacts"), validation_alias="ARTIFACTS_DIR")
    default_seed: int = Field(default=42, validation_alias="DEFAULT_SEED")


@lru_cache
def get_settings() -> Settings:
    return Settings()
