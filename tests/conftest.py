"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI response for testing."""
    from unittest.mock import MagicMock

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test response"
    mock_response.choices[0].message.tool_calls = None
    return mock_response
