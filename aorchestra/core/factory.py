"""AgentFactory for creating SubAgent instances.

AgentFactory provides a clean interface for spawning sub-agents
from 4-tuples. It validates configurations and handles errors.
"""

import logging
from typing import Tuple
from aorchestra.core.tuples import AgentTuple
from aorchestra.core.agents import SubAgent
from aorchestra.core.observations import Observation
from aorchestra.models.cost import CostRecord
from aorchestra.tools.base import validate_tool

logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating SubAgent instances from AgentTuples.

    The factory validates the tuple configuration and ensures tools
    are valid before creating a SubAgent. Used by the Orchestrator
    to spawn sub-agents dynamically.
    """

    def create(self, tuple_def: AgentTuple) -> SubAgent:
        """Create a SubAgent from an AgentTuple.

        Validates the tuple configuration and instantiates a SubAgent.

        Args:
            tuple_def: The 4-tuple defining the sub-agent.

        Returns:
            A configured SubAgent instance.

        Raises:
            ValueError: If the tuple configuration is invalid.
            TypeError: If tools don't implement the Tool protocol.
        """
        self._validate_tuple(tuple_def)
        logger.info(f"Creating SubAgent for instruction: {tuple_def.instruction[:50]}...")
        return SubAgent(tuple_def)

    def _validate_tuple(self, tuple_def: AgentTuple) -> None:
        """Validate an AgentTuple configuration.

        Args:
            tuple_def: The tuple to validate.

        Raises:
            ValueError: If validation fails.
            TypeError: If tools are invalid.
        """
        # Pydantic validates basic structure, but we add custom checks
        if not tuple_def.instruction.strip():
            raise ValueError("AgentTuple instruction cannot be empty")

        # Validate tools implement Tool protocol
        for i, tool in enumerate(tuple_def.tools):
            try:
                validate_tool(tool)
            except TypeError as e:
                raise TypeError(
                    f"Tool at index {i} is invalid: {e}"
                ) from e

        # Validate model configuration
        if not tuple_def.model.name:
            raise ValueError("Model name cannot be empty")
        if not tuple_def.model.api_base:
            raise ValueError("Model api_base cannot be empty")

        logger.debug("AgentTuple validation successful")

    async def create_and_execute(
        self, tuple_def: AgentTuple
    ) -> Tuple[Observation, CostRecord]:
        """Convenience method to create and execute a SubAgent.

        Args:
            tuple_def: The 4-tuple defining the sub-agent.

        Returns:
            Tuple of (Observation, CostRecord) from the sub-agent execution.
        """
        agent = self.create(tuple_def)
        return await agent.execute()
