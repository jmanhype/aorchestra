"""SubAgent execution engine.

SubAgent takes an AgentTuple and executes it by:
1. Building a prompt from instruction + context
2. Calling the LLM with available tools
3. Returning a structured Observation

Each sub-agent runs in isolation with only its assigned context and tools.
"""

import asyncio
import logging
from typing import Any
from openai import AsyncOpenAI

from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation
from aorchestra.tools.base import Tool

logger = logging.getLogger(__name__)


class SubAgent:
    """A sub-agent that executes a single 4-tuple.

    SubAgents are created by AgentFactory and run in isolation.
    They have access only to their assigned context and tools.
    """

    def __init__(self, tuple_def: AgentTuple, client: AsyncOpenAI | None = None):
        """Initialize the SubAgent with an AgentTuple.

        Args:
            tuple_def: The 4-tuple defining this agent's configuration.
            client: Optional OpenAI client for testing (defaults to None, creates new client).
        """
        self.tuple = tuple_def
        self._client = client

    @property
    def client(self) -> AsyncOpenAI:
        """Lazy-initialized OpenAI client."""
        if self._client is None:
            kwargs = self.tuple.model.to_openai_kwargs()
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    async def execute(self) -> Observation:
        """Execute the sub-agent's task.

        Builds a prompt from instruction + context, calls the LLM,
        invokes tools if needed, and returns a structured Observation.

        Returns:
            Observation with result_summary, artifacts, and error_logs.
        """
        try:
            return await self._execute_impl()
        except Exception as e:
            logger.exception("SubAgent execution failed")
            return Observation(
                result_summary=f"Execution failed: {e}",
                error_logs=[f"Critical error: {type(e).__name__}: {e}"],
            )

    async def _execute_impl(self) -> Observation:
        """Internal implementation of execute().

        Returns:
            Observation with execution results.
        """
        # Build prompt from instruction + context
        prompt = self.tuple.build_prompt()
        logger.info(f"Executing sub-agent with prompt: {prompt[:100]}...")

        # Prepare tools for OpenAI function calling (if supported)
        tools = self._prepare_tools()
        artifacts: dict[str, Any] = {}
        error_logs: list[str] = []

        # Call LLM
        response = await self._call_llm(prompt, tools)

        # Process response and invoke tools if needed
        result_summary, tool_artifacts, tool_errors = await self._process_response(
            response, tools
        )
        artifacts.update(tool_artifacts)
        error_logs.extend(tool_errors)

        return Observation(
            result_summary=result_summary,
            artifacts=artifacts,
            error_logs=error_logs,
        )

    def _prepare_tools(self) -> list[dict[str, Any]]:
        """Convert tool objects to OpenAI function-calling format.

        Returns:
            List of tool definitions in OpenAI format.
        """
        openai_tools = []
        for tool in self.tuple.tools:
            if hasattr(tool, "name") and hasattr(tool, "description"):
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": {
                            "type": "object",
                            "properties": {},  # Could be enhanced with schema
                        },
                    },
                })
        return openai_tools

    async def _call_llm(
        self, prompt: str, tools: list[dict[str, Any]]
    ) -> Any:
        """Call the LLM with the prompt and tools.

        Args:
            prompt: The prompt to send to the LLM.
            tools: List of tools in OpenAI format.

        Returns:
            LLM response object.
        """
        kwargs = {
            "model": self.tuple.model.name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.tuple.model.temperature,
            "max_tokens": self.tuple.model.max_tokens,
        }

        # Add tools if available (may not be supported by all models)
        if tools:
            kwargs["tools"] = tools

        response = await self.client.chat.completions.create(**kwargs)
        return response

    async def _process_response(
        self, response: Any, tool_definitions: list[dict[str, Any]]
    ) -> tuple[str, dict[str, Any], list[str]]:
        """Process the LLM response and invoke tools if requested.

        Args:
            response: Raw LLM response.
            tool_definitions: List of tool definitions.

        Returns:
            Tuple of (result_summary, artifacts, error_logs).
        """
        choice = response.choices[0]
        message = choice.message

        # Check if model requested tool calls
        tool_calls = getattr(message, "tool_calls", None)

        if tool_calls:
            return await self._handle_tool_calls(tool_calls)
        else:
            # Simple text response
            return message.content, {}, []

    async def _handle_tool_calls(
        self, tool_calls: list[Any]
    ) -> tuple[str, dict[str, Any], list[str]]:
        """Handle tool calls requested by the LLM.

        Args:
            tool_calls: List of tool call objects from LLM.

        Returns:
            Tuple of (result_summary, artifacts, error_logs).
        """
        artifacts = {}
        error_logs = []
        results = []

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool = self._find_tool(tool_name)

            if tool is None:
                error_logs.append(f"Tool not found: {tool_name}")
                continue

            try:
                # Parse arguments (JSON string -> dict)
                import json
                args = json.loads(tool_call.function.arguments)

                # Execute tool
                result = await tool.execute(**args)
                results.append(f"{tool_name}: {result}")
                artifacts[tool_name] = result

            except Exception as e:
                error_msg = f"Tool {tool_name} failed: {e}"
                error_logs.append(error_msg)
                logger.exception(error_msg)

        # Generate summary from tool results
        if results:
            result_summary = "Executed tools: " + ", ".join(results)
        else:
            result_summary = "Tool execution completed with errors"

        return result_summary, artifacts, error_logs

    def _find_tool(self, name: str) -> Tool | None:
        """Find a tool by name in the tuple's tool list.

        Args:
            name: Tool name to find.

        Returns:
            Tool object or None if not found.
        """
        for tool in self.tuple.tools:
            if hasattr(tool, "name") and tool.name == name:
                return tool
        return None
