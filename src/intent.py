"""Small, bounded LLM router for a user message in a conversation."""

from __future__ import annotations

import json
from dataclasses import dataclass


VALID_INTENTS = {
    "saludo",
    "ayuda",
    "consulta_documental",
    "reporte_error",
    "consulta_ambigua",
    "fuera_alcance",
}
VALID_CONVERSATION_PURPOSES = {
    "none",
    "saludo",
    "ayuda",
    "capacidad",
    "alcance",
    "aclaracion",
}

INTENT_PROMPT = """
Clasifique el mensaje de un usuario de Libras en JSON válido.
Use solo una intención: saludo, ayuda, consulta_documental, reporte_error,
consulta_ambigua o fuera_alcance.
Además devuelva proposito_conversacional con uno de estos valores: none, saludo,
ayuda, capacidad, alcance o aclaracion.
Marque requiere_contexto=true solo para un reporte de error o una consulta
realmente ambigua cuando falte información necesaria para buscar evidencia.
Una pregunta factual sobre políticas, pagos, planillas o documentos es
consulta_documental aunque no indique producto, módulo o versión.

Reglas:
- saludo: saludo o conversación social breve.
- ayuda: solicita orientación sobre cómo usar Libras o formular una consulta.
- consulta_documental: pregunta concreta sobre procedimiento, manual, hotfix o actualización.
- reporte_error: describe un error concreto; requiere_contexto depende de sus detalles.
- consulta_ambigua: no permite identificar qué se debe buscar.
- fuera_alcance: pregunta factual, recreativa o general que no busca información
  sobre la documentación técnica autorizada de Libras. Incluye preguntas sobre
  celebridades, deportes, política general, animales, recetas, noticias,
  entretenimiento o cualquier tema externo, aunque la pregunta sea clara.
  No intente responderla ni enviarla a recuperación documental.
Use capacidad si pregunta qué puede hacer Libras o cómo puede apoyar, incluso
con expresiones como "¿cómo me puedes apoyar?".
Use alcance si pregunta en qué bibliotecas, carpetas, fuentes o documentación
puede buscar, incluso con expresiones como "¿sobre qué carpetas puedes buscar?".
Use ayuda si necesita orientación para formular una consulta pero no pregunta
por capacidades ni alcance. También es ayuda si dice que no sabe cómo preguntar
o si pregunta qué información debe incluir al reportar un problema; en esos
casos requiere_contexto=false porque Libras debe explicar cómo formularlo.
Use aclaracion solo cuando se deba pedir más contexto para un error o consulta
ambigua. Siempre que requiere_contexto=true, proposito_conversacional debe ser
aclaracion.

Una frase como "necesito resolver un problema" o "tengo un inconveniente" sin
producto, versión, mensaje de error ni pasos es consulta_ambigua con
requiere_contexto=true y proposito_conversacional=aclaracion.

Ejemplos:
- "hola me podes orientar" => intencion=ayuda, proposito_conversacional=ayuda.
- "¿cómo me puedes apoyar?" => intencion=ayuda, proposito_conversacional=capacidad.
- "¿sobre qué carpetas puedes buscar?" => intencion=ayuda, proposito_conversacional=alcance.
- "No sé cómo preguntarte lo que necesito" => intencion=ayuda,
  proposito_conversacional=ayuda, requiere_contexto=false.
- "¿Qué información debo incluir para reportar un problema?" => intencion=ayuda,
  proposito_conversacional=ayuda, requiere_contexto=false.
- "Necesito resolver un problema" => intencion=consulta_ambigua,
  proposito_conversacional=aclaracion, requiere_contexto=true.
- "¿qué indica el Readme 1.19.1.10?" => intencion=consulta_documental,
  proposito_conversacional=none.
- "¿cuál es la edad de Messi?" => intencion=fuera_alcance,
  proposito_conversacional=none.
No responda la pregunta ni invente detalles. Devuelva únicamente JSON.
""".strip()


@dataclass(frozen=True)
class IntentResult:
    name: str
    requires_context: bool
    conversation_purpose: str = "none"


def _default_conversation_purpose(name: str, requires_context: bool) -> str:
    """Keep router compatibility when a provider omits the newer field."""
    if name == "saludo":
        return "saludo"
    if name == "ayuda":
        return "ayuda"
    if name in {"reporte_error", "consulta_ambigua"} and requires_context:
        return "aclaracion"
    return "none"


def classify_intent(user_message: str, client, model: str) -> IntentResult | None:
    """Return a whitelisted intent, or None when the provider response is unusable."""
    response = client.chat.completions.create(
        model=model,
        temperature=0,
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
    requires_context = bool(payload.get("requiere_contexto", False))
    purpose = (
        payload.get("proposito_conversacional")
        or payload.get("conversation_purpose")
        or _default_conversation_purpose(name, requires_context)
    )
    if purpose not in VALID_CONVERSATION_PURPOSES:
        return None

    # A request for clarification is an application action, not a detail the
    # model can vary. Normalize inconsistent but otherwise valid JSON so the
    # handler never produces an ambiguous conversational route.
    if name in {"reporte_error", "consulta_ambigua"} and requires_context:
        purpose = "aclaracion"
    elif name == "ayuda":
        requires_context = False
        if purpose in {"none", "aclaracion", "saludo"}:
            purpose = "ayuda"

    # Documentary routing must not be converted into a conversational shortcut
    # by an inconsistent model response. Conversely, capability and scope
    # requests are always conversational and are handled by the application.
    if name == "consulta_documental" and purpose != "none":
        return None
    if purpose in {"capacidad", "alcance"} and name != "ayuda":
        return None

    return IntentResult(
        name=name,
        requires_context=requires_context,
        conversation_purpose=purpose,
    )
