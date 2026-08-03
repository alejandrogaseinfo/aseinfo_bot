import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluate_intent_router import DEFAULT_CASES_PATH, evaluate_cases, load_cases
from intent import IntentResult


class IntentEvaluationTests(unittest.TestCase):
    def test_corpus_contains_balanced_non_sensitive_routes(self):
        cases = load_cases(DEFAULT_CASES_PATH)
        purposes = {case["conversation_purpose"] for case in cases}

        self.assertGreaterEqual(len(cases), 30)
        self.assertTrue({"capacidad", "alcance", "ayuda", "saludo", "aclaracion", "none"}.issubset(purposes))

    def test_evaluation_compares_all_router_fields(self):
        cases = [
            {
                "id": "CASE-01",
                "message": "Pregunta segura",
                "intent": "ayuda",
                "conversation_purpose": "capacidad",
                "requires_context": False,
            }
        ]

        results = evaluate_cases(
            cases,
            lambda _message: IntentResult(
                name="ayuda", requires_context=False, conversation_purpose="capacidad"
            ),
        )

        self.assertTrue(results[0]["passed"])

    def test_evaluation_reports_a_wrong_route(self):
        cases = [
            {
                "id": "CASE-02",
                "message": "Pregunta segura",
                "intent": "ayuda",
                "conversation_purpose": "alcance",
                "requires_context": False,
            }
        ]

        results = evaluate_cases(
            cases,
            lambda _message: IntentResult(
                name="consulta_documental", requires_context=False
            ),
        )

        self.assertFalse(results[0]["passed"])
        self.assertEqual("consulta_documental", results[0]["actual"]["intent"])

    def test_evaluation_accepts_equivalent_clarification_routes(self):
        cases = [
            {
                "id": "CASE-CLARIFY",
                "message": "Pregunta segura",
                "intent": "reporte_error",
                "conversation_purpose": "aclaracion",
                "requires_context": True,
            }
        ]

        results = evaluate_cases(
            cases,
            lambda _message: IntentResult(
                name="consulta_ambigua",
                requires_context=True,
                conversation_purpose="aclaracion",
            ),
        )

        self.assertTrue(results[0]["passed"])
        self.assertFalse(results[0]["exact_match"])

    def test_evaluation_reports_a_classifier_failure_without_aborting(self):
        cases = [
            {
                "id": "CASE-03",
                "message": "Pregunta segura",
                "intent": "ayuda",
                "conversation_purpose": "ayuda",
                "requires_context": False,
            }
        ]

        def unavailable_classifier(_message):
            raise TimeoutError("proveedor no disponible")

        results = evaluate_cases(cases, unavailable_classifier)

        self.assertFalse(results[0]["passed"])
        self.assertEqual("TimeoutError: proveedor no disponible", results[0]["error"])
