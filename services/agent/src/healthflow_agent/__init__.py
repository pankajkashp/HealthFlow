"""HealthFlow agent service.

This package hosts the AWS Strands Agents SDK runtime and Claude LLM integration.
The agent is a reasoning component that invokes authorized application-layer tool functions only.

Architecture position: Agent layer (services/agent).
Production dependencies: AWS Strands Agents SDK, boto3 Bedrock Runtime client.

PHASE 1 NOTE: Agent implementation is NOT in scope for Phase 1.
Strands SDK, Claude, and Bedrock dependencies are added in the agent implementation phase.

Ref: docs/architecture/ARCHITECTURE.md §2.6, §7
"""
