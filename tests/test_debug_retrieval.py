import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from debug_retrieval import build_debug_payload, retrieve_raw_azure_candidates
from models import EvidenceSource, RetrievalTrace


class DebugRetrievalTests(unittest.TestCase):
    def test_payload_shows_evidence_and_retrieval_diagnostics(self):
        config = SimpleNamespace(
            azure_search_configured=True,
            azure_search_index_name="libras-docs",
            retrieval_strategy="v2",
        )
        trace = RetrievalTrace(
            sources=[
                EvidenceSource(
                    tipo="sharepoint",
                    titulo="Readme 1.24.1.5.pdf — Página 5",
                    ubicacion="https://sharepoint.example/readme.pdf",
                    fragmento="Se actualizó la versión de Crystal Reports.",
                    document_version="1.24.1.5",
                    covered_requirements=("r1",),
                )
            ],
            candidate_count=7,
            direct_evidence_count=1,
            requirement_count=1,
            covered_requirement_count=1,
            rejected_reasons={"version": 2},
        )

        with patch("debug_retrieval.retrieve_raw_azure_candidates", return_value=[]), patch(
            "debug_retrieval.retrieve_azure_search_evidence", return_value=trace
        ):
            payload = build_debug_payload("¿Qué versión usó jquery?", config)

        self.assertEqual("azure_ai_search", payload["origen"])
        self.assertEqual(7, payload["diagnostico"]["candidatos_recibidos"])
        self.assertEqual(
            "Readme 1.24.1.5.pdf — Página 5",
            payload["evidencia_que_recibe_el_bot"][0]["titulo"],
        )

    def test_raw_candidates_preserve_azure_rank_and_matching_excerpt(self):
        class FakeSearchClient:
            def search(self, **_kwargs):
                return [
                    {
                        "title": "Readme 1.24.1.5.pdf — Página 4",
                        "chunk_number": 4,
                        "source_url": "https://sharepoint.example/readme.pdf",
                        "content": "Error de Jquery en encuestas de Clima Laboral.",
                        "@search.score": 2.5,
                    }
                ]

        config = SimpleNamespace(
            azure_search_endpoint="https://search.example",
            azure_search_index_name="libras-docs",
            azure_search_api_key="not-a-real-key",
            azure_search_use_entra_id=False,
            azure_search_use_semantic=False,
        )
        with patch("debug_retrieval.SearchClient", return_value=FakeSearchClient()):
            candidates = retrieve_raw_azure_candidates("¿Qué versión usó jquery?", config)

        self.assertEqual(1, candidates[0]["rango_azure"])
        self.assertEqual("Readme 1.24.1.5.pdf — Página 4", candidates[0]["titulo"])
        self.assertIn("Jquery", candidates[0]["fragmento"])

    def test_payload_requires_azure_search_configuration(self):
        config = SimpleNamespace(azure_search_configured=False)

        with self.assertRaisesRegex(RuntimeError, "no está configurado"):
            build_debug_payload("consulta", config)


if __name__ == "__main__":
    unittest.main()
