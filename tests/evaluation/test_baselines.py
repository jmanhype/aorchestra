"""Tests for evaluation baseline implementations."""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from aorchestra.evaluation.baselines import SingleAgentBaseline, StaticRolesBaseline
from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation
from aorchestra.models.config import ModelConfig
from aorchestra.models.cost import CostRecord
from aorchestra.tools.registry import ToolRegistry, ToolMetadata


class TestSingleAgentBaseline:
    """Tests for SingleAgentBaseline class."""

    @pytest.fixture
    def model_config(self):
        """Create a test model configuration."""
        return ModelConfig(
            name="test-model",
            api_base="https://api.example.com",
            api_key="test-key",
            temperature=0.0,
        )

    @pytest.fixture
    def tool_registry(self):
        """Create a test tool registry with mock tools."""
        registry = ToolRegistry()

        # Create a mock tool
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "A test tool"
        mock_tool.execute = AsyncMock(return_value="Tool result")

        # Register the tool
        metadata = ToolMetadata(
            name="test_tool",
            description="A test tool",
            tags=["test"],
            capabilities=["test"],
        )
        registry.register(mock_tool, metadata)

        return registry

    @pytest.fixture
    def single_agent_baseline(self, model_config, tool_registry):
        """Create a SingleAgentBaseline instance."""
        return SingleAgentBaseline(model_config, tool_registry)

    @pytest.mark.asyncio
    async def test_solve_returns_answer_and_cost_record(self, single_agent_baseline):
        """Test that solve() returns tuple of (answer, cost_record)."""
        # Mock the factory's create_and_execute method
        mock_observation = Observation(
            result_summary="Test answer",
            details="Test details",
            tool_calls=[],
        )
        mock_cost_record = CostRecord(
            model_name="test-model",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=0.001,
        )

        with patch.object(
            single_agent_baseline.factory,
            "create_and_execute",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = (mock_observation, mock_cost_record)

            # Call solve
            answer, cost_record = await single_agent_baseline.solve(
                goal="Test goal",
                tool_names=["test_tool"],
            )

            # Verify return values
            assert answer == "Test answer"
            assert cost_record == mock_cost_record

    @pytest.mark.asyncio
    async def test_solve_builds_correct_agent_tuple(self, single_agent_baseline):
        """Test that solve() builds correct AgentTuple."""
        with patch.object(
            single_agent_baseline.factory,
            "create_and_execute",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = (
                Observation(result_summary="Answer", details="", tool_calls=[]),
                CostRecord(model_name="test", prompt_tokens=0, completion_tokens=0, total_tokens=0, estimated_cost_usd=0),
            )

            # Call solve
            await single_agent_baseline.solve(
                goal="Test goal",
                tool_names=["test_tool"],
                context="Test context",
            )

            # Verify AgentTuple was built correctly
            call_args = mock_execute.call_args[0][0]
            assert isinstance(call_args, AgentTuple)
            assert call_args.instruction == "Test goal"
            assert call_args.context == "Test context"
            assert len(call_args.tools) == 1
            assert call_args.tools[0].name == "test_tool"
            assert call_args.model.name == "test-model"

    @pytest.mark.asyncio
    async def test_solve_with_multiple_tools(self, single_agent_baseline, tool_registry):
        """Test solve with multiple tools."""
        # Add another tool
        mock_tool2 = Mock()
        mock_tool2.name = "test_tool_2"
        mock_tool2.description = "Another test tool"
        mock_tool2.execute = AsyncMock(return_value="Tool result 2")

        metadata2 = ToolMetadata(
            name="test_tool_2",
            description="Another test tool",
            tags=["test"],
            capabilities=["test"],
        )
        tool_registry.register(mock_tool2, metadata2)

        with patch.object(
            single_agent_baseline.factory,
            "create_and_execute",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = (
                Observation(result_summary="Answer", details="", tool_calls=[]),
                CostRecord(model_name="test", prompt_tokens=0, completion_tokens=0, total_tokens=0, estimated_cost_usd=0),
            )

            # Call solve with multiple tools
            await single_agent_baseline.solve(
                goal="Test goal",
                tool_names=["test_tool", "test_tool_2"],
            )

            # Verify both tools are in the tuple
            call_args = mock_execute.call_args[0][0]
            assert len(call_args.tools) == 2
            tool_names = [t.name for t in call_args.tools]
            assert "test_tool" in tool_names
            assert "test_tool_2" in tool_names

    @pytest.mark.asyncio
    async def test_solve_with_empty_context(self, single_agent_baseline):
        """Test solve with empty context (default)."""
        with patch.object(
            single_agent_baseline.factory,
            "create_and_execute",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = (
                Observation(result_summary="Answer", details="", tool_calls=[]),
                CostRecord(model_name="test", prompt_tokens=0, completion_tokens=0, total_tokens=0, estimated_cost_usd=0),
            )

            # Call solve without context
            await single_agent_baseline.solve(
                goal="Test goal",
                tool_names=["test_tool"],
            )

            # Verify context is empty
            call_args = mock_execute.call_args[0][0]
            assert call_args.context == ""

    @pytest.mark.asyncio
    async def test_solve_raises_error_for_unknown_tool(self, single_agent_baseline):
        """Test that solve raises ValueError for unknown tool."""
        with pytest.raises(ValueError, match="Tool not found in registry"):
            await single_agent_baseline.solve(
                goal="Test goal",
                tool_names=["unknown_tool"],
            )

    @pytest.mark.asyncio
    async def test_solve_no_delegation_occurs(self, single_agent_baseline):
        """Test that no delegation occurs (single agent execution)."""
        with patch.object(
            single_agent_baseline.factory,
            "create_and_execute",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = (
                Observation(result_summary="Answer", details="", tool_calls=[]),
                CostRecord(model_name="test", prompt_tokens=0, completion_tokens=0, total_tokens=0, estimated_cost_usd=0),
            )

            # Call solve
            await single_agent_baseline.solve(
                goal="Test goal",
                tool_names=["test_tool"],
            )

            # Verify create_and_execute was called once (single execution)
            assert mock_execute.call_count == 1

            # Verify no delegation in result
            observation = mock_execute.return_value[0]
            # SingleAgentBaseline has no concept of delegation - it's just one execution
            assert observation is not None


class TestStaticRolesBaseline:
    """Tests for StaticRolesBaseline class."""

    @pytest.fixture
    def model_config(self):
        """Create a test model configuration."""
        return ModelConfig(
            name="test-model",
            api_base="https://api.example.com",
            api_key="test-key",
            temperature=0.0,
        )

    @pytest.fixture
    def tool_registry(self):
        """Create a test tool registry with mock tools."""
        registry = ToolRegistry()

        # Create mock tools for each type
        tools = {
            "calculator": Mock(name="CalculatorTool"),
            "code_execute": Mock(name="CodeExecuteTool"),
            "web_search_mock": Mock(name="WebSearchMockTool"),
            "file_read": Mock(name="FileReadTool"),
        }

        for tool_name, tool in tools.items():
            tool.name = tool_name
            tool.description = f"A {tool_name} tool"
            tool.execute = AsyncMock(return_value=f"{tool_name} result")

            metadata = ToolMetadata(
                name=tool_name,
                description=f"A {tool_name} tool",
                tags=[tool_name],
                capabilities=[tool_name],
            )
            registry.register(tool, metadata)

        return registry

    @pytest.fixture
    def static_roles_baseline(self, model_config, tool_registry):
        """Create a StaticRolesBaseline instance."""
        return StaticRolesBaseline(model_config, tool_registry)

    def test_creates_four_fixed_agents(self, static_roles_baseline):
        """Test that all four agents are created correctly."""
        assert "math" in static_roles_baseline.agents
        assert "code" in static_roles_baseline.agents
        assert "research" in static_roles_baseline.agents
        assert "planning" in static_roles_baseline.agents

    def test_math_agent_has_calculator_tool(self, static_roles_baseline):
        """Test that math agent has calculator tool."""
        math_agent = static_roles_baseline.agents["math"]
        assert len(math_agent.tuple.tools) == 1
        assert math_agent.tuple.tools[0].name == "calculator"
        assert "math expert" in math_agent.tuple.context.lower()

    def test_code_agent_has_code_execute_tool(self, static_roles_baseline):
        """Test that code agent has code_execute tool."""
        code_agent = static_roles_baseline.agents["code"]
        assert len(code_agent.tuple.tools) == 1
        assert code_agent.tuple.tools[0].name == "code_execute"
        assert "coding expert" in code_agent.tuple.context.lower()

    def test_research_agent_has_web_search_mock_tool(self, static_roles_baseline):
        """Test that research agent has web_search_mock tool."""
        research_agent = static_roles_baseline.agents["research"]
        assert len(research_agent.tuple.tools) == 1
        assert research_agent.tuple.tools[0].name == "web_search_mock"
        assert "research expert" in research_agent.tuple.context.lower()

    def test_planning_agent_has_file_read_tool(self, static_roles_baseline):
        """Test that planning agent has file_read tool."""
        planning_agent = static_roles_baseline.agents["planning"]
        assert len(planning_agent.tuple.tools) == 1
        assert planning_agent.tuple.tools[0].name == "file_read"
        assert "planning expert" in planning_agent.tuple.context.lower()

    @pytest.mark.asyncio
    async def test_select_agent_type_returns_valid_type(self, static_roles_baseline):
        """Test that _select_agent_type returns a valid agent type."""
        # Mock the OpenAI client response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "math"

        with patch.object(
            static_roles_baseline.client.chat.completions,
            "create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = mock_response

            agent_type = await static_roles_baseline._select_agent_type("Calculate 2 + 2")
            assert agent_type == "math"

            # Verify the call
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["temperature"] == 0.0
            assert call_kwargs["max_tokens"] == 10

    @pytest.mark.asyncio
    async def test_select_agent_type_with_various_goals(self, static_roles_baseline):
        """Test agent selection with different types of goals."""
        test_cases = [
            ("Calculate the area of a circle", "math"),
            ("Write Python code to sort a list", "code"),
            ("Search for information about machine learning", "research"),
            ("Read the file and summarize its contents", "planning"),
        ]

        for goal, expected_agent in test_cases:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = expected_agent

            with patch.object(
                static_roles_baseline.client.chat.completions,
                "create",
                new_callable=AsyncMock,
            ) as mock_create:
                mock_create.return_value = mock_response

                agent_type = await static_roles_baseline._select_agent_type(goal)
                assert agent_type == expected_agent

    @pytest.mark.asyncio
    async def test_select_agent_type_defaults_to_math_on_invalid(self, static_roles_baseline):
        """Test that _select_agent_type defaults to 'math' on invalid selection."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "invalid_agent"

        with patch.object(
            static_roles_baseline.client.chat.completions,
            "create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = mock_response

            agent_type = await static_roles_baseline._select_agent_type("Test goal")
            assert agent_type == "math"

    @pytest.mark.asyncio
    async def test_select_agent_type_defaults_to_math_on_error(self, static_roles_baseline):
        """Test that _select_agent_type defaults to 'math' on error."""
        with patch.object(
            static_roles_baseline.client.chat.completions,
            "create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.side_effect = Exception("API error")

            agent_type = await static_roles_baseline._select_agent_type("Test goal")
            assert agent_type == "math"

    @pytest.mark.asyncio
    async def test_solve_selects_and_executes_agent(self, static_roles_baseline):
        """Test that solve() selects agent type and executes it."""
        # Mock agent selection
        with patch.object(
            static_roles_baseline,
            "_select_agent_type",
            new_callable=AsyncMock,
        ) as mock_select:
            mock_select.return_value = "math"

            # Mock agent execution
            math_agent = static_roles_baseline.agents["math"]
            mock_observation = Observation(
                result_summary="Math answer",
                details="Math details",
                tool_calls=[],
            )
            mock_cost_record = CostRecord(
                model_name="test-model",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost_usd=0.001,
            )

            with patch.object(math_agent, "execute", new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = (mock_observation, mock_cost_record)

                # Call solve
                answer, cost_record = await static_roles_baseline.solve(
                    goal="Calculate 2 + 2",
                    tool_names=["calculator"],
                    context="Test context",
                )

                # Verify results
                assert answer == "Math answer"
                assert cost_record == mock_cost_record

                # Verify agent selection was called
                mock_select.assert_called_once_with("Calculate 2 + 2")

                # Verify agent was executed
                mock_execute.assert_called_once()
                # Check that instruction was updated
                assert math_agent.tuple.instruction == "Calculate 2 + 2"

    @pytest.mark.asyncio
    async def test_solve_with_code_agent(self, static_roles_baseline):
        """Test solve() with code agent."""
        with patch.object(
            static_roles_baseline,
            "_select_agent_type",
            new_callable=AsyncMock,
        ) as mock_select:
            mock_select.return_value = "code"

            code_agent = static_roles_baseline.agents["code"]
            mock_observation = Observation(
                result_summary="Code answer",
                details="Code details",
                tool_calls=[],
            )
            mock_cost_record = CostRecord(
                model_name="test-model",
                prompt_tokens=200,
                completion_tokens=100,
                total_tokens=300,
                estimated_cost_usd=0.002,
            )

            with patch.object(code_agent, "execute", new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = (mock_observation, mock_cost_record)

                answer, cost_record = await static_roles_baseline.solve(
                    goal="Write a hello world program",
                    tool_names=["code_execute"],
                )

                assert answer == "Code answer"
                assert cost_record == mock_cost_record

    @pytest.mark.asyncio
    async def test_solve_ignores_tool_names_and_context(self, static_roles_baseline):
        """Test that solve() ignores tool_names and context parameters."""
        with patch.object(
            static_roles_baseline,
            "_select_agent_type",
            new_callable=AsyncMock,
        ) as mock_select:
            mock_select.return_value = "research"

            research_agent = static_roles_baseline.agents["research"]
            original_tools = research_agent.tuple.tools.copy()
            original_context = research_agent.tuple.context

            with patch.object(research_agent, "execute", new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = (
                    Observation(result_summary="Answer", details="", tool_calls=[]),
                    CostRecord(model_name="test", prompt_tokens=0, completion_tokens=0, total_tokens=0, estimated_cost_usd=0),
                )

                # Call solve with different tool_names and context
                await static_roles_baseline.solve(
                    goal="Search for info",
                    tool_names=["calculator", "code_execute"],  # Should be ignored
                    context="Custom context",  # Should be ignored
                )

                # Verify tools and context were not changed
                assert research_agent.tuple.tools == original_tools
                assert research_agent.tuple.context == original_context

    @pytest.mark.asyncio
    async def test_solve_falls_back_to_math_on_missing_agent(self, static_roles_baseline):
        """Test that solve() falls back to math agent if selected agent is missing."""
        # Temporarily remove code agent
        code_agent = static_roles_baseline.agents.pop("code")

        with patch.object(
            static_roles_baseline,
            "_select_agent_type",
            new_callable=AsyncMock,
        ) as mock_select:
            mock_select.return_value = "code"  # Try to select missing agent

            math_agent = static_roles_baseline.agents["math"]
            with patch.object(math_agent, "execute", new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = (
                    Observation(result_summary="Math answer", details="", tool_calls=[]),
                    CostRecord(model_name="test", prompt_tokens=0, completion_tokens=0, total_tokens=0, estimated_cost_usd=0),
                )

                # Should fall back to math agent
                answer, cost_record = await static_roles_baseline.solve(
                    goal="Test goal",
                    tool_names=[],
                )

                # Verify math agent was used
                assert mock_execute.called
                assert math_agent.tuple.instruction == "Test goal"

            # Restore code agent
            static_roles_baseline.agents["code"] = code_agent

    @pytest.mark.asyncio
    async def test_solve_raises_error_when_no_agents_available(self, tool_registry):
        """Test that solve() raises RuntimeError when no agents are available."""
        # Create baseline with empty registry (no tools = no agents)
        empty_registry = ToolRegistry()
        model_config = ModelConfig(
            name="test-model",
            api_base="https://api.example.com",
            api_key="test-key",
        )

        baseline = StaticRolesBaseline(model_config, empty_registry)

        # All agents dict should be empty
        assert len(baseline.agents) == 0

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="No agents available"):
            await baseline.solve(goal="Test goal", tool_names=[])

    @pytest.mark.asyncio
    async def test_solve_with_research_agent(self, static_roles_baseline):
        """Test solve() with research agent."""
        with patch.object(
            static_roles_baseline,
            "_select_agent_type",
            new_callable=AsyncMock,
        ) as mock_select:
            mock_select.return_value = "research"

            research_agent = static_roles_baseline.agents["research"]
            mock_observation = Observation(
                result_summary="Research answer",
                details="Research details",
                tool_calls=[],
            )
            mock_cost_record = CostRecord(
                model_name="test-model",
                prompt_tokens=150,
                completion_tokens=75,
                total_tokens=225,
                estimated_cost_usd=0.0015,
            )

            with patch.object(research_agent, "execute", new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = (mock_observation, mock_cost_record)

                answer, cost_record = await static_roles_baseline.solve(
                    goal="Search for Python info",
                    tool_names=["web_search_mock"],
                )

                assert answer == "Research answer"
                assert cost_record == mock_cost_record

    @pytest.mark.asyncio
    async def test_solve_with_planning_agent(self, static_roles_baseline):
        """Test solve() with planning agent."""
        with patch.object(
            static_roles_baseline,
            "_select_agent_type",
            new_callable=AsyncMock,
        ) as mock_select:
            mock_select.return_value = "planning"

            planning_agent = static_roles_baseline.agents["planning"]
            mock_observation = Observation(
                result_summary="Planning answer",
                details="Planning details",
                tool_calls=[],
            )
            mock_cost_record = CostRecord(
                model_name="test-model",
                prompt_tokens=120,
                completion_tokens=60,
                total_tokens=180,
                estimated_cost_usd=0.0012,
            )

            with patch.object(planning_agent, "execute", new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = (mock_observation, mock_cost_record)

                answer, cost_record = await static_roles_baseline.solve(
                    goal="Read and summarize the file",
                    tool_names=["file_read"],
                )

                assert answer == "Planning answer"
                assert cost_record == mock_cost_record
