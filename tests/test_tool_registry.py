"""Unit tests for ToolRegistry.

Item 003: Dynamic context curation and tool selection
"""

import pytest
from aorchestra.tools.base import Tool
from aorchestra.tools.registry import (
    ToolRegistry,
    ToolMetadata,
    ToolSelectionCriteria,
)
from aorchestra.tools.builtins import CalculatorTool


class DummyTool:
    """Dummy tool for testing."""

    name: str = "dummy_tool"
    description: str = "A dummy tool for testing"

    async def execute(self, **kwargs) -> str:
        return "dummy result"


class AnotherDummyTool:
    """Another dummy tool for testing."""

    name: str = "another_tool"
    description: str = "Another dummy tool for testing math calculations"

    async def execute(self, **kwargs) -> str:
        return "another result"


class TestToolMetadata:
    """Tests for ToolMetadata Pydantic model."""

    def test_metadata_creation(self):
        """Test creating ToolMetadata with all fields."""
        metadata = ToolMetadata(
            name="test_tool",
            description="A test tool",
            tags=["test", "demo"],
            capabilities=["execute", "run"],
            requires_sandbox=True,
        )

        assert metadata.name == "test_tool"
        assert metadata.description == "A test tool"
        assert metadata.tags == ["test", "demo"]
        assert metadata.capabilities == ["execute", "run"]
        assert metadata.requires_sandbox is True

    def test_metadata_defaults(self):
        """Test ToolMetadata with default values."""
        metadata = ToolMetadata(
            name="test_tool",
            description="A test tool",
        )

        assert metadata.tags == []
        assert metadata.capabilities == []
        assert metadata.requires_sandbox is False

    def test_metadata_serialization(self):
        """Test ToolMetadata can be serialized to/from JSON."""
        metadata = ToolMetadata(
            name="test_tool",
            description="A test tool",
            tags=["test"],
            capabilities=["execute"],
        )

        # Serialize
        json_str = metadata.model_dump_json()
        assert "test_tool" in json_str

        # Deserialize
        restored = ToolMetadata.model_validate_json(json_str)
        assert restored.name == "test_tool"
        assert restored.description == "A test tool"
        assert restored.tags == ["test"]
        assert restored.capabilities == ["execute"]


