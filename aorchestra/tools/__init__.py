"""Tools module for AOrchestra.

Item 001: Tool protocol and mock tools
Item 003: ToolRegistry with metadata and selection
"""

from aorchestra.tools.base import Tool, validate_tool
from aorchestra.tools.registry import ToolRegistry, ToolMetadata, ToolSelectionCriteria

# Existing mock tools (from Item 001)
from aorchestra.tools.mock import EchoTool, ErrorTool

# Built-in tools (Item 003)
from aorchestra.tools.builtins import (
    CalculatorTool,
    CodeExecuteTool,
    WebSearchMockTool,
    FileReadTool,
    get_builtin_tools_metadata,
)

__all__ = [
    "Tool",
    "validate_tool",
    # Registry and metadata (Item 003)
    "ToolRegistry",
    "ToolMetadata",
    "ToolSelectionCriteria",
    # Mock tools (Item 001)
    "EchoTool",
    "ErrorTool",
    # Built-in tools (Item 003)
    "CalculatorTool",
    "CodeExecuteTool",
    "WebSearchMockTool",
    "FileReadTool",
    "get_builtin_tools_metadata",
]
