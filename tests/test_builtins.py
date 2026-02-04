"""Unit tests for built-in tools.

Item 003: Dynamic context curation and tool selection
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from aorchestra.tools.base import validate_tool
from aorchestra.tools.builtins import (
    CalculatorTool,
    CodeExecuteTool,
    WebSearchMockTool,
    FileReadTool,
    get_builtin_tools_metadata,
)


class TestCalculatorTool:
    """Tests for CalculatorTool."""

    @pytest.mark.asyncio
    async def test_add_operation(self):
        """Test addition operation."""
        tool = CalculatorTool()
        result = await tool.execute(operation="add", a=5.0, b=3.0)
        assert result == 8.0

    @pytest.mark.asyncio
    async def test_subtract_operation(self):
        """Test subtraction operation."""
        tool = CalculatorTool()
        result = await tool.execute(operation="subtract", a=10.0, b=4.0)
        assert result == 6.0

    @pytest.mark.asyncio
    async def test_multiply_operation(self):
        """Test multiplication operation."""
        tool = CalculatorTool()
        result = await tool.execute(operation="multiply", a=6.0, b=7.0)
        assert result == 42.0

    @pytest.mark.asyncio
    async def test_divide_operation(self):
        """Test division operation."""
        tool = CalculatorTool()
        result = await tool.execute(operation="divide", a=20.0, b=4.0)
        assert result == 5.0

    @pytest.mark.asyncio
    async def test_divide_by_zero_raises_error(self):
        """Test division by zero raises ValueError."""
        tool = CalculatorTool()
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            await tool.execute(operation="divide", a=10.0, b=0.0)

    @pytest.mark.asyncio
    async def test_unknown_operation_raises_error(self):
        """Test unknown operation raises ValueError."""
        tool = CalculatorTool()
        with pytest.raises(ValueError, match="Unknown operation"):
            await tool.execute(operation="modulo", a=10.0, b=3.0)

    def test_tool_protocol_compliance(self):
        """Test that CalculatorTool implements Tool protocol."""
        tool = CalculatorTool()
        assert tool.name == "calculator"
        assert tool.description == "Performs basic arithmetic operations: add, subtract, multiply, divide"
        assert hasattr(tool, "execute")

    def test_passes_validate_tool(self):
        """Test that CalculatorTool passes validate_tool()."""
        tool = CalculatorTool()
        validated = validate_tool(tool)
        assert validated is tool


class TestCodeExecuteTool:
    """Tests for CodeExecuteTool."""

    @pytest.mark.asyncio
    async def test_simple_print(self):
        """Test simple print statement."""
        tool = CodeExecuteTool()
        result = await tool.execute('print("Hello, World!")')

        assert result["success"] is True
        assert "Hello, World!" in result["stdout"]
        assert result["stderr"] == ""
        assert result["returncode"] == 0

    @pytest.mark.asyncio
    async def test_arithmetic_operation(self):
        """Test arithmetic calculation."""
        tool = CodeExecuteTool()
        result = await tool.execute('result = 2 + 2\nprint(result)')

        assert result["success"] is True
        assert "4" in result["stdout"]

    @pytest.mark.asyncio
    async def test_syntax_error(self):
        """Test syntax error handling."""
        tool = CodeExecuteTool()
        result = await tool.execute('print("unclosed string)')

        assert result["success"] is False
        assert result["returncode"] != 0
        assert len(result["stderr"]) > 0

    @pytest.mark.asyncio
    async def test_stdout_and_stderr_capture(self):
        """Test that both stdout and stderr are captured."""
        tool = CodeExecuteTool()
        result = await tool.execute(
            'import sys\nprint("stdout message")\nprint("stderr message", file=sys.stderr)'
        )

        assert result["success"] is True
        assert "stdout message" in result["stdout"]
        assert "stderr message" in result["stderr"]

    @pytest.mark.asyncio
    async def test_timeout_on_infinite_loop(self):
        """Test that infinite loops timeout."""
        tool = CodeExecuteTool(timeout=1)  # 1 second timeout
        result = await tool.execute('while True:\n    pass')

        # Should handle timeout gracefully
        assert result["success"] is False
        # Either returncode is -1 (process killed) or there's an error message
        assert result["returncode"] != 0 or "timed out" in result["stderr"].lower()

    @pytest.mark.asyncio
    async def test_custom_timeout(self):
        """Test custom timeout parameter."""
        tool = CodeExecuteTool(timeout=5)
        result = await tool.execute('import time\ntime.sleep(0.1)\nprint("Done")')

        assert result["success"] is True
        assert "Done" in result["stdout"]

    def test_tool_protocol_compliance(self):
        """Test that CodeExecuteTool implements Tool protocol."""
        tool = CodeExecuteTool()
        assert tool.name == "code_execute"
        assert "Executes Python code" in tool.description
        assert hasattr(tool, "execute")

    def test_passes_validate_tool(self):
        """Test that CodeExecuteTool passes validate_tool()."""
        tool = CodeExecuteTool()
        validated = validate_tool(tool)
        assert validated is tool


class TestWebSearchMockTool:
    """Tests for WebSearchMockTool."""

    @pytest.mark.asyncio
    async def test_python_search(self):
        """Test searching for Python."""
        tool = WebSearchMockTool()
        result = await tool.execute(query="python programming", max_results=5)

        assert result["query"] == "python programming"
        assert result["total"] >= 1
        assert len(result["results"]) > 0
        # Results should have title, url, snippet
        for item in result["results"]:
            assert "title" in item
            assert "url" in item
            assert "snippet" in item

    @pytest.mark.asyncio
    async def test_async_search(self):
        """Test searching for async."""
        tool = WebSearchMockTool()
        result = await tool.execute(query="asyncio", max_results=5)

        assert result["total"] >= 1
        assert any("asyncio" in item.get("url", "").lower() for item in result["results"])

    @pytest.mark.asyncio
    async def test_no_results_for_unknown_query(self):
        """Test search with no matching keywords."""
        tool = WebSearchMockTool()
        result = await tool.execute(query="xyznonexistentkeyword123", max_results=5)

        assert result["total"] == 0
        assert len(result["results"]) == 0

    @pytest.mark.asyncio
    async def test_max_results_limit(self):
        """Test max_results parameter."""
        tool = WebSearchMockTool()
        result = await tool.execute(query="python", max_results=2)

        assert len(result["results"]) <= 2

    @pytest.mark.asyncio
    async def test_case_insensitive_search(self):
        """Test search is case-insensitive."""
        tool = WebSearchMockTool()

        # Search with uppercase
        result1 = await tool.execute(query="PYTHON")
        # Search with lowercase
        result2 = await tool.execute(query="python")

        assert result1["total"] == result2["total"]

    @pytest.mark.asyncio
    async def test_duplicate_removal(self):
        """Test that duplicate results are removed."""
        # Custom index with duplicate URLs
        custom_index = {
            "python": [
                {"title": "Python", "url": "https://python.org", "snippet": "Official site"},
                {"title": "Python Again", "url": "https://python.org", "snippet": "Same site"},
            ],
        }

        tool = WebSearchMockTool(search_index=custom_index)
        result = await tool.execute(query="python")

        # Should only have one result (duplicates removed)
        assert len(result["results"]) == 1

    @pytest.mark.asyncio
    async def test_custom_search_index(self):
        """Test custom search index."""
        custom_index = {
            "test": [
                {"title": "Test Result", "url": "https://example.com", "snippet": "A test"},
            ],
        }

        tool = WebSearchMockTool(search_index=custom_index)
        result = await tool.execute(query="test query")

        assert result["total"] >= 1
        assert any("Test Result" in item.get("title", "") for item in result["results"])

    def test_tool_protocol_compliance(self):
        """Test that WebSearchMockTool implements Tool protocol."""
        tool = WebSearchMockTool()
        assert tool.name == "web_search_mock"
        assert "mock web search" in tool.description.lower()
        assert hasattr(tool, "execute")

    def test_passes_validate_tool(self):
        """Test that WebSearchMockTool passes validate_tool()."""
        tool = WebSearchMockTool()
        validated = validate_tool(tool)
        assert validated is tool


class TestFileReadTool:
    """Tests for FileReadTool."""

    @pytest.mark.asyncio
    async def test_read_existing_file(self):
        """Test reading an existing file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Hello, World!\nThis is a test file.")
            temp_path = f.name

        try:
            # Get temp directory for allowed_dirs
            temp_dir = str(Path(temp_path).parent)
            tool = FileReadTool(allowed_dirs=[temp_dir])
            result = await tool.execute(path=temp_path)

            assert result["success"] is True
            assert "Hello, World!" in result["content"]
            assert "This is a test file." in result["content"]
            assert result["path"] == str(Path(temp_path).resolve())
            assert result["size"] > 0
            assert result["error"] is None
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self):
        """Test reading a non-existent file."""
        tool = FileReadTool(allowed_dirs=[str(Path.cwd())])

        with pytest.raises(FileNotFoundError, match="File not found"):
            await tool.execute(path="nonexistent_file_12345.txt")

    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self):
        """Test that directory traversal attacks are prevented."""
        tool = FileReadTool(allowed_dirs=[str(Path.cwd())])

        # Try to read file outside allowed directory
        with pytest.raises(ValueError, match="outside allowed directories"):
            await tool.execute(path="../../../etc/passwd")

    @pytest.mark.asyncio
    async def test_custom_allowed_dirs(self):
        """Test custom allowed directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file in the temp directory
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Content in allowed dir")

            # Create tool with custom allowed directory
            tool = FileReadTool(allowed_dirs=[temp_dir])
            result = await tool.execute(path=str(test_file))

            assert result["success"] is True
            assert "Content in allowed dir" in result["content"]

    @pytest.mark.asyncio
    async def test_encoding_handling(self):
        """Test different file encodings."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("Hello, 世界!")
            temp_path = f.name

        try:
            # Get temp directory for allowed_dirs
            temp_dir = str(Path(temp_path).parent)
            tool = FileReadTool(allowed_dirs=[temp_dir])

            # Read with UTF-8 (default)
            result_utf8 = await tool.execute(path=temp_path, encoding="utf-8")
            assert result_utf8["success"] is True
            assert "世界" in result_utf8["content"]

            # Read with wrong encoding should raise error
            with pytest.raises(ValueError, match="Failed to decode"):
                await tool.execute(path=temp_path, encoding="ascii")
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_absolute_path_resolution(self):
        """Test that paths are resolved to absolute paths."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Test content")
            temp_dir = Path(f.name).parent
            filename = Path(f.name).name

        try:
            tool = FileReadTool(allowed_dirs=[temp_dir])

            # Read with just filename (should resolve relative to CWD first)
            # This test verifies the path resolution logic
            result = await tool.execute(path=str(temp_dir / filename))

            assert result["success"] is True
            assert Path(result["path"]).is_absolute()
        finally:
            Path(temp_dir / filename).unlink()

    def test_tool_protocol_compliance(self):
        """Test that FileReadTool implements Tool protocol."""
        tool = FileReadTool()
        assert tool.name == "file_read"
        assert "reads file" in tool.description.lower()
        assert hasattr(tool, "execute")

    def test_passes_validate_tool(self):
        """Test that FileReadTool passes validate_tool()."""
        tool = FileReadTool()
        validated = validate_tool(tool)
        assert validated is tool


class TestGetBuiltinToolsMetadata:
    """Tests for get_builtin_tools_metadata() helper."""

    def test_returns_four_tools(self):
        """Test that 4 built-in tools are returned."""
        metadata_list = get_builtin_tools_metadata()

        assert len(metadata_list) == 4

    def test_metadata_name_matches_tool_name(self):
        """Test that metadata.name matches tool.name for all tools."""
        metadata_list = get_builtin_tools_metadata()

        for metadata, tool_class in metadata_list:
            tool = tool_class()
            assert metadata.name == tool.name
            assert metadata.description == tool.description

    def test_tools_have_tags(self):
        """Test that all tools have tags."""
        metadata_list = get_builtin_tools_metadata()

        for metadata, _ in metadata_list:
            assert len(metadata.tags) > 0

    def test_tools_have_capabilities(self):
        """Test that all tools have capabilities."""
        metadata_list = get_builtin_tools_metadata()

        for metadata, _ in metadata_list:
            assert len(metadata.capabilities) > 0

    def test_all_tools_pass_validate_tool(self):
        """Test that all built-in tools pass validate_tool()."""
        metadata_list = get_builtin_tools_metadata()

        for _, tool_class in metadata_list:
            tool = tool_class()
            validated = validate_tool(tool)
            assert validated is tool

    def test_includes_calculator(self):
        """Test that CalculatorTool is included."""
        metadata_list = get_builtin_tools_metadata()

        metadata_dict = {meta.name: (meta, cls) for meta, cls in metadata_list}
        assert "calculator" in metadata_dict

    def test_includes_code_execute(self):
        """Test that CodeExecuteTool is included."""
        metadata_list = get_builtin_tools_metadata()

        metadata_dict = {meta.name: (meta, cls) for meta, cls in metadata_list}
        assert "code_execute" in metadata_dict

    def test_includes_web_search_mock(self):
        """Test that WebSearchMockTool is included."""
        metadata_list = get_builtin_tools_metadata()

        metadata_dict = {meta.name: (meta, cls) for meta, cls in metadata_list}
        assert "web_search_mock" in metadata_dict

    def test_includes_file_read(self):
        """Test that FileReadTool is included."""
        metadata_list = get_builtin_tools_metadata()

        metadata_dict = {meta.name: (meta, cls) for meta, cls in metadata_list}
        assert "file_read" in metadata_dict
