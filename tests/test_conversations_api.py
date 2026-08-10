import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from conversation_mapping_store import (
    InMemoryConversationMappingStore,
    mapping_key,
)
from openai_conversations import OpenAIConversationAdapter


class ConversationMappingTests(unittest.TestCase):
    def test_mapping_key_is_stable_and_does_not_expose_teams_ids(self):
        key = mapping_key("tenant-a", "teams-conversation-123")
        self.assertEqual(key, mapping_key("tenant-a", "teams-conversation-123"))
        self.assertNotIn("tenant-a", key)
        self.assertNotIn("teams-conversation-123", key)

    def test_in_memory_store_is_create_if_absent_and_deletable(self):
        store = InMemoryConversationMappingStore()
        first = store.create_if_absent("row", "conv_1")
        second = store.create_if_absent("row", "conv_2")
        self.assertEqual("conv_1", first.openai_conversation_id)
        self.assertEqual(first, second)
        self.assertEqual("conv_1", store.get("row").openai_conversation_id)
        store.delete("row")
        self.assertIsNone(store.get("row"))


class OpenAIConversationAdapterTests(unittest.TestCase):
    def test_adapter_uses_conversations_and_responses(self):
        calls = []

        class FakeConversations:
            def create(self, **kwargs):
                calls.append(("create", kwargs))
                return SimpleNamespace(id="conv_1")

            def delete(self, conversation_id, **kwargs):
                calls.append(("delete", conversation_id, kwargs))

            class Items:
                def create(self, conversation_id, **kwargs):
                    calls.append(("items.create", conversation_id, kwargs))

                def list(self, conversation_id, **kwargs):
                    calls.append(("items.list", conversation_id, kwargs))
                    return []

            items = Items()

        class FakeResponses:
            def create(self, **kwargs):
                calls.append(("response", kwargs))
                return SimpleNamespace(output_text="Respuesta persistente")

        client = SimpleNamespace(
            conversations=FakeConversations(), responses=FakeResponses()
        )
        adapter = OpenAIConversationAdapter(client, timeout_seconds=2)

        conversation_id = adapter.create()
        answer = adapter.respond(
            conversation_id,
            "Hola",
            instructions="Responde breve",
            model="test-model",
        )
        adapter.append_turn(conversation_id, "Pregunta", "Respuesta")
        adapter.delete(conversation_id)

        self.assertEqual("conv_1", conversation_id)
        self.assertEqual("Respuesta persistente", answer)
        self.assertEqual("create", calls[0][0])
        self.assertEqual("response", calls[1][0])
        self.assertEqual("conv_1", calls[1][1]["conversation"])
        self.assertEqual("items.create", calls[2][0])
        self.assertEqual("delete", calls[3][0])


if __name__ == "__main__":
    unittest.main()
