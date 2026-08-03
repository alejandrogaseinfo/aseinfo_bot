import json
import re

from document_index import has_requested_action_coverage, tokenize
from models import BotDecision, EvidenceSource


SYSTEM_PROMPT = """
Usted es Libras, un asistente formal del equipo de desarrollo.
Responde siempre en espanol, con tono tecnico y prudente.
No invente tickets, estados, causas, fechas, versiones ni soluciones.
Clasifique cada caso en uno de estos estados:
- resuelto
- en_progreso
- similar_del_pasado
- sin_evidencia

Debe devolver un JSON valido con esta estructura exacta:
{
  "estado": "resuelto | en_progreso | similar_del_pasado | sin_evidencia",
  "confianza": "alta | media | baja",
  "resumen": "string",
  "siguiente_accion": "string",
  "requiere_escalamiento": true
}

Reglas:
- Para preguntas factuales sobre políticas, procedimientos o manuales, use "resuelto" cuando la evidencia responda directamente a la pregunta. En ese caso, el campo "resumen" debe responder la pregunta con los valores, condiciones o fórmulas explícitamente documentados.
- Use "resuelto" para incidentes solo si la evidencia muestra una solucion o instruccion documentada.
- Use "en_progreso" solo si la evidencia muestra seguimiento activo.
- Use "similar_del_pasado" solo si la evidencia es historica o analogica.
- Use "sin_evidencia" si la evidencia es insuficiente o inexistente.
- Si faltan pruebas solidas, marque requiere_escalamiento=true.
""".strip()
VERSION_PATTERN = re.compile(r"(?<![\d.])(\d+(?:\.\d+){2,})(?!\d|\.\d)")


def _combined_evidence_text(evidence: list[EvidenceSource]) -> str:
    return " ".join(
        f"{source.titulo} {source.fragmento} {source.ubicacion}".lower()
        for source in evidence
    )


def _is_direct_document_question(user_message: str, evidence: list[EvidenceSource]) -> bool:
    """Identify a factual question directly covered by a retrieved document.

    This prevents a policy/manual from being treated as a historical incident
    merely because it is not a bug fix. It intentionally does not require the
    user to say "manual" or "política": normal users ask the factual question
    directly.
    """
    query_tokens = set(tokenize(user_message or ""))
    if not query_tokens:
        return False

    normalized_question = (user_message or "").strip().lower()
    question_markers = (
        "?",
        "cuál",
        "cual",
        "cómo",
        "como",
        "qué",
        "que ",
        "cuánt",
        "cuant",
        "dónde",
        "donde",
    )
    if not any(marker in normalized_question for marker in question_markers):
        return False

    for source in evidence:
        if source.tipo not in {"sharepoint", "azure_ai_search", "documento", "setup"}:
            continue
        source_tokens = set(tokenize(f"{source.titulo} {source.fragmento}"))
        required_overlap = 2 if len(query_tokens) <= 4 else 3
        if len(query_tokens.intersection(source_tokens)) >= required_overlap:
            return True
    return False


def _requested_version(user_message: str) -> str | None:
    match = VERSION_PATTERN.search(user_message or "")
    return match.group(1) if match else None


def has_explicit_version_request(user_message: str) -> bool:
    return _requested_version(user_message) is not None


def _version_document_summary(version: str, evidence: list[EvidenceSource]) -> str:
    """Answer a version lookup from its cited text without inventing changes."""
    details = " ".join(source.fragmento.strip() for source in evidence[:2] if source.fragmento.strip())
    details = " ".join(details.split())
    if not details:
        return f"Se encontró documentación para Evolution {version}, pero el fragmento recuperado no contiene detalles suficientes."
    if len(details) > 900:
        details = f"{details[:900].rsplit(' ', 1)[0]}..."
    return f"Para Evolution {version}, la documentación indica: {details}"


def _version_answer_is_none(user_message: str, evidence: list[EvidenceSource]) -> bool:
    """Keep an explicit 'Ninguno' result concise instead of expanding a heading."""
    asks_for_software_requirements = bool(
        re.search(r"nuevos?\s+requisitos?\s+de\s+software", user_message or "", re.IGNORECASE)
    )
    if not asks_for_software_requirements:
        return False
    return any(
        re.search(
            r"nuevos?\s+requisitos?\s+de\s+software.{0,120}\bninguno\b",
            source.fragmento,
            re.IGNORECASE | re.DOTALL,
        )
        for source in evidence
    )


