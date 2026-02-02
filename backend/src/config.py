"""Configuration management for the Mastermind platform."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from pathlib import Path
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/collab.db",
        alias="DATABASE_URL"
    )

    # Personas path - points to the AI-Personas repo
    # Default looks for AI-Personas as sibling directory or in common locations
    personas_path: Path = Field(
        default=Path(os.environ.get("PERSONAS_PATH", "../AI-Personas/experts")),
        alias="PERSONAS_PATH"
    )

    skills_path: Path = Field(
        default=Path(os.environ.get("SKILLS_PATH", "../AI-Personas/skills")),
        alias="SKILLS_PATH"
    )

    domains_path: Path = Field(
        default=Path(os.environ.get("DOMAINS_PATH", "../AI-Personas/domains")),
        alias="DOMAINS_PATH"
    )

    # Server settings
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    debug: bool = Field(default=True, alias="DEBUG")

    # Session limits
    max_personas_per_session: int = Field(default=5, alias="MAX_PERSONAS_PER_SESSION")
    max_turns_per_session: int = Field(default=100, alias="MAX_TURNS_PER_SESSION")

    # Token budgets (per provider)
    anthropic_budget_per_session: int = Field(default=100000, alias="ANTHROPIC_BUDGET")
    openai_budget_per_session: int = Field(default=100000, alias="OPENAI_BUDGET")

    # Rate limiting
    rate_limit_requests: int = Field(default=60, alias="RATE_LIMIT_REQUESTS")
    rate_limit_period: int = Field(default=60, alias="RATE_LIMIT_PERIOD")

    # WebSocket settings
    ws_heartbeat_interval: int = Field(default=30, alias="WS_HEARTBEAT_INTERVAL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
