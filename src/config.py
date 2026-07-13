class Config:
    """Runtime configuration for Chat-Salvador."""

    def __init__(self, env):
        self.port = int(env.get("PORT", 3978))
        self.openai_api_key = env.get("OPENAI_API_KEY") or env["SECRET_OPENAI_API_KEY"]
        self.openai_model_name = env.get("OPENAI_MODEL", "gpt-4o")
        self.openai_vector_store_id = env.get("OPENAI_VECTOR_STORE_ID", "").strip()
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
