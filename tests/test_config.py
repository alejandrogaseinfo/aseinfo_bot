import unittest

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config import Config


class ConfigTests(unittest.TestCase):
    def test_openai_base_url_is_optional_and_normalized(self):
        config = Config({"OPENAI_BASE_URL": "http://127.0.0.1:11434/v1/"})

        self.assertEqual("http://127.0.0.1:11434/v1", config.openai_base_url)
        self.assertEqual("", config.openai_api_key)

    def test_empty_openai_base_url_resolves_to_the_official_endpoint(self):
        config = Config({"OPENAI_API_KEY": "test-key", "OPENAI_BASE_URL": ""})

        self.assertEqual("https://api.openai.com/v1", config.resolved_openai_base_url)

    def test_embedding_configuration_has_safe_defaults(self):
        config = Config({})

        self.assertEqual("text-embedding-3-small", config.openai_embedding_model)
        self.assertEqual(1536, config.openai_embedding_dimensions)
        self.assertEqual(12, config.retrieval_timeout_seconds)
        self.assertEqual(12, config.classification_timeout_seconds)

    def test_model_endpoint_requires_http_url_when_custom_endpoint_is_set(self):
        invalid_config = Config(
            {"OPENAI_API_KEY": "test-key", "OPENAI_BASE_URL": "localhost:11434/v1"}
        )
        valid_config = Config(
            {"OPENAI_API_KEY": "test-key", "OPENAI_BASE_URL": "http://127.0.0.1:11434/v1"}
        )

        self.assertFalse(invalid_config.model_endpoint_configured)
        self.assertTrue(valid_config.model_endpoint_configured)

    def test_application_sharepoint_mode_requires_an_explicit_approved_location(self):
        config = Config(
            {
                "SHAREPOINT_AUTH_MODE": "application",
                "SHAREPOINT_TENANT_ID": "tenant",
                "SHAREPOINT_CLIENT_ID": "client",
                "SHAREPOINT_CLIENT_SECRET": "secret",
            }
        )

        self.assertFalse(config.sharepoint_configured)
        self.assertFalse(config.sharepoint_application_configured)

    def test_local_document_fallback_is_disabled_in_production(self):
        local_config = Config({"LIBRAS_ENV": "local"})
        production_config = Config(
            {
                "LIBRAS_ENV": "production",
                "ALLOW_LOCAL_DOCUMENT_FALLBACK": "true",
            }
        )

        self.assertTrue(local_config.allow_local_document_fallback)
        self.assertFalse(production_config.allow_local_document_fallback)


if __name__ == "__main__":
    unittest.main()
