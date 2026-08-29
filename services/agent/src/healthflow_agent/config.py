"""HealthFlow Agent Configuration.

Settings for AWS Bedrock, Claude model parameters, and execution limits.
Loaded from environment variables with safe, production-grade defaults.

Ref: docs/architecture/ARCHITECTURE.md §2.6, §7
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    """Configuration for HealthFlow AI Agent runtime."""

    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    bedrock_model_id: str = os.getenv(
        "BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
    )
    max_iterations: int = int(os.getenv("AGENT_MAX_ITERATIONS", "15"))
    temperature: float = float(os.getenv("AGENT_TEMPERATURE", "0.0"))
    timeout_seconds: int = int(os.getenv("AGENT_TIMEOUT_SECONDS", "60"))
