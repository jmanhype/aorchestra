"""Mock tools for testing SubAgent execution."""

from typing import Any
from aorchestra.tools.base import Tool


class EchoTool:
    """A simple tool that echoes back its input.

    Useful for testing tool invocation without side effects.
    """

    name: str = "echo"
    description: str = "Echoes back the input message"

    async def execute(self, message: str) -> str:
        """Echo the input message.

        Args:
            message: The message to echo.

        Returns:
            The same message.
        """
        return f"Echo: {message}"


class CalculatorTool:
    """A basic calculator tool for arithmetic operations."""

    name: str = "calculator"
    description: str = "Performs basic arithmetic: add, subtract, multiply, divide"

    async def execute(self, operation: str, a: float, b: float) -> float:
        """Execute a calculator operation.

        Args:
            operation: One of 'add', 'subtract', 'multiply', 'divide'
            a: First operand
            b: Second operand

        Returns:
            Result of the calculation

        Raises:
            ValueError: If operation is unknown or dividing by zero
        """
        if operation == "add":
            return a + b
        elif operation == "subtract":
            return a - b
        elif operation == "multiply":
            return a * b
        elif operation == "divide":
            if b == 0:
                raise ValueError("Cannot divide by zero")
            return a / b
        else:
            raise ValueError(f"Unknown operation: {operation}")


class ErrorTool:
    """A tool that always raises an error.

    Useful for testing error handling in SubAgent.
    """

    name: str = "error_tool"
    description: str = "Always raises a test error"

    async def execute(self, message: str = "Test error") -> None:
        """Raise a test error.

        Args:
            message: Error message

        Raises:
            RuntimeError: Always raises this error
        """
        raise RuntimeError(f"Intentional test error: {message}")
