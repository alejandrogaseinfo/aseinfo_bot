import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from azure_search import _install_search_observer
from latency_observability import endpoint_host, error_code, request_hash


class LatencyObservabilityTests(unittest.TestCase):
    def test_metadata_does_not_expose_query_text(self):
        value = request_hash("consulta con token-secreto")

        self.assertEqual(16, len(value))
        self.assertNotIn("token", value)
        self.assertEqual("search.example.test", endpoint_host("https://search.example.test/index"))

    def test_error_code_contains_only_exception_type(self):
        self.assertEqual("RuntimeError", error_code(RuntimeError("secret detail")))

    def test_search_observer_records_sdk_retry_history_without_query(self):
        class FakeSearchClient:
            def _search_post(self, **kwargs):
                callback = kwargs["cls"]
                response = SimpleNamespace(context={"history": ["retry", "retry"]})
                return callback(response, {"results": []}, {})

        config = SimpleNamespace(azure_search_endpoint="https://srch.example.test")
        observed = _install_search_observer(
            FakeSearchClient(),
            "pregunta con token-secreto",
            config,
        )

        with self.assertLogs("chat_salvador", level="INFO") as captured:
            observed._search_post(body={"search": "pregunta con token-secreto"})

        output = "\n".join(captured.output)
        self.assertIn("azure_search_query_start", output)
        self.assertIn("azure_search_query_end", output)
        self.assertIn("retries=2", output)
        self.assertNotIn("token-secreto", output)
        self.assertNotIn("pregunta con", output)


if __name__ == "__main__":
    unittest.main()
