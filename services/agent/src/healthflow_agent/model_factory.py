"""Factory for the Strands model provider, selected by AgentConfig.llm_provider.

Ref: docs/phases/PHASE_06_WALKTHROUGH.md, decision 1 (swappable LLM provider).
"""

from __future__ import annotations

from typing import Any

from healthflow_agent.config import AgentConfig


def build_model(config: AgentConfig) -> Any | None:
    """Return a Strands Model for the configured provider, or None for the scripted provider."""
    if config.llm_provider == "scripted":
        return None

    if config.llm_provider == "anthropic":
        if not config.anthropic_api_key:
            raise ValueError(
                "LLM_PROVIDER=anthropic requires ANTHROPIC_API_KEY to be set. "
                "Get a key at https://console.anthropic.com, or set LLM_PROVIDER=scripted."
            )
        from strands.models import AnthropicModel

        return AnthropicModel(
            client_args={"api_key": config.anthropic_api_key},
            model_id=config.anthropic_model_id,
            max_tokens=config.max_tokens,
            params={"temperature": config.temperature},
        )

    if config.llm_provider == "bedrock":
        from strands.models import BedrockModel

        return BedrockModel(
            model_id=config.bedrock_model_id,
            region_name=config.aws_region,
            temperature=config.temperature,
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER: {config.llm_provider!r}. Expected 'scripted', 'anthropic', or 'bedrock'."
    )
