import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from intent import classify_intent


class IntentTests(unittest.TestCase):
    def _client_with_content(self, content):
        return SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **_kwargs: SimpleNamespace(
                        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
                    )
                )
            )
        )

    def test_classify_intent_accepts_whitelisted_result(self):
        result = classify_intent(
            "Buenas, ¿me puedes orientar?",
            self._client_with_content('{"intencion":"ayuda","requiere_contexto":false}'),
            "test-model",
        )

        self.assertEqual("ayuda", result.name)
        self.assertFalse(result.requires_context)
        self.assertEqual("ayuda", result.conversation_purpose)

    def test_classify_intent_recognizes_capability_paraphrases(self):
        result = classify_intent(
            "¿Cómo me puedes apoyar?",
            self._client_with_content(
                '{"intencion":"ayuda","proposito_conversacional":"capacidad",'
                '"requiere_contexto":false}'
            ),
            "test-model",
        )

        self.assertEqual("ayuda", result.name)
        self.assertEqual("capacidad", result.conversation_purpose)

    def test_classify_intent_recognizes_scope_paraphrases(self):
        result = classify_intent(
            "¿Sobre qué carpetas puedes buscar?",
            self._client_with_content(
                '{"intencion":"ayuda","proposito_conversacional":"alcance",'
                '"requiere_contexto":false}'
            ),
            "test-model",
        )

        self.assertEqual("ayuda", result.name)
        self.assertEqual("alcance", result.conversation_purpose)

    def test_classify_intent_rejects_unknown_result(self):
        result = classify_intent(
            "Hola",
            self._client_with_content('{"intencion":"respuesta_libre"}'),
            "test-model",
        )

        self.assertIsNone(result)

    def test_classify_intent_accepts_out_of_scope_route(self):
        result = classify_intent(
            "¿Cuál es la edad de Messi?",
            self._client_with_content(
                '{"intencion":"fuera_alcance",'
                '"proposito_conversacional":"none",'
                '"requiere_contexto":false}'
            ),
            "test-model",
        )

        self.assertIsNotNone(result)
        self.assertEqual("fuera_alcance", result.name)
        self.assertFalse(result.requires_context)

    def test_classify_intent_rejects_inconsistent_documentary_purpose(self):
        result = classify_intent(
            "¿Qué indica el manual?",
            self._client_with_content(
                '{"intencion":"consulta_documental",'
                '"proposito_conversacional":"capacidad","requiere_contexto":false}'
            ),
            "test-model",
        )

        self.assertIsNone(result)

    def test_classify_intent_normalizes_clarification_purpose_for_an_error(self):
        result = classify_intent(
            "Algo falla en Evolution",
            self._client_with_content(
                '{"intencion":"reporte_error","proposito_conversacional":"none",'
                '"requiere_contexto":true}'
            ),
            "test-model",
        )

        self.assertEqual("reporte_error", result.name)
        self.assertTrue(result.requires_context)
        self.assertEqual("aclaracion", result.conversation_purpose)

    def test_classify_intent_normalizes_help_without_context_request(self):
        result = classify_intent(
            "No sé cómo preguntarte lo que necesito",
            self._client_with_content(
                '{"intencion":"ayuda","proposito_conversacional":"aclaracion",'
                '"requiere_contexto":true}'
            ),
            "test-model",
        )

        self.assertEqual("ayuda", result.name)
        self.assertFalse(result.requires_context)
        self.assertEqual("ayuda", result.conversation_purpose)


if __name__ == "__main__":
    unittest.main()
