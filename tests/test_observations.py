"""Tests for Observation models."""

import pytest
from aorchestra.core.observations import Observation


class TestObservation:
    """Test Observation model validation and behavior."""

    def test_create_observation_with_summary_only(self):
        """Observation can be created with just a result_summary."""
        obs = Observation(result_summary="Task completed successfully")
        assert obs.result_summary == "Task completed successfully"
        assert obs.artifacts == {}
        assert obs.error_logs == []

    def test_observation_with_artifacts(self):
        """Observation can store structured artifacts."""
        obs = Observation(
            result_summary="Generated code",
            artifacts={"code": "print('hello')", "language": "python"},
        )
        assert obs.artifacts["code"] == "print('hello')"
        assert obs.artifacts["language"] == "python"

    def test_observation_with_errors(self):
        """Observation can capture error logs."""
        obs = Observation(
            result_summary="Partial completion",
            error_logs=["Warning: timeout", "Error: API rate limit"],
        )
        assert len(obs.error_logs) == 2
        assert "timeout" in obs.error_logs[0]

    def test_add_error_method(self):
        """Observation.add_error() appends to error_logs."""
        obs = Observation(result_summary="Test")
        obs.add_error("New error")
        assert len(obs.error_logs) == 1
        assert obs.error_logs[0] == "New error"

    def test_add_artifact_method(self):
        """Observation.add_artifact() adds to artifacts dict."""
        obs = Observation(result_summary="Test")
        obs.add_artifact("output", "result")
        assert obs.artifacts["output"] == "result"

    def test_observation_serialization(self):
        """Observation can serialize to/from JSON."""
        obs = Observation(
            result_summary="Test",
            artifacts={"key": "value"},
            error_logs=["error1"],
        )
        json_str = obs.model_dump_json()
        restored = Observation.model_validate_json(json_str)
        assert restored.result_summary == obs.result_summary
        assert restored.artifacts == obs.artifacts
        assert restored.error_logs == obs.error_logs
