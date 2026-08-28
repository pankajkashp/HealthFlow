"""HealthFlow application layer.

This package implements use cases, workflow orchestration, and authorized agent tool definitions
for the HealthFlow prior-authorization workflow system.

Architecture position: Application layer.
Allowed dependencies: Domain layer (packages/domain), Safety layer (packages/safety).
Prohibited dependencies: Infrastructure implementations, FastAPI, SQLAlchemy, Strands, boto3.

Ref: docs/architecture/ARCHITECTURE.md §2.3
"""
