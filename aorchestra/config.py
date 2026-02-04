"""Configuration management for AOrchestra."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration."""

    zai_api_key: str
    zai_api_base: str
    zai_model: str

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            zai_api_key=os.getenv("ZAI_API_KEY", ""),
            zai_api_base=os.getenv("ZAI_API_BASE", "https://api.z.ai/v1"),
            zai_model=os.getenv("ZAI_MODEL", "glm-4.7"),
        )
