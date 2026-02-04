"""Built-in tools for AOrchestra.

Item 003: Four built-in tools for common operations.
"""

import asyncio
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from aorchestra.tools.registry import ToolMetadata


class CalculatorTool:
    """A basic calculator tool for arithmetic operations.

    Enhanced from tools/mock.py with Tool metadata support.
    """

    name: str = "calculator"
    description: str = "Performs basic arithmetic operations: add, subtract, multiply, divide"

    async def execute(self, operation: str, a: float, b: float) -> float:
        """Execute a calculator operation.

        Args:
            operation: One of 'add', 'subtract', 'multiply', 'divide'
            a: First operand
            b: Second operand

        Returns:
            Result of the arithmetic operation

        Raises:
            ValueError: If operation is unknown or divide by zero
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


class CodeExecuteTool:
    """Safely executes Python code in a subprocess.

    Uses subprocess with timeout for basic isolation. Not full
    container sandbox but provides basic safety by restricting
    environment variables and limiting execution time.
    """

    name: str = "code_execute"
    description: str = "Executes Python code safely in a subprocess. Returns stdout and stderr."

    def __init__(self, timeout: int = 10):
        """Initialize the code execution tool.

        Args:
            timeout: Maximum execution time in seconds (default: 10)
        """
        self.timeout = timeout

    async def execute(self, code: str) -> dict[str, Any]:
        """Execute Python code in a subprocess.

        Args:
            code: Python code to execute

        Returns:
            Dictionary with keys:
                - success (bool): Whether execution succeeded
                - stdout (str): Standard output
                - stderr (str): Standard error
                - returncode (int): Process return code

        Raises:
            TimeoutError: If execution exceeds timeout
            RuntimeError: If Python interpreter not found
        """
        # Restrict environment variables (remove PYTHONPATH)
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)

        try:
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                "python", "-c", code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            try:
                # Wait for completion with timeout
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError as e:
                # Kill process on timeout
                process.kill()
                await process.wait()
                raise TimeoutError(f"Code execution timed out after {self.timeout} seconds") from e

            # Decode output
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            return {
                "success": process.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": process.returncode,
            }

        except FileNotFoundError:
            raise RuntimeError("Python interpreter not found")
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
            }


class WebSearchMockTool:
    """Mock web search tool for testing and demonstration.

    Returns predefined search results based on keyword matching.
    No real API calls are made.
    """

    name: str = "web_search_mock"
    description: str = "Performs mock web search. Returns predefined results for testing."

    def __init__(self, search_index: dict[str, list[dict[str, Any]]] | None = None):
        """Initialize the mock web search tool.

        Args:
            search_index: Optional custom search index. If None, uses default.
        """
        self.search_index = search_index or self._default_search_index()

    @staticmethod
    def _default_search_index() -> dict[str, list[dict[str, Any]]]:
        """Get default search index.

        Returns:
            Dictionary mapping keywords to search results
        """
        return {
            "python": [
                {
                    "title": "Python Official Website",
                    "url": "https://python.org",
                    "snippet": "The official home of Python programming language."
                },
                {
                    "title": "Python Documentation",
                    "url": "https://docs.python.org",
                    "snippet": "Official Python documentation and tutorials."
                },
            ],
            "async": [
                {
                    "title": "Python asyncio Documentation",
                    "url": "https://docs.python.org/3/library/asyncio.html",
                    "snippet": "Asynchronous I/O, event loop, coroutines and tasks."
                },
            ],
            "machine learning": [
                {
                    "title": "Python Machine Learning",
                    "url": "https://scikit-learn.org",
                    "snippet": "Simple and efficient tools for predictive data analysis."
                },
            ],
        }

    async def execute(self, query: str, max_results: int = 5) -> dict[str, Any]:
        """Perform mock web search.

        Args:
            query: Search query string
            max_results: Maximum number of results to return (default: 5)

        Returns:
            Dictionary with keys:
                - query (str): The search query
                - results (list): List of search result dicts with title, url, snippet
                - total (int): Total number of results returned
        """
        query_lower = query.lower()
        matched_results = []

        # Match results by keywords
        for keyword, results in self.search_index.items():
            if keyword in query_lower:
                matched_results.extend(results)

        # Remove duplicates by URL
        seen_urls = set()
        unique_results = []
        for result in matched_results:
            url = result["url"]
            if url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)

        # Limit results
        results = unique_results[:max_results]

        return {
            "query": query,
            "results": results,
            "total": len(results),
        }


class FileReadTool:
    """Safely reads file contents with path validation.

    Validates that file paths are within allowed directories
    to prevent directory traversal attacks and unauthorized access.
    """

    name: str = "file_read"
    description: str = "Reads file contents safely. Supports text files with encoding."

    def __init__(self, allowed_dirs: list[str] | None = None):
        """Initialize the file read tool.

        Args:
            allowed_dirs: List of allowed directory paths. If None, uses current working directory.
        """
        self.allowed_dirs = allowed_dirs or [str(Path.cwd())]
        # Resolve to absolute paths
        self.allowed_dirs = [str(Path(d).resolve()) for d in self.allowed_dirs]

    async def execute(self, path: str, encoding: str = "utf-8") -> dict[str, Any]:
        """Read file contents.

        Args:
            path: Path to file to read
            encoding: File encoding (default: 'utf-8')

        Returns:
            Dictionary with keys:
                - success (bool): Whether read succeeded
                - content (str): File contents
                - path (str): Resolved absolute path
                - size (int): File size in bytes
                - error (str|None): Error message if failed

        Raises:
            FileNotFoundError: If file does not exist
            PermissionError: If file cannot be read
            ValueError: If path is invalid or outside allowed directories
        """
        # Resolve absolute path
        abs_path = Path(path).resolve()

        # Validate path is within allowed directories
        self._validate_path(abs_path)

        # Check file exists
        if not abs_path.is_file():
            raise FileNotFoundError(f"File not found: {path}")

        # Check file is readable
        if not os.access(abs_path, os.R_OK):
            raise PermissionError(f"Cannot read file (permission denied): {path}")

        try:
            # Read file contents
            content = abs_path.read_text(encoding=encoding)
            file_size = abs_path.stat().st_size

            return {
                "success": True,
                "content": content,
                "path": str(abs_path),
                "size": file_size,
                "error": None,
            }
        except UnicodeDecodeError as e:
            raise ValueError(f"Failed to decode file with encoding '{encoding}': {e}")
        except Exception as e:
            raise IOError(f"Failed to read file: {e}")

    def _validate_path(self, path: Path) -> None:
        """Validate that path is within allowed directories.

        Args:
            path: Path to validate

        Raises:
            ValueError: If path is outside allowed directories
        """
        # Resolve the path to absolute form
        try:
            abs_path = path.resolve()
        except (FileNotFoundError, PermissionError):
            # If path doesn't exist, get its parent and resolve that
            abs_path = path.absolute()

        abs_path_str = str(abs_path)

        for allowed_dir in self.allowed_dirs:
            # Ensure allowed_dir ends with path separator for proper matching
            allowed_dir_normalized = allowed_dir
            if not allowed_dir_normalized.endswith(os.sep):
                allowed_dir_normalized += os.sep

            # Check if normalized path starts with normalized allowed dir
            if abs_path_str.startswith(allowed_dir_normalized) or abs_path_str == allowed_dir.rstrip(os.sep):
                return

        raise ValueError(
            f"Path '{path}' is outside allowed directories: {self.allowed_dirs}"
        )


def get_builtin_tools_metadata() -> list[tuple[ToolMetadata, type]]:
    """Get metadata for all built-in tools.

    Returns:
        List of (ToolMetadata, tool_class) tuples for all built-in tools.
        Used for registering tools in ToolRegistry.
    """
    return [
        (
            ToolMetadata(
                name="calculator",
                description="Performs basic arithmetic operations: add, subtract, multiply, divide",
                tags=["math", "calculation", "arithmetic"],
                capabilities=["add", "subtract", "multiply", "divide"],
                requires_sandbox=False,
            ),
            CalculatorTool,
        ),
        (
            ToolMetadata(
                name="code_execute",
                description="Executes Python code safely in a subprocess. Returns stdout and stderr.",
                tags=["code", "execution", "python"],
                capabilities=["execute", "run_code"],
                requires_sandbox=True,
            ),
            CodeExecuteTool,
        ),
        (
            ToolMetadata(
                name="web_search_mock",
                description="Performs mock web search. Returns predefined results for testing.",
                tags=["web", "search", "research"],
                capabilities=["search", "query"],
                requires_sandbox=False,
            ),
            WebSearchMockTool,
        ),
        (
            ToolMetadata(
                name="file_read",
                description="Reads file contents safely. Supports text files with encoding.",
                tags=["file", "io", "filesystem"],
                capabilities=["read", "read_file"],
                requires_sandbox=False,
            ),
            FileReadTool,
        ),
    ]
