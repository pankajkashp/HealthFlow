"""HealthFlow API application package.

This package is the HTTP boundary between the Next.js frontend and the
HealthFlow application layer. It accepts HTTP requests, validates request schemas,
delegates to application use cases, and serializes responses.

Architecture position: API layer (apps/api).
Must NOT contain business logic.
Must NOT access the database directly.
Must NOT bypass the application layer.

Ref: docs/architecture/ARCHITECTURE.md §2.2, §16
"""
