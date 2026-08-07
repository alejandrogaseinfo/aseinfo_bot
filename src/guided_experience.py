"""Closed, deterministic guided actions for the first Teams message."""

from __future__ import annotations

from microsoft_agents.activity import Activity, ActivityTypes, Attachment


GUIDED_ACTIONS = {
    "version": "Consultar versión",
    "procedure": "Consultar procedimiento",
    "update": "Revisar actualización",
    "error": "Reportar un error",
    "help": "Ayuda",
}

GUIDED_PROMPTS = {
    "version": "Perfecto. Indícame el producto o módulo y la versión que deseas consultar.",
    "procedure": "Perfecto. Indícame el producto o módulo, la versión y el procedimiento que necesitas.",
    "update": "Perfecto. Indícame el producto o módulo, la versión y el componente de la actualización que deseas revisar.",
    "error": "Perfecto. Indícame el producto o módulo, la versión, el mensaje exacto de error y los pasos que lo provocan.",
    "help": "Puedo consultar documentación técnica autorizada. Indica producto o módulo, versión y la pregunta que deseas resolver.",
}

TOPIC_HINTS = {
    "version": "consulta de versión",
    "procedure": "consulta de procedimiento",
    "update": "consulta de actualización",
    "error": "reporte de error técnico",
    "help": "orientación para consultar documentación",
}

COMMAND_ACTIONS = {
    "ayuda": "help",
    "version": "version",
    "procedimiento": "procedure",
    "actualizacion": "update",
    "actualización": "update",
    "consultar_documentacion": "help",
    "consultar_procedimiento": "procedure",
    "consultar_actualizacion": "update",
    "consultar_actualización": "update",
}


def command_from_text(text: str) -> tuple[str, str] | None:
    """Parse a slash command and return (action, optional remaining text)."""
    parts = (text or "").strip().split(maxsplit=1)
    if not parts or not parts[0].startswith("/"):
        return None
    command = parts[0][1:].strip().lower()
    if command == "nuevo":
        return "new", parts[1] if len(parts) > 1 else ""
    action = COMMAND_ACTIONS.get(command)
    if not action:
        return None
    return action, parts[1] if len(parts) > 1 else ""


def guided_action_from_activity(activity) -> str | None:
    """Return only a known action from an Adaptive Card submit payload."""
    value = getattr(activity, "value", None)
    if not isinstance(value, dict):
        return None
    action = value.get("libras_action")
    return action if action in GUIDED_ACTIONS else None


def guided_prompt(action: str) -> str:
    return GUIDED_PROMPTS[action]


def topic_hint(action: str) -> str:
    return TOPIC_HINTS[action]


def build_welcome_activity() -> Activity:
    """Create a Teams-compatible card with a plain-text fallback."""
    actions = [
        {
            "type": "Action.Submit",
            "title": title,
            "data": {"libras_action": action},
        }
        for action, title in GUIDED_ACTIONS.items()
    ]
    card = {
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": "¿Qué deseas hacer hoy?",
                "weight": "Bolder",
                "size": "Medium",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": "Elige una opción o escribe directamente tu pregunta.",
                "wrap": True,
            },
        ],
        "actions": actions,
    }
    return Activity(
        type=ActivityTypes.message,
        text="¿Qué deseas hacer hoy? Elige una opción o escribe directamente tu pregunta.",
        attachments=[
            Attachment(
                contentType="application/vnd.microsoft.card.adaptive",
                content=card,
            )
        ],
    )