class TestToolRegistry:
    """Tests for ToolRegistry class."""

    def test_instantiate_empty_registry(self):
        """Test creating an empty registry."""
        registry = ToolRegistry()
        assert len(registry) == 0
        assert registry.list_tools() == []

    def test_register_valid_tool(self):
        """Test registering a valid tool."""
        registry = ToolRegistry()
        tool = DummyTool()
        metadata = ToolMetadata(
            name=tool.name,
            description=tool.description,
            tags=["test"],
        )

        registry.register(tool, metadata)

        assert len(registry) == 1
        assert "dummy_tool" in registry
        assert registry.get("dummy_tool") is tool
        assert registry.get_metadata("dummy_tool") is metadata

    def test_register_duplicate_name(self):
        """Test registering duplicate tool names raises error."""
        registry = ToolRegistry()
        tool1 = DummyTool()
        tool2 = DummyTool()
        metadata1 = ToolMetadata(name="dummy_tool", description="Tool 1")
        metadata2 = ToolMetadata(name="dummy_tool", description="Tool 2")

        registry.register(tool1, metadata1)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(tool2, metadata2)

    def test_register_name_mismatch(self):
        """Test registering with name mismatch raises error."""
        registry = ToolRegistry()
        tool = DummyTool()
        metadata = ToolMetadata(
            name="wrong_name",  # Doesn't match tool.name
            description="A tool",
        )

        with pytest.raises(ValueError, match="name mismatch"):
            registry.register(tool, metadata)

    def test_register_invalid_tool(self):
        """Test registering a tool that doesn't implement Tool protocol."""
        registry = ToolRegistry()
        not_a_tool = "not a tool"
        metadata = ToolMetadata(
            name="not_a_tool",
            description="Not a tool",
        )

        with pytest.raises(TypeError):
            registry.register(not_a_tool, metadata)

    def test_unregister_existing_tool(self):
        """Test unregistering an existing tool."""
        registry = ToolRegistry()
        tool = DummyTool()
        metadata = ToolMetadata(
            name=tool.name,
            description=tool.description,
        )

        registry.register(tool, metadata)
        assert "dummy_tool" in registry

        registry.unregister("dummy_tool")
        assert "dummy_tool" not in registry
        assert len(registry) == 0

    def test_unregister_nonexistent_tool(self):
        """Test unregistering non-existent tool raises KeyError."""
        registry = ToolRegistry()

        with pytest.raises(KeyError, match="not registered"):
            registry.unregister("nonexistent")

    def test_get_existing_tool(self):
        """Test getting an existing tool."""
        registry = ToolRegistry()
        tool = DummyTool()
        metadata = ToolMetadata(
            name=tool.name,
            description=tool.description,
        )

        registry.register(tool, metadata)
        retrieved = registry.get("dummy_tool")

        assert retrieved is tool

    def test_get_nonexistent_tool(self):
        """Test getting a non-existent tool returns None."""
        registry = ToolRegistry()
        retrieved = registry.get("nonexistent")

        assert retrieved is None

    def test_get_all_tools(self):
        """Test getting all tools."""
        registry = ToolRegistry()
        tool1 = DummyTool()
        tool2 = AnotherDummyTool()

        metadata1 = ToolMetadata(
            name=tool1.name,
            description=tool1.description,
        )
        metadata2 = ToolMetadata(
            name=tool2.name,
            description=tool2.description,
        )

        registry.register(tool1, metadata1)
        registry.register(tool2, metadata2)

        tools = registry.get_all()
        assert len(tools) == 2
        assert tool1 in tools
        assert tool2 in tools

    def test_list_tools(self):
        """Test listing tool names."""
        registry = ToolRegistry()
        tool1 = DummyTool()
        tool2 = AnotherDummyTool()

        metadata1 = ToolMetadata(
            name=tool1.name,
            description=tool1.description,
        )
        metadata2 = ToolMetadata(
            name=tool2.name,
            description=tool2.description,
        )

        registry.register(tool1, metadata1)
        registry.register(tool2, metadata2)

        names = registry.list_tools()
        assert len(names) == 2
        assert "dummy_tool" in names
        assert "another_tool" in names

    def test_contains_operator(self):
        """Test the __contains__ operator."""
        registry = ToolRegistry()
        tool = DummyTool()
        metadata = ToolMetadata(
            name=tool.name,
            description=tool.description,
        )

        assert "dummy_tool" not in registry

        registry.register(tool, metadata)
        assert "dummy_tool" in registry

    def test_len_operator(self):
        """Test the __len__ operator."""
        registry = ToolRegistry()
        tool = DummyTool()
        metadata = ToolMetadata(
            name=tool.name,
            description=tool.description,
        )

        assert len(registry) == 0

        registry.register(tool, metadata)
        assert len(registry) == 1


