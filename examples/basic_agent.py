"""Basic example of using the 4-tuple agent abstraction.

This example shows how to:
1. Create an AgentTuple
2. Use AgentFactory to spawn a SubAgent
3. Execute the agent and get an Observation
"""

import asyncio
import logging

from aorchestra import AgentTuple, AgentFactory, Observation
from aorchestra.models.config import ModelConfig
from aorchestra.tools.mock import EchoTool, CalculatorTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run a basic agent example."""

    # Configure the model (using mock for this example)
    model = ModelConfig(
        name="glm-4.7",
        api_base="https://api.z.ai/v1",
        api_key="dummy",  # Replace with real key for production
    )

    # Create a 4-tuple defining the sub-agent
    agent_tuple = AgentTuple(
        instruction="Calculate the sum of 15 and 27",
        tools=[CalculatorTool()],
        model=model,
    )

    # Use AgentFactory to create the sub-agent
    factory = AgentFactory()

    # For this example, we'll use a mock instead of real LLM
    # In production, you would do:
    # result = await factory.create_and_execute(agent_tuple)

    # Instead, let's demonstrate the structure:
    agent = factory.create(agent_tuple)
    logger.info(f"Created agent for instruction: {agent_tuple.instruction}")
    logger.info(f"Available tools: {[t.name for t in agent_tuple.tools]}")
    logger.info(f"Model: {agent_tuple.model.name}")

    # The agent.execute() would call the LLM here
    # For demo purposes, we'll just show the structure
    print("\n=== Agent Configuration ===")
    print(f"Instruction: {agent_tuple.instruction}")
    print(f"Prompt: {agent_tuple.build_prompt()}")
    print(f"Tools: {[t.name for t in agent_tuple.tools]}")
    print(f"Model: {agent_tuple.model.name}")

    print("\n=== Example Observation Structure ===")
    demo_observation = Observation(
        result_summary="Calculator tool executed successfully",
        artifacts={"calculator": 42.0},
        error_logs=[],
    )
    print(f"Result Summary: {demo_observation.result_summary}")
    print(f"Artifacts: {demo_observation.artifacts}")
    print(f"Error Logs: {demo_observation.error_logs}")


if __name__ == "__main__":
    asyncio.run(main())
