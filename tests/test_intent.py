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

    def test_classify_intent_rejects_unknown_result(self):
        result = classify_intent(
            "Hola",
            self._client_with_content('{"intencion":"respuesta_libre"}'),
            "test-model",
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
