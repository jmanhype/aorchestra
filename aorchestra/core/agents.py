"""SubAgent execution engine.

SubAgent takes an AgentTuple and executes it by:
1. Building a prompt from instruction + context
2. Calling LLM with available tools
3. Returning a structured Observation

Each sub-agent runs in isolation with only its assigned context and tools.
"""

import asyncio
import logging
from typing import Any, Tuple
from openai import AsyncOpenAI

from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation
from aorchestra.models.cost import CostRecord
from aorchestra.tools.base import Tool

logger = logging.getLogger(__name__)


class SubAgent:
    """A sub-agent that executes a single 4-tuple.

    SubAgents are created by AgentFactory and run in isolation.
    They have access only to their assigned context and tools.
    """

    def __init__(self, tuple_def: AgentTuple, client: AsyncOpenAI | None = None):
        """Initialize SubAgent with an AgentTuple.

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
            self._client = AsyncOpenAI(**kwargs, timeout=60.0)
        return self._client

    async def execute(self) -> Tuple[Observation, CostRecord]:
        """Execute sub-agent's task.

        Builds a prompt from instruction + context, calls LLM,
        invokes tools if needed, and returns a structured Observation.

        Returns:
            Tuple of (Observation with result_summary, artifacts, and error_logs,
                      CostRecord with token usage and estimated cost).
        """
        try:
            return await self._execute_impl()
        except Exception as e:
            logger.exception("SubAgent execution failed")
            observation = Observation(
                result_summary=f"Execution failed: {e}",
                error_logs=[f"Critical error: {type(e).__name__}: {e}"],
            )
            # Return zero cost record on error
            cost_record = CostRecord(
                model_name=self.tuple.model.name,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                estimated_cost_usd=0.0,
            )
            return observation, cost_record

    async def _execute_impl(self) -> Tuple[Observation, CostRecord]:
        """Internal implementation of execute() with multi-turn tool calling.

        Supports up to MAX_TOOL_ROUNDS of tool call → result → LLM loops.

        Returns:
            Tuple of (Observation, CostRecord).
        """
        MAX_TOOL_ROUNDS = 5
        prompt = self.tuple.build_prompt()
        logger.info(f"Executing sub-agent with prompt: {prompt[:100]}...")

        tools = self._prepare_tools()
        artifacts: dict[str, Any] = {}
        error_logs: list[str] = []

        # Build conversation messages
        messages = [{"role": "user", "content": prompt}]

        # Accumulate cost across rounds
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0

        for round_num in range(MAX_TOOL_ROUNDS):
            # Call LLM
            response, round_cost = await self._call_llm_messages(messages, tools)
            total_prompt_tokens += round_cost.prompt_tokens
            total_completion_tokens += round_cost.completion_tokens
            total_tokens += round_cost.total_tokens

            # Check for valid response
            if not hasattr(response, 'choices') or response.choices is None:
                # Anthropic-style or failed response
                content = self._extract_content(response)
                observation = Observation(
                    result_summary=content or "No response",
                    artifacts=artifacts,
                    error_logs=error_logs,
                )
                break

            choice = response.choices[0]
            message = choice.message
            tool_calls = getattr(message, "tool_calls", None)

            if not tool_calls:
                # No more tool calls — we have the final answer
                observation = Observation(
                    result_summary=message.content or "",
                    artifacts=artifacts,
                    error_logs=error_logs,
                )
                break

            # Execute tool calls and build tool result messages
            # Add assistant message with tool calls
            assistant_msg = {"role": "assistant", "content": message.content or ""}
            if tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                    }
                    for tc in tool_calls
                ]
            messages.append(assistant_msg)

            # Execute each tool and add result messages
            for tc in tool_calls:
                tool_name = tc.function.name
                tool = self._find_tool(tool_name)
                if tool is None:
                    error_logs.append(f"Tool not found: {tool_name}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": f"Error: tool '{tool_name}' not found",
                    })
                    continue

                try:
                    import json
                    args = json.loads(tc.function.arguments)
                    logger.info(f"[Round {round_num+1}] Tool call: {tool_name}({args})")
                    result = await tool.execute(**args)
                    artifacts[f"{tool_name}_r{round_num+1}"] = result
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": str(result),
                    })
                except Exception as e:
                    error_msg = f"Tool {tool_name} failed: {e}"
                    error_logs.append(error_msg)
                    logger.exception(error_msg)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": f"Error: {e}",
                    })
        else:
            # Hit max rounds
            observation = Observation(
                result_summary=f"Reached max tool rounds ({MAX_TOOL_ROUNDS}). Last results: {artifacts}",
                artifacts=artifacts,
                error_logs=error_logs,
            )

        cost_record = CostRecord(
            model_name=self.tuple.model.name,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=0.0,
        )
        return observation, cost_record

    def _extract_content(self, response: Any) -> str:
        """Extract text content from non-OpenAI response formats."""
        if hasattr(response, 'content'):
            if isinstance(response.content, list):
                return " ".join(getattr(block, 'text', str(block)) for block in response.content)
            return str(response.content)
        return ""

    async def _call_llm_messages(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> Tuple[Any, CostRecord]:
        """Call LLM with full message history (for multi-turn)."""
        kwargs = {
            "model": self.tuple.model.name,
            "messages": messages,
            "temperature": self.tuple.model.temperature,
            "max_tokens": self.tuple.model.max_tokens,
        }
        if tools:
            kwargs["tools"] = tools

        response = await self.client.chat.completions.create(**kwargs)

        usage = response.usage
        if usage:
            prompt_tokens = getattr(usage, "prompt_tokens", 0)
            completion_tokens = getattr(usage, "completion_tokens", 0)
            total_tokens = getattr(usage, "total_tokens", 0)
        else:
            prompt_tokens = sum(len(str(m.get("content", ""))) // 4 for m in messages)
            completion_tokens = 0
            total_tokens = prompt_tokens

        cost_record = CostRecord(
            model_name=self.tuple.model.name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=0.0,
        )
        return response, cost_record

    def _prepare_tools(self) -> list[dict[str, Any]]:
        """Convert tool objects to OpenAI function-calling format.

        Returns:
            List of tool definitions in OpenAI format.
        """
        openai_tools = []
        for tool in self.tuple.tools:
            if hasattr(tool, "name") and hasattr(tool, "description"):
                # Extract parameter schema from tool if available
                params = {"type": "object", "properties": {}}
                if hasattr(tool, "parameters"):
                    params = tool.parameters
                elif hasattr(tool, "get_schema"):
                    params = tool.get_schema()
                else:
                    # Introspect execute() signature for parameter info
                    import inspect
                    sig = inspect.signature(tool.execute)
                    properties = {}
                    required = []
                    for name, param in sig.parameters.items():
                        if name == "self":
                            continue
                        ptype = "string"
                        annotation = param.annotation
                        if annotation in (float, int):
                            ptype = "number"
                        elif annotation == bool:
                            ptype = "boolean"
                        properties[name] = {"type": ptype}
                        if param.default is inspect.Parameter.empty:
                            required.append(name)
                    params = {"type": "object", "properties": properties}
                    if required:
                        params["required"] = required

                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": params,
                    },
                })
        return openai_tools

    async def _call_llm(
        self, prompt: str, tools: list[dict[str, Any]]
    ) -> Tuple[Any, CostRecord]:
        """Call LLM with prompt and tools.

        Args:
            prompt: The prompt to send to LLM.
            tools: List of tools in OpenAI format.

        Returns:
            Tuple of (LLM response object, CostRecord with token usage).
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

        # Extract token usage from response
        usage = response.usage

        if usage:
            try:
                prompt_tokens = getattr(usage, "prompt_tokens", 0)
                completion_tokens = getattr(usage, "completion_tokens", 0)
                total_tokens = getattr(usage, "total_tokens", 0)
            except AttributeError:
                # Usage object doesn't have expected attributes
                prompt_tokens = 0
                completion_tokens = 0
                total_tokens = 0
        else:
            # No usage data available, estimate from prompt length
            # Rough estimate: 1 token ≈ 4 characters
            prompt_tokens = len(prompt) // 4
            completion_tokens = 0
            total_tokens = prompt_tokens + completion_tokens

        # Create cost record with placeholder cost (recalculated later)
        cost_record = CostRecord(
            model_name=self.tuple.model.name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=0.0,  # Placeholder, recalculated later with actual tier rates
        )

        return response, cost_record

    async def _process_response(
        self, response: Any, tool_definitions: list[dict[str, Any]]
    ) -> tuple[str, dict[str, Any], list[str]]:
        """Process LLM response and invoke tools if requested.

        Args:
            response: Raw LLM response.
            tool_definitions: List of tool definitions.

        Returns:
            Tuple of (result_summary, artifacts, error_logs).
        """
        # Handle different response formats (OpenAI vs Anthropic-compatible)
        if not hasattr(response, 'choices') or response.choices is None:
            # Try to extract content from Anthropic-style response
            content = ""
            if hasattr(response, 'content'):
                if isinstance(response.content, list):
                    content = " ".join(
                        getattr(block, 'text', str(block))
                        for block in response.content
                    )
                else:
                    content = str(response.content)
            elif isinstance(response, dict):
                content = response.get('content', [{}])
                if isinstance(content, list) and content:
                    content = content[0].get('text', str(content))
                else:
                    content = str(content)
            return content or "No response", {}, []

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
        """Handle tool calls requested by LLM.

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
                logger.info(f"Tool call: {tool_name}({args})")

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
        """Find a tool by name in tuple's tool list.

        Args:
            name: Tool name to find.

        Returns:
            Tool object or None if not found.
        """
        for tool in self.tuple.tools:
            if hasattr(tool, "name") and tool.name == name:
                return tool
        return None
