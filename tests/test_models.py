"""Tests for ModelConfig."""

import pytest
from pydantic import ValidationError
from aorchestra.models.config import ModelConfig


class TestModelConfig:
    """Test ModelConfig validation."""

    def test_create_model_config_minimal(self):
        """ModelConfig with required fields only."""
        config = ModelConfig(
            name="glm-4.7",
            api_base="https://api.z.ai/v1",
        )
        assert config.name == "glm-4.7"
        assert config.api_base == "https://api.z.ai/v1"
        assert config.temperature == 0.7  # default
        assert config.max_tokens == 2048  # default

    def test_create_model_config_with_all_fields(self):
        """ModelConfig with all fields specified."""
        config = ModelConfig(
            name="glm-4-flash",
            api_base="https://api.z.ai/v1",
            api_key="sk-test",
            temperature=0.5,
            max_tokens=1024,
        )
        assert config.temperature == 0.5
        assert config.max_tokens == 1024

    def test_invalid_api_base_raises_error(self):
        """api_base must start with http:// or https://."""
        with pytest.raises(ValidationError):
            ModelConfig(name="glm-4.7", api_base="invalid-url")

    def test_temperature_out_of_range_raises_error(self):
        """temperature must be between 0.0 and 2.0."""
        with pytest.raises(ValidationError):
            ModelConfig(name="glm-4.7", api_base="https://api.z.ai/v1", temperature=3.0)

    def test_max_tokens_must_be_positive(self):
        """max_tokens must be > 0."""
        with pytest.raises(ValidationError):
            ModelConfig(name="glm-4.7", api_base="https://api.z.ai/v1", max_tokens=0)

    def test_to_openai_kwargs(self):
        """to_openai_kwargs() returns correct dictionary."""
        config = ModelConfig(
            name="glm-4.7",
            api_base="https://api.z.ai/v1",
            api_key="sk-test",
        )
        kwargs = config.to_openai_kwargs()
        assert kwargs["base_url"] == "https://api.z.ai/v1"
        assert kwargs["api_key"] == "sk-test"
