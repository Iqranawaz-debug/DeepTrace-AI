"""Validated local-only configuration; no credential fields."""

import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_data_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share")) / "DeepTraceAI"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DEEPTRACE_", env_file=".env", extra="forbid")
    mode: Literal["mock", "offline"] = "mock"
    allow_paid_apis: Literal[False] = False
    host: Literal["127.0.0.1"] = "127.0.0.1"
    port: int = Field(default=8000, ge=1024, le=65535)
    data_dir: Path = Field(default_factory=default_data_dir)
    origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]

    @field_validator("origins")
    @classmethod
    def local_origins(cls, values: list[str]) -> list[str]:
        for value in values:
            url = urlsplit(value)
            if (
                url.scheme != "http"
                or url.hostname not in {"127.0.0.1", "localhost"}
                or url.username
                or url.password
                or url.path
                or url.query
                or url.fragment
                or not url.port
            ):
                raise ValueError("Only explicit HTTP loopback origins with ports are allowed")
        return values

    @field_validator("data_dir")
    @classmethod
    def absolute_data_dir(cls, path: Path) -> Path:
        if not path.is_absolute():
            raise ValueError("Data directory must be absolute")
        return path
