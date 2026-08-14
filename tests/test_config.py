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
        self.assertEqual(8, config.retrieval_grace_seconds)
        self.assertEqual(12, config.classification_timeout_seconds)
        self.assertEqual("unversioned", config.runtime_revision)

    def test_grounded_response_is_opt_in(self):
        disabled = Config({})
        enabled = Config({"USE_LLM_GROUNDED_RESPONSE": "true"})

        self.assertFalse(disabled.use_llm_grounded_response)
        self.assertTrue(enabled.use_llm_grounded_response)
        self.assertEqual("gpt-4o", enabled.grounded_response_model_name)

    def test_runtime_revision_uses_a_non_empty_deployment_value(self):
        config = Config({"LIBRAS_RUNTIME_REVISION": "20260806-rag-evidence"})

        self.assertEqual("20260806-rag-evidence", config.runtime_revision)

    def test_quality_metadata_refresh_is_opt_in_before_v2_promotion(self):
        self.assertFalse(Config({}).index_quality_metadata_enabled)
        self.assertTrue(
            Config({"INDEX_QUALITY_METADATA_ENABLED": "true"}).index_quality_metadata_enabled
        )

    def test_retrieval_grace_timeout_is_never_negative(self):
        config = Config({"RETRIEVAL_GRACE_SECONDS": "-2"})

        self.assertEqual(0, config.retrieval_grace_seconds)

    def test_context_guard_is_opt_in_and_defaults_to_observe(self):
        config = Config({})

        self.assertFalse(config.use_context_guard)
        self.assertEqual("gpt-4o-mini", config.context_guard_model_name)
        self.assertEqual("observe", config.context_guard_mode)
        self.assertEqual(2, config.context_guard_timeout_seconds)
        self.assertEqual("block", config.context_guard_failure_policy)

    def test_context_guard_normalizes_invalid_modes(self):
        config = Config(
            {
                "USE_CONTEXT_GUARD": "true",
                "CONTEXT_GUARD_MODE": "unexpected",
                "CONTEXT_GUARD_FAILURE_POLICY": "unexpected",
            }
        )

        self.assertTrue(config.use_context_guard)
        self.assertEqual("observe", config.context_guard_mode)
        self.assertEqual("block", config.context_guard_failure_policy)

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

    def test_sharepoint_source_labels_are_parsed_for_user_visible_scope(self):
        config = Config(
            {
                "LIBRAS_SHAREPOINT_SOURCE_LABELS": (
                    "ReadME Hotfixes; Documentos/SOLUCIONES, Manuales"
                )
            }
        )

        self.assertEqual(
            ("ReadME Hotfixes", "Documentos/SOLUCIONES", "Manuales"),
            config.sharepoint_source_labels,
        )

    def test_soluciones_is_an_explicit_approved_folder_for_documentos(self):
        config = Config(
            {
                "SHAREPOINT_DRIVE_IDS": "drive-documentos",
                "SHAREPOINT_FOLDER_PATHS": "SOLUCIONES",
            }
        )
        self.assertEqual(("SOLUCIONES",), config.sharepoint_folder_paths)
        self.assertEqual((("SOLUCIONES", "drive-documentos"),), config.sharepoint_sources)

    def test_production_evaluation_allowlist_keeps_approved_library_roots(self):
        config = Config(
            {
                "SHAREPOINT_DRIVE_IDS": "d1,d2,d3,d4",
                "SHAREPOINT_FOLDER_PATHS": ",SOLUCIONES,,",
            }
        )
        self.assertEqual(("", "SOLUCIONES", "", ""), config.sharepoint_folder_paths)
        self.assertEqual(4, len(config.sharepoint_sources))
        self.assertIn(("SOLUCIONES", "d2"), config.sharepoint_sources)

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
