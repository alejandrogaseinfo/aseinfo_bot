import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from models import EvidenceSource, RetrievalTrace
from retrieval import retrieve_evidence


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.local_evidence = [
            EvidenceSource(
                tipo="documento",
                titulo="Respaldo local",
                ubicacion="docs/respaldo.md",
                fragmento="Información solo para desarrollo.",
            )
        ]

    def test_production_does_not_fall_back_to_local_documents(self):
        config = SimpleNamespace(
            environment="production",
            azure_search_configured=True,
            azure_search_index_name="libras-docs",
            allow_local_document_fallback=False,
        )

        with patch("retrieval.retrieve_azure_search_evidence", return_value=[]), patch(
            "retrieval.retrieve_document_evidence", return_value=self.local_evidence
        ) as local_retrieval:
            evidence = retrieve_evidence("¿Qué dice el manual?", config=config)

        self.assertEqual([], evidence)
        local_retrieval.assert_not_called()

    def test_development_uses_local_documents_without_calling_pending_azure_search(self):
        config = SimpleNamespace(
            environment="local",
            azure_search_configured=True,
            azure_search_enabled=False,
            azure_search_index_name="libras-docs",
            allow_local_document_fallback=True,
        )

        with patch("retrieval.retrieve_azure_search_evidence", return_value=[]), patch(
            "retrieval.retrieve_document_evidence", return_value=self.local_evidence
        ) as local_retrieval:
            evidence = retrieve_evidence("¿Qué dice el manual?", config=config)

        self.assertEqual(self.local_evidence, evidence)
        local_retrieval.assert_called_once_with("¿Qué dice el manual?")

    def test_development_can_opt_in_to_azure_search(self):
        config = SimpleNamespace(
            environment="local",
            azure_search_configured=True,
            azure_search_enabled=True,
            azure_search_index_name="libras-docs",
            allow_local_document_fallback=True,
        )

        with patch("retrieval.retrieve_azure_search_evidence", return_value=[] ) as azure_retrieval, patch(
            "retrieval.retrieve_document_evidence", return_value=self.local_evidence
        ):
            retrieve_evidence("¿Qué dice el manual?", config=config)

        azure_retrieval.assert_called_once()

    def test_v2_keeps_azure_abstention_instead_of_using_local_documents(self):
        config = SimpleNamespace(
            environment="local",
            azure_search_configured=True,
            azure_search_enabled=True,
            azure_search_index_name="libras-docs-v2-candidate",
            retrieval_strategy="v2",
            allow_local_document_fallback=True,
        )

        with patch(
            "retrieval.retrieve_azure_search_evidence", return_value=RetrievalTrace()
        ), patch("retrieval.retrieve_document_evidence", return_value=self.local_evidence) as local_retrieval:
            evidence = retrieve_evidence("¿Qué dice el manual?", config=config, return_trace=True)

        self.assertEqual([], evidence.sources)
        local_retrieval.assert_not_called()


if __name__ == "__main__":
    unittest.main()
