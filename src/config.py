class Config:
    """Runtime configuration for Chat-Salvador."""

    def __init__(self, env):
        self.port = int(env.get("PORT", 3978))
        self.openai_api_key = env.get("OPENAI_API_KEY") or env["SECRET_OPENAI_API_KEY"]
        self.openai_model_name = env.get("OPENAI_MODEL", "gpt-4o")
        self.openai_vector_store_id = env.get("OPENAI_VECTOR_STORE_ID", "").strip()
        self.bot_name = "Chat-Salvador"
        self.bot_role = "Asistente de Base de Conocimiento y Resolucion de Errores"
        self.response_language = "es"