class TestToolRegistrySelectTools:
    """Tests for ToolRegistry.select_tools() method."""

    def test_select_by_tool_names(self):
        """Test selecting tools by specific names."""
        registry = ToolRegistry()
        tool1 = DummyTool()
        tool2 = AnotherDummyTool()

        metadata1 = ToolMetadata(
            name=tool1.name,
            description=tool1.description,
        )
        metadata2 = ToolMetadata(
            name=tool2.name,
            description=tool2.description,
        )

        registry.register(tool1, metadata1)
        registry.register(tool2, metadata2)

        # Select by name
        criteria = ToolSelectionCriteria(
            tool_names=["dummy_tool"],
        )
        selected = registry.select_tools(criteria)

        assert len(selected) == 1
        assert selected[0] is tool1

    def test_select_by_tool_names_ignores_other_criteria(self):
        """Test that tool_names takes precedence over other criteria."""
        registry = ToolRegistry()
        tool1 = DummyTool()
        tool2 = AnotherDummyTool()

        metadata1 = ToolMetadata(
            name=tool1.name,
            description=tool1.description,
            tags=["test"],
        )
        metadata2 = ToolMetadata(
            name=tool2.name,
            description=tool2.description,
            tags=["math"],
        )

        registry.register(tool1, metadata1)
        registry.register(tool2, metadata2)

        # Select by name but also filter by different tag
        criteria = ToolSelectionCriteria(
            tool_names=["another_tool"],
            tags=["test"],  # This should be ignored
        )
        selected = registry.select_tools(criteria)

        assert len(selected) == 1
        assert selected[0] is tool2

    def test_select_by_tool_names_nonexistent_skipped(self):
        """Test that nonexistent tool names are skipped."""
        registry = ToolRegistry()
        tool1 = DummyTool()

        metadata1 = ToolMetadata(
            name=tool1.name,
            description=tool1.description,
        )

        registry.register(tool1, metadata1)

        # Select with one nonexistent name
        criteria = ToolSelectionCriteria(
            tool_names=["dummy_tool", "nonexistent"],
        )
        selected = registry.select_tools(criteria)

        assert len(selected) == 1
        assert selected[0] is tool1

    def test_select_by_tags(self):
        """Test selecting tools by tags."""
        registry = ToolRegistry()
        tool1 = DummyTool()
        tool2 = AnotherDummyTool()

        metadata1 = ToolMetadata(
            name=tool1.name,
            description=tool1.description,
            tags=["test", "demo"],
        )
        metadata2 = ToolMetadata(
            name=tool2.name,
            description=tool2.description,
            tags=["math", "calculation"],
        )

        registry.register(tool1, metadata1)
        registry.register(tool2, metadata2)

        # Select by tag
        criteria = ToolSelectionCriteria(
            tags=["math"],
        )
        selected = registry.select_tools(criteria)

        assert len(selected) == 1
        assert selected[0] is tool2

    def test_select_by_tags_or_logic(self):
        """Test tag matching uses OR logic."""
        registry = ToolRegistry()
        tool1 = DummyTool()
        tool2 = AnotherDummyTool()

        metadata1 = ToolMetadata(
            name=tool1.name,
            description=tool1.description,
            tags=["test"],
        )
        metadata2 = ToolMetadata(
            name=tool2.name,
            description=tool2.description,
            tags=["math"],
        )

        registry.register(tool1, metadata1)
        registry.register(tool2, metadata2)

        # Select by multiple tags (should match both)
        criteria = ToolSelectionCriteria(
            tags=["test", "math"],
        )
        selected = registry.select_tools(criteria)

        assert len(selected) == 2
        assert tool1 in selected
        assert tool2 in selected

    def test_select_by_capabilities(self):
        """Test selecting tools by capabilities."""
        registry = ToolRegistry()
        calc = CalculatorTool()

        metadata = ToolMetadata(
            name=calc.name,
            description=calc.description,
            tags=["math"],
            capabilities=["add", "subtract", "multiply", "divide"],
        )

        registry.register(calc, metadata)

        # Select by capability
        criteria = ToolSelectionCriteria(
            capabilities=["add"],
        )
        selected = registry.select_tools(criteria)

        assert len(selected) == 1
        assert selected[0] is calc

    def test_select_by_keywords(self):
        """Test selecting tools by keywords in description."""
        registry = ToolRegistry()
        tool1 = DummyTool()
        tool2 = AnotherDummyTool()

        metadata1 = ToolMetadata(
            name=tool1.name,
            description=tool1.description,  # "A dummy tool for testing"
            tags=[],
        )
        metadata2 = ToolMetadata(
            name=tool2.name,
            description=tool2.description,  # "Another dummy tool for testing math calculations"
            tags=[],
        )

        registry.register(tool1, metadata1)
        registry.register(tool2, metadata2)

        # Select by keyword "math"
        criteria = ToolSelectionCriteria(
            keywords=["math"],
        )
        selected = registry.select_tools(criteria)

        assert len(selected) == 1
        assert selected[0] is tool2

    def test_select_by_keywords_case_insensitive(self):
        """Test keyword matching is case-insensitive."""
        registry = ToolRegistry()
        tool = CalculatorTool()

        metadata = ToolMetadata(
            name=tool.name,
            description="Performs arithmetic operations: Add, Subtract, Multiply, Divide",
            tags=["math"],
        )

        registry.register(tool, metadata)

        # Select with uppercase keyword
        criteria = ToolSelectionCriteria(
            keywords=["ARITHMETIC"],
        )
        selected = registry.select_tools(criteria)

        assert len(selected) == 1
        assert selected[0] is tool

    def test_select_combined_filters(self):
        """Test combining multiple filters (AND logic between groups)."""
        registry = ToolRegistry()
        tool1 = DummyTool()
        tool2 = AnotherDummyTool()
        tool3 = CalculatorTool()

        metadata1 = ToolMetadata(
            name=tool1.name,
            description=tool1.description,
            tags=["test"],
            capabilities=["execute"],
        )
        metadata2 = ToolMetadata(
            name=tool2.name,
            description="Another tool for math calculations",
            tags=["math"],
            capabilities=["calculate"],
        )
        metadata3 = ToolMetadata(
            name=tool3.name,
            description="Performs arithmetic operations",
            tags=["math"],
            capabilities=["add", "subtract", "multiply", "divide"],
        )

        registry.register(tool1, metadata1)
        registry.register(tool2, metadata2)
        registry.register(tool3, metadata3)

        # Select tools with tag "math" AND capability "calculate"
        criteria = ToolSelectionCriteria(
            tags=["math"],
            capabilities=["calculate"],
        )
        selected = registry.select_tools(criteria)

        # Only tool2 matches both filters
        assert len(selected) == 1
        assert selected[0] is tool2

    def test_select_no_matches(self):
        """Test selecting when nothing matches."""
        registry = ToolRegistry()
        tool = DummyTool()

        metadata = ToolMetadata(
            name=tool.name,
            description=tool.description,
            tags=["test"],
        )

        registry.register(tool, metadata)

        # Select with non-matching criteria
        criteria = ToolSelectionCriteria(
            tags=["nonexistent"],
        )
        selected = registry.select_tools(criteria)

        assert len(selected) == 0

    def test_select_respects_max_tools(self):
        """Test that max_tools limits the number of results."""
        registry = ToolRegistry()
        tool1 = DummyTool()
        tool2 = AnotherDummyTool()
        tool3 = CalculatorTool()

        metadata1 = ToolMetadata(
            name=tool1.name,
            description=tool1.description,
            tags=["test"],
        )
        metadata2 = ToolMetadata(
            name=tool2.name,
            description="Math tool for calculations",
            tags=["math"],
        )
        metadata3 = ToolMetadata(
            name=tool3.name,
            description="Arithmetic operations",
            tags=["math"],
        )

        registry.register(tool1, metadata1)
        registry.register(tool2, metadata2)
        registry.register(tool3, metadata3)

        # Select with max_tools=2
        criteria = ToolSelectionCriteria(
            tags=["math"],
            max_tools=2,
        )
        selected = registry.select_tools(criteria)

        # Should only return 2 tools even though 3 match
        assert len(selected) == 2
        assert tool1 not in selected
        assert tool2 in selected
        assert tool3 in selected

    def test_select_empty_criteria(self):
        """Test selecting with empty criteria (returns all tools)."""
        registry = ToolRegistry()
        tool1 = DummyTool()
        tool2 = AnotherDummyTool()

        metadata1 = ToolMetadata(
            name=tool1.name,
            description=tool1.description,
        )
        metadata2 = ToolMetadata(
            name=tool2.name,
            description=tool2.description,
        )

        registry.register(tool1, metadata1)
        registry.register(tool2, metadata2)

        # Select with empty criteria
        criteria = ToolSelectionCriteria()
        selected = registry.select_tools(criteria)

        assert len(selected) == 2
        assert tool1 in selected
        assert tool2 in selected

    def test_select_empty_registry(self):
        """Test selecting from empty registry."""
        registry = ToolRegistry()

        criteria = ToolSelectionCriteria(
            tags=["test"],
        )
        selected = registry.select_tools(criteria)

        assert len(selected) == 0
