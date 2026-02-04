"""Tool registry for managing available tools with metadata.

Item 003: Dynamic context curation and tool selection
"""

from typing import Any
from pydantic import BaseModel, Field

from aorchestra.tools.base import Tool, validate_tool


class ToolMetadata(BaseModel):
    """Metadata for a tool in the registry.

    Enables intelligent tool selection based on tags, capabilities,
    and descriptions.
    """

    name: str = Field(..., description="Tool name (must match tool.name)")
    description: str = Field(..., description="Tool description (must match tool.description)")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization (e.g., 'math', 'code')")
    capabilities: list[str] = Field(default_factory=list, description="Specific capabilities (e.g., 'arithmetic', 'file_io')")
    requires_sandbox: bool = Field(default=False, description="Whether tool requires sandboxed execution")


class ToolSelectionCriteria(BaseModel):
    """Criteria for selecting tools from the registry.

    Used by Orchestrator to find relevant tools for subtasks.
    """

    tags: list[str] = Field(default_factory=list, description="Required tags (OR logic)")
    capabilities: list[str] = Field(default_factory=list, description="Required capabilities (OR logic)")
    keywords: list[str] = Field(default_factory=list, description="Keywords to match in tool descriptions")
    tool_names: list[str] = Field(default_factory=list, description="Specific tool names to include")
    max_tools: int = Field(default=10, description="Maximum number of tools to return")


class ToolRegistry:
    """Central registry for managing available tools.

    Provides methods for registering, retrieving, and selecting tools
    based on metadata and selection criteria.
    """

    def __init__(self):
        """Initialize an empty registry."""
        self._tools: dict[str, Tool] = {}
        self._metadata: dict[str, ToolMetadata] = {}

    def register(self, tool: Tool, metadata: ToolMetadata) -> None:
        """Register a tool with metadata.

        Args:
            tool: Tool object implementing Tool protocol.
            metadata: Metadata for the tool.

        Raises:
            TypeError: If tool doesn't implement Tool protocol.
            ValueError: If tool name already registered or name mismatch.
        """
        # Validate tool implements protocol
        validated_tool = validate_tool(tool)

        # Validate name consistency
        if validated_tool.name != metadata.name:
            raise ValueError(
                f"Tool name mismatch: tool.name='{validated_tool.name}' != metadata.name='{metadata.name}'"
            )

        # Check for duplicate
        if validated_tool.name in self._tools:
            raise ValueError(f"Tool '{validated_tool.name}' already registered")

        # Store tool and metadata
        self._tools[validated_tool.name] = validated_tool
        self._metadata[validated_tool.name] = metadata

    def unregister(self, name: str) -> None:
        """Unregister a tool by name.

        Args:
            name: Tool name to unregister.

        Raises:
            KeyError: If tool not found.
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not registered")
        del self._tools[name]
        del self._metadata[name]

    def get(self, name: str) -> Tool | None:
        """Get a tool by name.

        Args:
            name: Tool name.

        Returns:
            Tool object or None if not found.
        """
        return self._tools.get(name)

    def get_metadata(self, name: str) -> ToolMetadata | None:
        """Get tool metadata by name.

        Args:
            name: Tool name.

        Returns:
            ToolMetadata or None if not found.
        """
        return self._metadata.get(name)

    def get_all(self) -> list[Tool]:
        """Get all registered tools.

        Returns:
            List of all tool objects.
        """
        return list(self._tools.values())

    def select_tools(self, criteria: ToolSelectionCriteria) -> list[Tool]:
        """Select tools matching the given criteria.

        Selection logic:
        1. If tool_names specified, return those tools only
        2. Otherwise, filter by tags, capabilities, keywords
        3. Return up to max_tools matches

        Args:
            criteria: Selection criteria.

        Returns:
            List of matching tools.
        """
        # If specific tool names requested, return those
        if criteria.tool_names:
            tools = []
            for name in criteria.tool_names:
                tool = self.get(name)
                if tool:
                    tools.append(tool)
            return tools

        # Otherwise, apply filters
        selected = []
        for tool in self.get_all():
            metadata = self._metadata[tool.name]

            if self._matches_criteria(metadata, criteria):
                selected.append(tool)

        # Limit to max_tools
        return selected[:criteria.max_tools]

    def _matches_criteria(self, metadata: ToolMetadata, criteria: ToolSelectionCriteria) -> bool:
        """Check if tool metadata matches criteria.

        Args:
            metadata: Tool metadata.
            criteria: Selection criteria.

        Returns:
            True if tool matches criteria.
        """
        # Tag matching (OR logic: match any tag)
        if criteria.tags:
            if not any(tag in metadata.tags for tag in criteria.tags):
                return False

        # Capability matching (OR logic: match any capability)
        if criteria.capabilities:
            if not any(cap in metadata.capabilities for cap in criteria.capabilities):
                return False

        # Keyword matching in description (case-insensitive)
        if criteria.keywords:
            desc_lower = metadata.description.lower()
            if not any(kw.lower() in desc_lower for kw in criteria.keywords):
                return False

        return True

    def list_tools(self) -> list[str]:
        """List all registered tool names.

        Returns:
            List of tool names.
        """
        return list(self._tools.keys())

    def __len__(self) -> int:
        """Return number of registered tools."""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Check if tool is registered."""
        return name in self._tools
