import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from runtime_health import readiness_payload


class RuntimeHealthTests(unittest.TestCase):
    def test_local_mode_is_ready_with_a_model_and_without_azure_search(self):
        payload = readiness_payload(
            SimpleNamespace(
                environment="local",
                openai_api_key="",
                openai_base_url="http://127.0.0.1:11434/v1",
                azure_search_configured=False,
                require_azure_search=False,
            )
        )

        self.assertEqual("ready", payload["status"])
        self.assertFalse(payload["azure_search_configured"])
        self.assertEqual([], payload["missing"])

    def test_production_mode_requires_search_and_model(self):
        payload = readiness_payload(
            SimpleNamespace(
                environment="production",
                openai_api_key="",
                openai_base_url="",
                azure_search_configured=False,
                require_azure_search=True,
            )
        )

        self.assertEqual("not_ready", payload["status"])
        self.assertEqual(["model", "azure_ai_search"], payload["missing"])


if __name__ == "__main__":
    unittest.main()
