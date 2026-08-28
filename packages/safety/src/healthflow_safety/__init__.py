"""HealthFlow safety layer.

This package implements deterministic input validation, permission checks, and safety gates.
Safety controls are implemented in code, NOT in LLM prompts.

Architecture position: Safety layer.
Allowed dependencies: Domain layer (packages/domain).
Prohibited: Safety controls must never be bypassed by any other layer.

Ref: docs/architecture/ARCHITECTURE.md §2.7, §8
"""
