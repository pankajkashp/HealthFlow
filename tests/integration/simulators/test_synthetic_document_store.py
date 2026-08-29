"""Integration tests for Synthetic Document Store Simulator & Adapter.

Verifies document metadata lookup, content retrieval, fault injection, and DocumentStorePort compliance.
Ref: docs/architecture/ARCHITECTURE.md §6.4, §13
"""

from healthflow_domain import DocumentStorePort
from healthflow_domain.external_models import (
    DocumentContent,
    DocumentMetadata,
)
from healthflow_infrastructure.simulators import (
    SyntheticDocumentStoreAdapter,
    SyntheticDocumentStoreSimulator,
)


class TestSyntheticDocumentStore:
    def test_get_valid_document_metadata_and_content(self) -> None:
        sim = SyntheticDocumentStoreSimulator()
        meta = sim.get_document_metadata("doc_ref_jenkins_001")
        assert meta is not None
        assert meta.document_reference == "doc_ref_jenkins_001"
        assert meta.document_type == "physician_referral"
        assert meta.patient_id == "pat_jenkins_001"
        assert meta.file_format == "PDF"

        content = sim.get_document_content("doc_ref_jenkins_001")
        assert content is not None
        assert "radiculopathy" in content.text_content

    def test_get_nonexistent_document_returns_none(self) -> None:
        sim = SyntheticDocumentStoreSimulator()
        assert sim.get_document_metadata("doc_ref_missing_999") is None
        assert sim.get_document_content("doc_ref_missing_999") is None

    def test_simulated_document_store_downtime(self) -> None:
        sim = SyntheticDocumentStoreSimulator()
        sim.set_availability(False)
        assert sim.get_document_metadata("doc_ref_jenkins_001") is None
        assert sim.get_document_content("doc_ref_jenkins_001") is None

        sim.set_availability(True)
        assert sim.get_document_metadata("doc_ref_jenkins_001") is not None

    def test_remove_document_simulates_missing_artifact(self) -> None:
        sim = SyntheticDocumentStoreSimulator()
        assert sim.get_document_metadata("doc_ref_jenkins_002") is not None
        sim.remove_document("doc_ref_jenkins_002")
        assert sim.get_document_metadata("doc_ref_jenkins_002") is None

    def test_dynamic_document_registration(self) -> None:
        sim = SyntheticDocumentStoreSimulator()
        custom_doc = DocumentContent(
            document_reference="doc_ref_custom_55",
            document_type="specialist_evaluation",
            text_content="Orthopedic consultation report.",
            metadata=DocumentMetadata(
                document_reference="doc_ref_custom_55",
                document_type="specialist_evaluation",
                patient_id="pat_custom_55",
                created_date="2026-08-20",
                author_reference="dr_consult",
                file_format="PDF",
                content_hash="hash_55",
            ),
        )
        sim.register_document(custom_doc)
        fetched = sim.get_document_content("doc_ref_custom_55")
        assert fetched is not None
        assert fetched.text_content == "Orthopedic consultation report."

    def test_document_store_adapter_implements_port(self) -> None:
        sim = SyntheticDocumentStoreSimulator()
        adapter: DocumentStorePort = SyntheticDocumentStoreAdapter(sim)

        meta = adapter.get_document_metadata("doc_ref_jenkins_001")
        assert meta is not None
        assert meta.document_type == "physician_referral"

        content = adapter.get_document_content("doc_ref_jenkins_001")
        assert content is not None
        assert "radiculopathy" in content.text_content
