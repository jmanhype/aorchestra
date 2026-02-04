"""Tool interface and base classes.

Tools are callable objects that sub-agents can use to perform actions.
Item 003 will implement ToolRegistry with built-in tools.
This module defines the interface that all tools must follow.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Tool(Protocol):
    """Protocol defining the tool interface.

    A tool must have a name, description, and be callable.
    Uses Protocol (duck typing) for maximum flexibility - any object
    with matching signature qualifies as a tool.

    Compatible with item 003's requirement for tools with
    "name, description, execute" interface.
    """

    name: str
    """Human-readable name of the tool."""

    description: str
    """Description of what the tool does and how to use it."""

    async def execute(**kwargs: Any) -> Any:
        """Execute the tool with given arguments.

        Args:
            **kwargs: Tool-specific arguments.

        Returns:
            Any: The result of tool execution.

        Raises:
            Exception: Tool-specific errors (captured in Observation.error_logs).
        """
        ...


def validate_tool(tool: Any) -> Tool:
    """Validate that an object implements the Tool protocol.

    Args:
        tool: Object to validate.

    Returns:
        Tool: The validated tool.

    Raises:
        TypeError: If the object doesn't implement Tool protocol.
    """
    if not isinstance(tool, Tool):
        raise TypeError(
            f"Object {tool!r} does not implement Tool protocol. "
            f"Tools must have 'name', 'description', and async 'execute' method."
        )
    return tool
