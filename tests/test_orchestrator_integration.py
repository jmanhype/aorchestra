"""Integration tests for Orchestrator with ToolRegistry (Item 003)."""

import pytest

from aorchestra.core.orchestrator import Orchestrator
from aorchestra.models.config import ModelConfig
from aorchestra.tools import ToolRegistry, ToolMetadata, CalculatorTool
from aorchestra.core.observations import Observation
from aorchestra.core.tuples import AgentTuple
from aorchestra.orchestrator.state import OrchestratorState, Delegation
from aorchestra.orchestrator.actions import DelegateAction
from aorchestra.models.cost import CostRecord


def _make_cost_record(model_name: str = "gpt-4") -> CostRecord:
    """Helper to create a cost record."""
    return CostRecord(
        model_name=model_name,
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        estimated_cost_usd=0.001,
    )


@pytest.fixture
def model_config():
    return ModelConfig(name="gpt-4", api_key="test-key", api_base="https://api.openai.com/v1")


class TestOrchestratorToolRegistryIntegration:
    """Tests for Orchestrator integration with ToolRegistry."""

    def test_orchestrator_creates_tool_registry(self, model_config):
        orch = Orchestrator(model=model_config)
        assert hasattr(orch, 'tool_registry')
        assert isinstance(orch.tool_registry, ToolRegistry)

    def test_orchestrator_registers_four_builtin_tools(self, model_config):
        orch = Orchestrator(model=model_config)
        assert "calculator" in orch.tool_registry
        assert "code_execute" in orch.tool_registry
        assert "web_search_mock" in orch.tool_registry
        assert "file_read" in orch.tool_registry
        assert len(orch.tool_registry) == 4

    def test_custom_tool_registry_injection(self, model_config):
        custom_registry = ToolRegistry()
        tool = CalculatorTool()
        metadata = ToolMetadata(name=tool.name, description=tool.description, tags=["custom"])
        custom_registry.register(tool, metadata)

        orch = Orchestrator(model=model_config, tool_registry=custom_registry)
        assert orch.tool_registry is custom_registry
        assert len(orch.tool_registry) == 1

    def test_filter_tools_with_tool_names(self, model_config):
        orch = Orchestrator(model=model_config)
        tools = orch._filter_tools(["calculator", "web_search_mock"])
        assert len(tools) == 2
        names = {t.name for t in tools}
        assert names == {"calculator", "web_search_mock"}

    def test_filter_tools_skips_nonexistent_names(self, model_config):
        orch = Orchestrator(model=model_config)
        tools = orch._filter_tools(["calculator", "nonexistent", "file_read"])
        assert len(tools) == 2
        names = {t.name for t in tools}
        assert names == {"calculator", "file_read"}

    def test_filter_tools_empty_names(self, model_config):
        orch = Orchestrator(model=model_config)
        tools = orch._filter_tools([])
        assert isinstance(tools, list)

    def test_filter_tools_with_state_history(self, model_config):
        orch = Orchestrator(model=model_config)
        orch.state = OrchestratorState(goal="test", max_steps=10)

        tuple_def = AgentTuple(instruction="Calculate something", context="", tools=[], model=model_config)
        obs = Observation(result_summary="Calculated the sum")
        delegation = Delegation(step=0, tuple=tuple_def, observation=obs, cost_record=_make_cost_record())
        orch.state.add_delegation(delegation)

        tools = orch._filter_tools([])
        assert isinstance(tools, list)

    def test_filter_tools_handles_none_state(self, model_config):
        orch = Orchestrator(model=model_config)
        orch.state = None
        tools = orch._filter_tools([])
        assert isinstance(tools, list)

    def test_build_context_for_subagent(self, model_config):
        orch = Orchestrator(model=model_config)
        orch.state = OrchestratorState(goal="test", max_steps=10)

        for i in range(5):
            tuple_def = AgentTuple(instruction=f"Task {i}", context="", tools=[], model=model_config)
            obs = Observation(result_summary=f"Result {i}")
            delegation = Delegation(step=i, tuple=tuple_def, observation=obs, cost_record=_make_cost_record())
            orch.state.add_delegation(delegation)

        action = DelegateAction(instruction="New task", context="Some context", tools=[], reasoning="test")
        context = orch._build_context_for_subagent(action)
        assert isinstance(context, str)

    def test_build_context_for_subagent_handles_none_state(self, model_config):
        orch = Orchestrator(model=model_config)
        orch.state = None
        action = DelegateAction(instruction="New task", context="Some context", tools=[], reasoning="test")
        context = orch._build_context_for_subagent(action)
        assert isinstance(context, str)


class TestOrchestratorEndToEnd:
    """End-to-end tests for Orchestrator with tool selection."""

    def test_backward_compatibility(self, model_config):
        orch = Orchestrator(model=model_config)
        assert orch.tool_registry is not None
        assert len(orch.tool_registry) > 0
        assert hasattr(orch, '_filter_tools')
        assert hasattr(orch, '_build_context_for_subagent')
        assert hasattr(orch, 'run')

    def test_tool_registry_separate_instances(self, model_config):
        orch1 = Orchestrator(model=model_config)
        orch2 = Orchestrator(model=model_config)
        assert orch1.tool_registry is not orch2.tool_registry
        assert len(orch1.tool_registry) == len(orch2.tool_registry)
        assert set(orch1.tool_registry.list_tools()) == set(orch2.tool_registry.list_tools())

    def test_context_curation_realistic(self, model_config):
        orch = Orchestrator(model=model_config)
        orch.state = OrchestratorState(goal="Analyze and calculate", max_steps=10)

        history_items = [
            ("Search for python async", "Found asyncio documentation"),
            ("Read config file", "Config loaded successfully"),
            ("Calculate sum", "Sum is 42"),
            ("Execute test code", "Tests passed"),
            ("Search for optimization", "Found optimization tips"),
        ]

        for i, (instruction, result) in enumerate(history_items):
            tuple_def = AgentTuple(instruction=instruction, context="", tools=[], model=model_config)
            obs = Observation(result_summary=result)
            delegation = Delegation(step=i, tuple=tuple_def, observation=obs, cost_record=_make_cost_record())
            orch.state.add_delegation(delegation)

        action = DelegateAction(
            instruction="Use python asyncio for async programming",
            context="", tools=["code_execute"], reasoning="Need async",
        )
        context = orch._build_context_for_subagent(action)
        assert isinstance(context, str)

    def test_tool_selection_for_different_subtasks(self, model_config):
        orch = Orchestrator(model=model_config)
        orch.state = OrchestratorState(goal="Math problem", max_steps=10)

        tuple_def = AgentTuple(instruction="Calculate the sum", context="", tools=[], model=model_config)
        obs = Observation(result_summary="Sum calculated")
        orch.state.add_delegation(Delegation(step=0, tuple=tuple_def, observation=obs, cost_record=_make_cost_record()))

        tools = orch._filter_tools([])
        assert isinstance(tools, list)
