"""Natural, bounded responses for non-documentary conversation turns."""

from __future__ import annotations

from intent import IntentResult


CONVERSATION_PROMPT = """
Eres Libras, asistente interno de documentación técnica.
Responde en español natural, cordial y breve (máximo dos oraciones).
Solo atiendes saludos, solicitudes de orientación o mensajes que aún no tienen
suficiente contexto técnico. No afirmes causas, versiones, procedimientos,
estados ni soluciones técnicas; no inventes documentación ni cites fuentes.

Según la intención indicada:
- saludo: saluda y ofrece ayuda para consultar documentación.
- ayuda: explica qué datos debe aportar el usuario.
- reporte_error o consulta_ambigua: solicita producto o módulo, versión,
  mensaje exacto de error y pasos para reproducirlo.
""".strip()


def generate_conversational_response(
    user_message: str,
    intent: IntentResult,
    client,
    model: str,
) -> str | None:
    """Generate a safe conversational response without documentary claims."""
    response = client.chat.completions.create(
        model=model,
        temperature=0.3,
        max_tokens=120,
        messages=[
            {"role": "system", "content": CONVERSATION_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Intención: {intent.name}. "
                    f"Requiere contexto: {intent.requires_context}.\n"
                    f"Mensaje: {user_message}"
                ),
            },
        ],
    )
    content = (response.choices[0].message.content or "").strip()
    return content or None