def classify_case_by_rules(
    user_message: str,
    evidence: list[EvidenceSource],
) -> BotDecision:
    query = (user_message or "").lower()
    evidence_text = _combined_evidence_text(evidence)

    if not evidence:
        return BotDecision(
            estado="sin_evidencia",
            confianza="baja",
            resumen="No se encontro evidencia suficiente en las fuentes documentales consultadas.",
            fuentes=[],
            siguiente_accion="Escale el caso al equipo de desarrollo para una revision manual.",
            requiere_escalamiento=True,
        )

    if not any(
        has_requested_action_coverage(
            user_message, f"{source.titulo} {source.fragmento}"
        )
        for source in evidence
    ):
        return BotDecision(
            estado="sin_evidencia",
            confianza="baja",
            resumen="No se encontro evidencia suficiente en las fuentes documentales consultadas.",
            fuentes=[],
            siguiente_accion="Escale el caso al equipo de desarrollo para una revision manual.",
            requiere_escalamiento=True,
        )

    requested_version = _requested_version(user_message)
    if requested_version:
        summary = (
            "Ninguno."
            if _version_answer_is_none(user_message, evidence)
            else _version_document_summary(requested_version, evidence)
        )
        return BotDecision(
            estado="resuelto",
            confianza="alta",
            resumen=summary,
            fuentes=evidence,
            siguiente_accion="Revise el Readme citado antes de aplicar los cambios de esa versión.",
            requiere_escalamiento=False,
        )

    if _is_direct_document_question(user_message, evidence):
        return BotDecision(
            estado="resuelto",
            confianza="alta",
            resumen=(
                "Se encontró documentación que responde directamente a la consulta. "
                "La respuesta se fundamenta en los fragmentos citados a continuación."
            ),
            fuentes=evidence,
            siguiente_accion="Revise el documento citado para validar el detalle aplicable a su caso.",
            requiere_escalamiento=False,
        )

    resolved_markers = [
        "advertencia",
        "antes de instalar",
        "ejecutar el script",
        "resolucion",
        "corrige",
        "correccion",
        "hotfix",
    ]
    in_progress_markers = [
        "seguimiento activo",
        "ticket activo",
        "reportado",
        "en progreso",
        "pendiente de confirmacion",
    ]
    historical_markers = [
        "historico",
        "antecedente",
        "referencia",
        "caso historico",
        "puede servir como antecedente",
    ]

    if any(marker in evidence_text for marker in resolved_markers):
        return BotDecision(
            estado="resuelto",
            confianza="alta",
            resumen="Se encontro documentacion que describe el problema y una accion concreta de correccion o validacion previa a la instalacion.",
            fuentes=evidence,
            siguiente_accion="Aplique la instruccion documentada indicada en la evidencia y repita la prueba antes de escalar el caso.",
            requiere_escalamiento=False,
        )

    if any(marker in evidence_text for marker in in_progress_markers):
        return BotDecision(
            estado="en_progreso",
            confianza="media",
            resumen="La evidencia indica que el caso ya fue reportado y tiene seguimiento activo.",
            fuentes=evidence,
            siguiente_accion="Valide si su caso coincide con la evidencia encontrada y de seguimiento al ticket activo.",
            requiere_escalamiento=False,
        )

    if any(marker in evidence_text for marker in historical_markers) or any(
        marker in query for marker in ["oracle", "similar", "antecedente", "pasado"]
    ):
        return BotDecision(
            estado="similar_del_pasado",
            confianza="media",
            resumen="No se identifico una resolucion actual confirmada, pero si antecedentes tecnicos que pueden orientar el analisis.",
            fuentes=evidence,
            siguiente_accion="Compare el contexto actual con el antecedente recuperado antes de asumir que se trata de la misma causa.",
            requiere_escalamiento=True,
        )

    return BotDecision(
        estado="sin_evidencia",
        confianza="baja",
        resumen="Se recupero informacion relacionada, pero no es suficiente para confirmar una resolucion o seguimiento activo con seguridad.",
        fuentes=evidence,
        siguiente_accion="Escale el caso al equipo de desarrollo si el problema persiste o si necesita confirmacion tecnica adicional.",
        requiere_escalamiento=True,
    )


def classify_case(
    user_message: str,
    evidence: list[EvidenceSource],
    client,
    model: str,
) -> BotDecision:
    evidence_lines = []
    for source in evidence:
        evidence_lines.append(
            f"- tipo: {source.tipo}; titulo: {source.titulo}; ubicacion: {source.ubicacion}; fragmento: {source.fragmento}"
        )

    evidence_block = "\n".join(evidence_lines) if evidence_lines else "- sin evidencia recuperada"

    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Consulta del usuario:\n{user_message}\n\n"
                    f"Evidencia recuperada:\n{evidence_block}\n\n"
                    "Clasifique el caso y resuma el siguiente paso."
                ),
            },
        ],
    )

    content = response.choices[0].message.content or "{}"
    payload = json.loads(content)

    estado = payload.get("estado", "sin_evidencia")
    confianza = payload.get("confianza", "baja")
    if estado == "sin_evidencia":
        confianza = "baja"

    return BotDecision(
        estado=estado,
        confianza=confianza,
        resumen=payload.get("resumen", "No fue posible clasificar el caso con confianza."),
        fuentes=evidence,
        siguiente_accion=payload.get(
            "siguiente_accion",
            "Escale el caso al equipo de desarrollo para revision manual.",
        ),
        requiere_escalamiento=payload.get("requiere_escalamiento", True),
    )
