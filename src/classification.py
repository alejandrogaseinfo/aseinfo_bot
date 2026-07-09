import json

from models import BotDecision, EvidenceSource


SYSTEM_PROMPT = """
Usted es Chat-Salvador, un asistente formal del equipo de desarrollo.
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
- Use "resuelto" solo si la evidencia muestra una solucion o instruccion documentada.
- Use "en_progreso" solo si la evidencia muestra seguimiento activo.
- Use "similar_del_pasado" solo si la evidencia es historica o analogica.
- Use "sin_evidencia" si la evidencia es insuficiente o inexistente.
- Si faltan pruebas solidas, marque requiere_escalamiento=true.
""".strip()


def _combined_evidence_text(evidence: list[EvidenceSource]) -> str:
    return " ".join(
        f"{source.titulo} {source.fragmento} {source.ubicacion}".lower()
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

    return BotDecision(
        estado=payload.get("estado", "sin_evidencia"),
        confianza=payload.get("confianza", "baja"),
        resumen=payload.get("resumen", "No fue posible clasificar el caso con confianza."),
        fuentes=evidence,
        siguiente_accion=payload.get(
            "siguiente_accion",
            "Escale el caso al equipo de desarrollo para revision manual.",
        ),
        requiere_escalamiento=payload.get("requiere_escalamiento", True),
    )
