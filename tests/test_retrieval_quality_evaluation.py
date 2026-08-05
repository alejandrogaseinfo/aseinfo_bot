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
            return []

        report = evaluate_cases(cases, retriever)

        self.assertEqual(2, report["summary"]["passed_count"])
        self.assertEqual(1.0, report["summary"]["evidence_recall"])
        self.assertEqual(1.0, report["summary"]["correct_abstention_rate"])

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


if __name__ == "__main__":
    unittest.main()
