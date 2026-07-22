import os
from pathlib import Path

from dotenv import load_dotenv


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
            load_dotenv(candidate, override=False)


class Config:
    """Runtime configuration for Chat-Salvador."""

    def __init__(self, env):
        self.port = int(env.get("PORT", 3978))
        self.openai_api_key = env.get("OPENAI_API_KEY") or env.get("SECRET_OPENAI_API_KEY", "")
        self.openai_model_name = env.get("OPENAI_MODEL", "gpt-4o")
        self.openai_base_url = env.get("OPENAI_BASE_URL", "").strip().rstrip("/")
        self.openai_embedding_model = env.get(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
        ).strip()
        self.openai_embedding_dimensions = int(
            env.get("OPENAI_EMBEDDING_DIMENSIONS", "1536")
        )
        self.retrieval_timeout_seconds = float(
            env.get("RETRIEVAL_TIMEOUT_SECONDS", "12")
        )
        self.classification_timeout_seconds = float(
            env.get("CLASSIFICATION_TIMEOUT_SECONDS", "12")
        )
        self.azure_search_endpoint = env.get("AZURE_SEARCH_ENDPOINT", "").rstrip("/")
        self.azure_search_index_name = env.get("AZURE_SEARCH_INDEX_NAME", "chat-salvador-docs").strip()
        self.azure_search_api_key = env.get("AZURE_SEARCH_API_KEY", "").strip()
        self.azure_search_use_entra_id = env.get("AZURE_SEARCH_USE_ENTRA_ID", "false").lower() == "true"
        self.azure_search_semantic_configuration = env.get(
            "AZURE_SEARCH_SEMANTIC_CONFIGURATION", "default"
        ).strip()
        self.azure_search_use_semantic = env.get("AZURE_SEARCH_USE_SEMANTIC", "false").lower() == "true"
        self.sharepoint_tenant_id = env.get("SHAREPOINT_TENANT_ID", "").strip()
        self.sharepoint_client_id = env.get("SHAREPOINT_CLIENT_ID", "").strip()
        self.sharepoint_site_id = env.get("SHAREPOINT_SITE_ID", "").strip()
        self.sharepoint_drive_id = env.get("SHAREPOINT_DRIVE_ID", "").strip()
        self.sharepoint_folder_path = env.get("SHAREPOINT_FOLDER_PATH", "").strip("/")
        self.clickup_api_token = env.get("CLICKUP_API_TOKEN", "").strip()
        self.clickup_workspace_id = env.get("CLICKUP_WORKSPACE_ID", "").strip()
        self.clickup_list_id = env.get("CLICKUP_LIST_ID", "").strip()
        self.jira_domain = env.get("JIRA_DOMAIN", "").strip() # ej. tu-dominio.atlassian.net
        self.jira_email = env.get("JIRA_EMAIL", "").strip()
        self.jira_api_token = env.get("JIRA_API_TOKEN", "").strip()
        self.jira_project_key = env.get("JIRA_PROJECT_KEY", "").strip() # Opcional: para filtrar por proyecto
        self.bot_name = "Chat-Salvador"
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
    def sharepoint_configured(self) -> bool:
        """SharePoint sync deliberately uses delegated (user) authentication."""
        return bool(
            self.sharepoint_tenant_id
            and self.sharepoint_client_id
        )
