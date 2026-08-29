"""Synthetic Document Store Simulator.

Simulates an external clinical document repository storing physician referrals,
conservative therapy progress notes, and diagnostic reports.

Ref: docs/architecture/ARCHITECTURE.md §6.4, §13
"""

from healthflow_domain.external_models import (
    DocumentContent,
    DocumentMetadata,
)

from healthflow_infrastructure.simulators.models import (
    ALL_BENCHMARK_FIXTURES,
    SyntheticCaseFixture,
)


class SyntheticDocumentStoreSimulator:
    """In-memory deterministic simulator for external clinical document repositories."""

    def __init__(self, fixtures: dict[str, SyntheticCaseFixture] | None = None) -> None:
        self._is_available: bool = True
        self._documents: dict[str, DocumentContent] = {}

        # Populate from fixture datasets
        fixtures_map = fixtures if fixtures is not None else ALL_BENCHMARK_FIXTURES
        for fixture in fixtures_map.values():
            for doc_ref, doc_content in fixture.documents.items():
                self._documents[doc_ref] = doc_content

    def set_availability(self, available: bool) -> None:
        """Simulate document store availability or maintenance outage."""
        self._is_available = available

    def register_document(self, document: DocumentContent) -> None:
        """Store or override a synthetic document."""
        self._documents[document.document_reference] = document

    def remove_document(self, document_reference: str) -> None:
        """Simulate missing or deleted document."""
        self._documents.pop(document_reference, None)

    def get_document_metadata(self, document_reference: str) -> DocumentMetadata | None:
        """Retrieve metadata for a specified document reference."""
        if not self._is_available:
            return None

        doc = self._documents.get(document_reference)
        return doc.metadata if doc else None

    def get_document_content(self, document_reference: str) -> DocumentContent | None:
        """Retrieve document content and metadata."""
        if not self._is_available:
            return None

        return self._documents.get(document_reference)
