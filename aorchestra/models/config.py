"""Model configuration for LLM backends."""

from pydantic import Field, field_validator
from pydantic.dataclasses import dataclass


@dataclass
class ModelConfig:
    """Configuration for an LLM model.

    Designed to work with OpenAI-compatible APIs (Z.ai, GLM-4.7).
    Simple structure that can be extended by ModelRegistry in item 004.
    """

    name: str = Field(
        ...,
        description="Model name (e.g., 'glm-4.7', 'glm-4-flash')",
    )
    api_base: str = Field(
        ...,
        description="Base URL for the API endpoint",
    )
    api_key: str = Field(
        default="",
        description="API key for authentication (empty for local models)",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 = deterministic, 2.0 = creative)",
    )
    max_tokens: int = Field(
        default=2048,
        gt=0,
        description="Maximum tokens in the response",
    )

    @field_validator("api_base")
    @classmethod
    def api_base_must_be_valid_url(cls, v: str) -> str:
        """Ensure api_base is a valid URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("api_base must start with http:// or https://")
        return v

    def to_openai_kwargs(self) -> dict:
        """Convert to kwargs suitable for OpenAI client initialization."""
        return {
            "api_key": self.api_key or "dummy",  # OpenAI requires non-empty
            "base_url": self.api_base,
        }
