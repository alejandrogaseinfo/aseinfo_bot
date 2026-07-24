"""Small, bounded LLM router for the first user message in a conversation."""

from __future__ import annotations

import json
from dataclasses import dataclass


VALID_INTENTS = {
    "saludo",
    "ayuda",
    "consulta_documental",
    "reporte_error",
    "consulta_ambigua",
}

INTENT_PROMPT = """
Clasifique el primer mensaje de un usuario de Libras en JSON válido.
Use solo una intención: saludo, ayuda, consulta_documental, reporte_error o consulta_ambigua.
Marque requiere_contexto=true solo si faltan producto o módulo, versión, mensaje de error
o pasos para poder buscar evidencia técnica de manera segura.

Reglas:
- saludo: saludo o conversación social breve.
- ayuda: solicita orientación sobre cómo usar Libras o formular una consulta.
- consulta_documental: pregunta concreta sobre procedimiento, manual, hotfix o actualización.
- reporte_error: describe un error concreto; requiere_contexto depende de sus detalles.
- consulta_ambigua: no permite identificar qué se debe buscar.
Ejemplo: "hola me podes orientar" es ayuda, no consulta_ambigua.
No responda la pregunta ni invente detalles. Devuelva únicamente JSON.
""".strip()


@dataclass(frozen=True)
class IntentResult:
    name: str
    requires_context: bool


def classify_intent(user_message: str, client, model: str) -> IntentResult | None:
    """Return a whitelisted intent, or None when the provider response is unusable."""
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": INTENT_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    content = response.choices[0].message.content or "{}"
    payload = json.loads(content)
    name = payload.get("intencion") or payload.get("intent")
    if name not in VALID_INTENTS:
        return None
    return IntentResult(name=name, requires_context=bool(payload.get("requiere_contexto", False)))
