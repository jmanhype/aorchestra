"""Tests for tool protocol and mock tools."""

import pytest
from aorchestra.tools.base import Tool, validate_tool
from aorchestra.tools.mock import EchoTool, CalculatorTool, ErrorTool


class TestToolProtocol:
    """Test Tool protocol validation."""

    def test_valid_tool_passes_validation(self):
        """A valid tool implements the Tool protocol."""
        echo = EchoTool()
        assert validate_tool(echo) == echo

    def test_invalid_object_raises_type_error(self):
        """An object without Tool interface raises TypeError."""
        invalid = {"name": "bad"}  # Dict doesn't implement Tool
        with pytest.raises(TypeError) as exc:
            validate_tool(invalid)
        assert "does not implement Tool protocol" in str(exc.value)

    def test_tool_with_missing_name_raises_error(self):
        """Tool without 'name' attribute fails validation."""
        class BadTool:
            description = "Missing name"
            async def execute(self):
                pass

        with pytest.raises(TypeError):
            validate_tool(BadTool())


class TestEchoTool:
    """Test EchoTool functionality."""

    @pytest.mark.asyncio
    async def test_echo_tool_returns_message(self):
        """EchoTool echoes back the input message."""
        tool = EchoTool()
        result = await tool.execute(message="Hello, world!")
        assert result == "Echo: Hello, world!"

    def test_echo_tool_has_name_and_description(self):
        """EchoTool has required name and description."""
        tool = EchoTool()
        assert tool.name == "echo"
        assert tool.description != ""


class TestCalculatorTool:
    """Test CalculatorTool functionality."""

    @pytest.mark.asyncio
    async def test_calculator_add(self):
        """Calculator can add two numbers."""
        tool = CalculatorTool()
        result = await tool.execute(operation="add", a=5, b=3)
        assert result == 8

    @pytest.mark.asyncio
    async def test_calculator_multiply(self):
        """Calculator can multiply two numbers."""
        tool = CalculatorTool()
        result = await tool.execute(operation="multiply", a=4, b=7)
        assert result == 28

    @pytest.mark.asyncio
    async def test_calculator_divide(self):
        """Calculator can divide two numbers."""
        tool = CalculatorTool()
        result = await tool.execute(operation="divide", a=10, b=2)
        assert result == 5

    @pytest.mark.asyncio
    async def test_calculator_divide_by_zero_raises_error(self):
        """Calculator raises error for division by zero."""
        tool = CalculatorTool()
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            await tool.execute(operation="divide", a=5, b=0)

    @pytest.mark.asyncio
    async def test_calculator_unknown_operation_raises_error(self):
        """Calculator raises error for unknown operations."""
        tool = CalculatorTool()
        with pytest.raises(ValueError, match="Unknown operation"):
            await tool.execute(operation="modulo", a=10, b=3)


class TestErrorTool:
    """Test ErrorTool functionality."""

    @pytest.mark.asyncio
    async def test_error_tool_always_raises(self):
        """ErrorTool always raises a RuntimeError."""
        tool = ErrorTool()
        with pytest.raises(RuntimeError, match="Intentional test error"):
            await tool.execute(message="Test")
