import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


OPENAI_OFFICIAL_BASE_URL = "https://api.openai.com/v1"


def load_project_environment() -> None:
    """Load the same user-scoped environment files as the Teams host."""
    load_dotenv()
    project_root = Path(__file__).resolve().parent.parent
    env_name = os.environ.get("TEAMSFX_ENV", "local")
    for candidate in (
        project_root / "env" / ".env.local.user",
        project_root / "env" / f".env.{env_name}.user",
    ):
        if candidate.exists():
            # User-scoped settings must supersede empty or development defaults
            # from the repository-level .env file.
            load_dotenv(candidate, override=True)


class Config:
    """Runtime configuration for Libras."""

    def __init__(self, env):
        self.port = int(env.get("PORT", 3978))
        self.environment = env.get("LIBRAS_ENV", env.get("TEAMSFX_ENV", "local")).strip().lower()
        # A deployment-supplied, non-secret identifier. It lets Teams checks
        # prove which backend revision answered without exposing environment
        # data or a commit URL.
        self.runtime_revision = (
            env.get("LIBRAS_RUNTIME_REVISION", "unversioned").strip() or "unversioned"
        )
        self.require_azure_search = env.get(
            "REQUIRE_AZURE_SEARCH", "true" if self.environment == "production" else "false"
        ).lower() == "true"
        self.use_azure_search_in_local = (
            env.get("USE_AZURE_SEARCH_IN_LOCAL", "false").lower() == "true"
        )
        self.allow_local_document_fallback = (
            self.environment != "production"
            and env.get("ALLOW_LOCAL_DOCUMENT_FALLBACK", "true").lower() == "true"
        )
        self.openai_api_key = env.get("OPENAI_API_KEY") or env.get("SECRET_OPENAI_API_KEY", "")
        self.openai_model_name = env.get("OPENAI_MODEL", "gpt-4o")
        self.openai_base_url = env.get("OPENAI_BASE_URL", "").strip().rstrip("/")
        self.openai_intent_model_name = env.get(
            "OPENAI_INTENT_MODEL", "gpt-4o-mini"
        ).strip()
        self.use_llm_intent_classifier = env.get(
            "USE_LLM_INTENT_CLASSIFIER", "true"
        ).lower() == "true"
        # Disabled by default so existing Teams deployments keep their current
        # behaviour until the guard has been observed and explicitly enabled.
        self.use_context_guard = env.get("USE_CONTEXT_GUARD", "false").lower() == "true"
        self.context_guard_model_name = env.get(
            "CONTEXT_GUARD_MODEL", self.openai_intent_model_name
        ).strip()
        configured_guard_mode = env.get("CONTEXT_GUARD_MODE", "observe").strip().lower()
        self.context_guard_mode = (
            configured_guard_mode if configured_guard_mode in {"observe", "enforce"} else "observe"
        )
        self.context_guard_timeout_seconds = float(
            env.get("CONTEXT_GUARD_TIMEOUT_SECONDS", "2")
        )
        configured_failure_policy = env.get(
            "CONTEXT_GUARD_FAILURE_POLICY", "block"
        ).strip().lower()
        self.context_guard_failure_policy = (
            configured_failure_policy
            if configured_failure_policy in {"allow", "block"}
            else "block"
        )
        self.openai_embedding_model = env.get(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
        ).strip()
        self.openai_embedding_dimensions = int(
            env.get("OPENAI_EMBEDDING_DIMENSIONS", "1536")
        )
        self.retrieval_timeout_seconds = float(
            env.get("RETRIEVAL_TIMEOUT_SECONDS", "12")
        )
        # Azure AI Search may finish shortly after the first budget expires
        # when the index is cold or the request needs several bounded passes.
        # Keep a small grace window so a late, valid result is not converted
        # into a false "sin evidencia" response.
        self.retrieval_grace_seconds = max(
            0.0, float(env.get("RETRIEVAL_GRACE_SECONDS", "8"))
        )
        configured_retrieval_strategy = env.get("RETRIEVAL_STRATEGY", "legacy").strip().lower()
        self.retrieval_strategy = (
            configured_retrieval_strategy
            if configured_retrieval_strategy in {"legacy", "v2"}
            else "legacy"
        )
        # Lets the separate ingestion job enrich reviewed metadata while the
        # chat still serves the reversible legacy retrieval policy. It is off
        # by default so ordinary legacy refreshes remain schema-compatible.
        self.index_quality_metadata_enabled = env.get(
            "INDEX_QUALITY_METADATA_ENABLED", "false"
        ).lower() == "true"
        self.use_llm_evidence_verifier = env.get(
            "USE_LLM_EVIDENCE_VERIFIER", "false"
        ).lower() == "true"
        self.evidence_verifier_model_name = env.get(
            "EVIDENCE_VERIFIER_MODEL", self.openai_intent_model_name
        ).strip()
        self.classification_timeout_seconds = float(
            env.get("CLASSIFICATION_TIMEOUT_SECONDS", "12")
        )
        self.intent_timeout_seconds = float(env.get("INTENT_TIMEOUT_SECONDS", "3"))
        self.conversation_timeout_seconds = float(
            env.get("CONVERSATION_TIMEOUT_SECONDS", "4")
        )
        self.use_ephemeral_thread_context = env.get(
            "USE_EPHEMERAL_THREAD_CONTEXT", "true"
        ).lower() == "true"
        self.thread_context_ttl_seconds = float(
            env.get("THREAD_CONTEXT_TTL_SECONDS", "1800")
        )
        self.thread_context_max_conversations = int(
            env.get("THREAD_CONTEXT_MAX_CONVERSATIONS", "1000")
        )
        self.use_friendly_links = env.get("USE_FRIENDLY_LINKS", "true").lower() == "true"
        self.use_pdf_page_links = env.get("USE_PDF_PAGE_LINKS", "true").lower() == "true"
        self.use_guided_start = env.get("USE_GUIDED_START", "true").lower() == "true"
        self.use_slash_commands = env.get("USE_SLASH_COMMANDS", "true").lower() == "true"
        self.use_openai_conversations = env.get(
            "USE_OPENAI_CONVERSATIONS", "false"
        ).lower() == "true"
        self.conversation_mapping_table = env.get(
            "CONVERSATION_MAPPING_TABLE", "librasconversationmap"
        ).strip()
        self.azure_storage_table_url = env.get(
            "AZURE_STORAGE_TABLE_URL", ""
        ).strip().rstrip("/")
        self.azure_storage_connection_string = env.get(
            "AZURE_STORAGE_CONNECTION_STRING", ""
        ).strip()
        self.conversation_mapping_timeout_seconds = float(
            env.get("CONVERSATION_MAPPING_TIMEOUT_SECONDS", "5")
        )
        self.azure_search_endpoint = env.get("AZURE_SEARCH_ENDPOINT", "").rstrip("/")
        self.azure_search_index_name = env.get("AZURE_SEARCH_INDEX_NAME", "libras-docs").strip()
        self.azure_search_api_key = env.get("AZURE_SEARCH_API_KEY", "").strip()
        self.azure_search_use_entra_id = env.get("AZURE_SEARCH_USE_ENTRA_ID", "false").lower() == "true"
        self.azure_search_semantic_configuration = env.get(
            "AZURE_SEARCH_SEMANTIC_CONFIGURATION", "default"
        ).strip()
        self.azure_search_use_semantic = env.get("AZURE_SEARCH_USE_SEMANTIC", "false").lower() == "true"
        self.sharepoint_tenant_id = env.get("SHAREPOINT_TENANT_ID", "").strip()
        self.sharepoint_client_id = env.get("SHAREPOINT_CLIENT_ID", "").strip()
        self.sharepoint_auth_mode = env.get("SHAREPOINT_AUTH_MODE", "delegated").strip().lower()
        self.sharepoint_client_secret = (
            env.get("SHAREPOINT_CLIENT_SECRET")
            or env.get("SECRET_SHAREPOINT_CLIENT_SECRET", "")
        ).strip()
        self.sharepoint_site_id = env.get("SHAREPOINT_SITE_ID", "").strip()
        # Optional SharePoint folder content type used to construct the
        # browser's native AllItems link for related solution files.
        self.sharepoint_folder_ctid = env.get("SHAREPOINT_FOLDER_CTID", "").strip()
        self.sharepoint_drive_id = env.get("SHAREPOINT_DRIVE_ID", "").strip()
        configured_drives = env.get("SHAREPOINT_DRIVE_IDS", "")
        self.sharepoint_drive_ids = tuple(
            drive.strip()
            for drive in configured_drives.replace(";", ",").split(",")
            if drive.strip()
        ) or ((self.sharepoint_drive_id,) if self.sharepoint_drive_id else ())
        self.sharepoint_folder_path = env.get("SHAREPOINT_FOLDER_PATH", "").strip("/")
        configured_paths = env.get("SHAREPOINT_FOLDER_PATHS", "")
        raw_paths = [path.strip() for path in configured_paths.replace(";", ",").split(",")]
        self.sharepoint_folder_paths = (
            tuple("" if path in {"", "/", "."} else path.strip("/") for path in raw_paths)
            if configured_paths
            else ((self.sharepoint_folder_path,) if self.sharepoint_folder_path else ())
        )
        configured_source_labels = env.get("LIBRAS_SHAREPOINT_SOURCE_LABELS", "")
        self.sharepoint_source_labels = tuple(
            label.strip()
            for label in configured_source_labels.replace(";", ",").split(",")
            if label.strip()
        )
        self.sharepoint_sources = (
            tuple(zip(self.sharepoint_folder_paths, self.sharepoint_drive_ids))
            if len(self.sharepoint_folder_paths) == len(self.sharepoint_drive_ids)
            else ()
        )
        self.bot_name = "Libras"
        self.bot_role = "Asistente de Base de Conocimiento y Resolucion de Errores"
        self.response_language = "es"

    @property
    def azure_search_configured(self) -> bool:
        """Azure AI Search needs an endpoint, index and a query/admin key."""
        return bool(
            self.azure_search_endpoint
            and self.azure_search_index_name
            and (self.azure_search_api_key or self.azure_search_use_entra_id)
        )

    @property
    def azure_search_enabled(self) -> bool:
        """Keep local Markdown tests independent from pending Azure permissions."""
        return self.azure_search_configured and (
            self.environment == "production" or self.use_azure_search_in_local
        )

    @property
    def model_endpoint_configured(self) -> bool:
        """Avoid remote model calls when a custom endpoint is malformed."""
        if not self.openai_api_key:
            return False
        if not self.openai_base_url:
            return True
        parsed = urlparse(self.openai_base_url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    @property
    def resolved_openai_base_url(self) -> str:
        """Use the official endpoint when no compatible provider is configured."""
        return self.openai_base_url or OPENAI_OFFICIAL_BASE_URL

    @property
    def openai_conversations_supported(self) -> bool:
        """Conversations requires the official OpenAI API endpoint."""
        return self.resolved_openai_base_url.rstrip("/") == OPENAI_OFFICIAL_BASE_URL

    @property
    def sharepoint_configured(self) -> bool:
        """Report whether the selected SharePoint authentication mode is usable."""
        if self.sharepoint_auth_mode == "application":
            return self.sharepoint_application_configured
        return bool(
            self.sharepoint_tenant_id
            and self.sharepoint_client_id
        )

    @property
    def sharepoint_application_configured(self) -> bool:
        """Production sync requires an explicit approved SharePoint location."""
        return bool(
            self.sharepoint_tenant_id
            and self.sharepoint_client_id
            and self.sharepoint_client_secret
            and self.sharepoint_site_id
            and self.sharepoint_drive_id
            and self.sharepoint_sources
            and len(self.sharepoint_sources) == len(self.sharepoint_folder_paths)
            and len(self.sharepoint_sources) == len(self.sharepoint_drive_ids)
        )
