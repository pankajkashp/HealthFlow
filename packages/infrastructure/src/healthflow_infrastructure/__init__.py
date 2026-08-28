"""HealthFlow infrastructure layer.

This package implements port interfaces defined in the domain layer:
database repositories, simulated system adapters, and the pgvector/RAG adapter.

Architecture position: Infrastructure layer.
Allowed dependencies: Domain layer (packages/domain), SQLAlchemy 2.x, Alembic, pgvector, boto3.
Prohibited: SQLAlchemy model types must not leak into domain or application layers.

Note: Production infrastructure dependencies (SQLAlchemy, etc.) are added in the
infrastructure implementation phase, not in Phase 1.

Ref: docs/architecture/ARCHITECTURE.md §2.5
"""
