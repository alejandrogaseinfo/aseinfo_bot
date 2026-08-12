import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluate_retrieval_quality import comparison_summary, evaluate_strategy_variants
from models import EvidenceSource, RetrievalTrace


class RetrievalEvaluationTests(unittest.TestCase):
    def test_variants_use_the_same_cases_and_expose_comparable_metrics(self):
        cases = [
            {
                "id": "positive",
                "message": "¿Dónde está el procedimiento?",
                "expected": "evidence",
                "expected_title_contains": ["Manual"],
                "category": "procedural",
            },
            {
                "id": "negative",
                "message": "¿Cuál es la edad de Messi?",
                "expected": "sin_evidencia",
                "expected_title_contains": [],
                "category": "out_of_scope",
            },
        ]
        evidence = [
            EvidenceSource(
                tipo="sharepoint",
                titulo="Manual autorizado",
                ubicacion="https://example.test/manual",
                fragmento="Procedimiento documentado.",
            )
        ]

        def current(message):
            return RetrievalTrace(
                sources=evidence if message.startswith("¿Dónde") else [],
                candidate_count=4,
                direct_evidence_count=1 if message.startswith("¿Dónde") else 0,
                stage_counts={"bounded_pool": 4, "rerank_pool": 4},
            )

        def expanded(message):
            return RetrievalTrace(
                sources=evidence if message.startswith("¿Dónde") else [],
                candidate_count=12,
                direct_evidence_count=1 if message.startswith("¿Dónde") else 0,
                stage_counts={"bounded_pool": 12, "rerank_pool": 12},
            )

        reports = evaluate_strategy_variants(
            cases,
            {"actual": current, "ampliada": expanded},
        )
        summary = comparison_summary(reports)

        self.assertEqual(2, summary["actual"]["case_count"])
        self.assertEqual(summary["actual"]["evidence_recall"], summary["ampliada"]["evidence_recall"])
        self.assertEqual(12, reports["ampliada"]["results"][0]["candidate_count"])


if __name__ == "__main__":
    unittest.main()
