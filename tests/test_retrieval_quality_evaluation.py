import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluate_retrieval_quality import evaluate_cases, load_cases
from models import EvidenceSource


class RetrievalQualityEvaluationTests(unittest.TestCase):
    def test_evaluation_measures_expected_document_and_correct_abstention(self):
        cases = [
            {
                "id": "DOC-01",
                "message": "Pregunta documental revisada.",
                "expected": "evidence",
                "expected_title_contains": ["Gestión de documentos"],
            },
            {
                "id": "NOE-01",
                "message": "Pregunta sin evidencia revisada.",
                "expected": "sin_evidencia",
                "expected_title_contains": [],
            },
            {
                "id": "CTX-01",
                "message": "Precauciones antes de actualizar.",
                "expected": "solicita_contexto",
                "expected_title_contains": [],
            },
        ]

        def retriever(message):
            if message.startswith("Pregunta documental"):
                return [
                    EvidenceSource(
                        tipo="sharepoint",
                        titulo="Gestión de Documentos.pdf — Página 4",
                        ubicacion="https://contoso.example/documentos.pdf",
                        fragmento="Contenido de prueba.",
                    )
                ]
            if message.startswith("Precauciones"):
                from models import RetrievalTrace

                return RetrievalTrace(requires_version_context=True)
            return []

        report = evaluate_cases(cases, retriever)

        self.assertEqual(3, report["summary"]["passed_count"])
        self.assertEqual(1.0, report["summary"]["evidence_recall"])
        self.assertEqual(1.0, report["summary"]["correct_abstention_rate"])
        self.assertEqual(1.0, report["summary"]["correct_context_request_rate"])
        self.assertEqual(3, len(report["results"]))
        self.assertTrue(all(result["latency_ms"] >= 0 for result in report["results"]))
        self.assertIsNotNone(report["summary"]["retrieval_latency_ms_p95"])
        self.assertIn("answer_state", report["results"][0])
        self.assertIn("single_source_rate", report["summary"])
        self.assertEqual("solicita_contexto", report["results"][2]["answer_state"])

    def test_loader_rejects_evidence_case_without_a_reviewed_document(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(
                json.dumps(
                    [
                        {
                            "id": "DOC-01",
                            "message": "Pregunta sin documento esperado.",
                            "expected": "evidence",
                            "expected_title_contains": [],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_cases(path)

    def test_loader_rejects_unknown_quality_category(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(
                json.dumps(
                    [
                        {
                            "id": "DOC-01",
                            "message": "Pregunta documental revisada.",
                            "expected": "evidence",
                            "expected_title_contains": ["Gestión"],
                            "category": "unknown",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_cases(path)

    def test_loader_accepts_conceptual_quality_category(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(
                json.dumps(
                    [
                        {
                            "id": "CON-01",
                            "message": "Pregunta conceptual revisada.",
                            "expected": "evidence",
                            "expected_title_contains": ["Manual general"],
                            "category": "conceptual",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual("conceptual", load_cases(path)[0]["category"])

    def test_loader_rejects_titles_for_context_request(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(
                json.dumps(
                    [{
                        "id": "CTX-01",
                        "message": "Precauciones antes de actualizar.",
                        "expected": "solicita_contexto",
                        "expected_title_contains": ["Readme"],
                    }]
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_cases(path)

    def test_underspecified_case_skips_retrieval_and_counts_as_correct_abstention(self):
        cases = [
            {
                "id": "INSUF-01",
                "message": "¿Qué se debe revisar?",
                "expected": "sin_evidencia",
                "expected_title_contains": [],
            }
        ]
        calls = []

        def retriever(message):
            calls.append(message)
            return [
                EvidenceSource(
                    tipo="sharepoint",
                    titulo="Documento tangencial",
                    ubicacion="https://contoso.example/doc.pdf",
                    fragmento="Texto relacionado.",
                )
            ]

        report = evaluate_cases(cases, retriever)

        self.assertEqual([], calls)
        self.assertEqual(1.0, report["summary"]["correct_abstention_rate"])
        self.assertEqual("sin_evidencia", report["results"][0]["answer_state"])


if __name__ == "__main__":
    unittest.main()
