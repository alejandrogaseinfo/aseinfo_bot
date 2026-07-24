import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from conversation import generate_conversational_response
from intent import IntentResult


class ConversationTests(unittest.TestCase):
    def test_generates_a_conversational_response_for_a_greeting(self):
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **_kwargs: SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                message=SimpleNamespace(
                                    content="Hola, ¿qué documentación quieres consultar?"
                                )
                            )
                        ]
                    )
                )
            )
        )

        response = generate_conversational_response(
            "Buenas, tengo una duda.",
            IntentResult(name="saludo", requires_context=False),
            client,
            "test-model",
        )

        self.assertEqual("Hola, ¿qué documentación quieres consultar?", response)


if __name__ == "__main__":
    unittest.main()
