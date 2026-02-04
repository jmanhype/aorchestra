"""Configuration management for AOrchestra."""

import json
import os
from dataclasses import dataclass, field
from typing import Dict

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration."""

    zai_api_key: str
    zai_api_base: str
    zai_model: str

    # Cost-aware routing configuration (Item 004)
    cost_rates: Dict[str, Dict[str, float]] = field(default_factory=dict)
    lambda_param: float = 0.5

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        # Load cost rates from environment variable
        cost_rates = {}
        cost_rates_json = os.getenv("COST_RATES", "{}")
        try:
            cost_rates = json.loads(cost_rates_json)
            # Validate format: {"model_name": {"input": float, "output": float}}
            for model_name, rates in cost_rates.items():
                if not isinstance(rates, dict):
                    raise ValueError(f"Cost rates for {model_name} must be a dict")
                if "input" not in rates or "output" not in rates:
                    raise ValueError(
                        f"Cost rates for {model_name} must have 'input' and 'output' keys"
                    )
        except json.JSONDecodeError as e:
            # Use default rates if JSON is invalid
            default_rates = {
                "glm-4-flash": {"input": 0.0001, "output": 0.0002},
                "glm-4.7": {"input": 0.001, "output": 0.002},
                "glm-4-plus": {"input": 0.01, "output": 0.02},
            }
            cost_rates = default_rates

        # Load lambda parameter from environment variable
        lambda_str = os.getenv("LAMBDA", "0.5")
        try:
            lambda_param = float(lambda_str)
            # Clamp to [0.0, 1.0] range
            lambda_param = max(0.0, min(1.0, lambda_param))
        except ValueError:
            # Use default if parsing fails
            lambda_param = 0.5

        return cls(
            zai_api_key=os.getenv("ZAI_API_KEY", ""),
            zai_api_base=os.getenv("ZAI_API_BASE", "https://api.z.ai/v1"),
            zai_model=os.getenv("ZAI_MODEL", "glm-4.7"),
            cost_rates=cost_rates,
            lambda_param=lambda_param,
        )
