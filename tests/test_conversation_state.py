import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from conversation_state import ConversationStateStore


class ConversationStateTests(unittest.TestCase):
    def test_keeps_documentary_context_across_intermediate_turn(self):
        store = ConversationStateStore(ttl_seconds=60, max_conversations=10)
        store.record_response("chat-1", "respuesta con Fuente:", is_documentary=True)
        store.record_response("chat-1", "Hola, ¿en qué ayudo?", is_documentary=False)

        state = store.get("chat-1")
        self.assertEqual("respuesta con Fuente:", state.previous_documentary_response)

    def test_evicts_oldest_chat_when_capacity_is_reached(self):
        store = ConversationStateStore(ttl_seconds=60, max_conversations=1)
        store.record_response("chat-1", "respuesta", is_documentary=True)
        store.record_response("chat-2", "respuesta", is_documentary=True)

        self.assertIsNone(store.get("chat-1").previous_documentary_response)
        self.assertEqual("respuesta", store.get("chat-2").previous_documentary_response)

    def test_expiry_starts_a_new_empty_thread(self):
        store = ConversationStateStore(ttl_seconds=1, max_conversations=10)
        store.record_response("chat-1", "respuesta", is_documentary=True)

        with patch("conversation_state.monotonic", return_value=1000):
            store.record_response("chat-1", "respuesta", is_documentary=True)
        with patch("conversation_state.monotonic", return_value=1002.1):
            self.assertIsNone(store.get("chat-1").previous_documentary_response)

    def test_clear_forgets_only_requested_chat(self):
        store = ConversationStateStore(ttl_seconds=60, max_conversations=10)
        store.record_response("chat-1", "respuesta", is_documentary=True)
        store.record_response("chat-2", "respuesta", is_documentary=True)
        store.clear("chat-1")

        self.assertIsNone(store.get("chat-1").previous_documentary_response)
        self.assertEqual("respuesta", store.get("chat-2").previous_documentary_response)

    def test_topic_is_scoped_to_one_chat(self):
        store = ConversationStateStore(ttl_seconds=60, max_conversations=10)
        store.set_topic("chat-1", "consulta de versión")

        self.assertEqual("consulta de versión", store.get("chat-1").topic)
        self.assertIsNone(store.get("chat-2").topic)

    def test_keeps_only_structured_context_for_the_active_chat(self):
        store = ConversationStateStore(ttl_seconds=60, max_conversations=10)
        store.record_response(
            "chat-1",
            "Respuesta documental\n\nFuente: Readme 1.19.1.10.pdf",
            is_documentary=True,
            product="Evolution",
            version="1.19.1.10",
            query_type="actualización",
            source_label="Readme 1.19.1.10.pdf — Azure AI Search",
        )

        state = store.get("chat-1")
        self.assertEqual("Evolution", state.product)
        self.assertEqual("1.19.1.10", state.version)
        self.assertEqual("actualización", state.query_type)
        self.assertEqual("Readme 1.19.1.10.pdf — Azure AI Search", state.source_label)

    def test_named_new_product_drops_old_version_and_source(self):
        store = ConversationStateStore(ttl_seconds=60, max_conversations=10)
        store.record_response(
            "chat-1", "respuesta", is_documentary=True,
            product="Evolution", version="1.19.1.10", source_label="Readme anterior",
        )
        store.record_response("chat-1", "respuesta", is_documentary=False, product="OtroProducto")

        state = store.get("chat-1")
        self.assertEqual("OtroProducto", state.product)
        self.assertIsNone(state.version)
        self.assertIsNone(state.source_label)


if __name__ == "__main__":
    unittest.main()
