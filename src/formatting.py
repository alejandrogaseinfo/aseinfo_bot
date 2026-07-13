from models import BotDecision


SOURCE_LABELS = {
    "setup": "Setup / Hotfix",
    "clickup": "ClickUp",
    "jira": "Jira",
    "vector_store": "Vector Store",
    "documento": "Base documental local",
}


def _research_route(decision: BotDecision, config=None) -> str:
    source_types = {source.tipo for source in decision.fuentes}
    route_lines = []

    if "setup" in source_types:
        route_lines.append("Setup / Hotfix: evidencia primaria encontrada")
    elif "vector_store" in source_types:
        route_lines.append("Setup / Hotfix y Vector Store: evidencia encontrada")
    elif getattr(config, "openai_vector_store_id", ""):
        route_lines.append("Setup / Hotfix y Vector Store: consultados sin coincidencias")

    if "clickup" in source_types or getattr(config, "clickup_api_token", ""):
        clickup_status = "evidencia encontrada" if "clickup" in source_types else "consultado sin coincidencias"
        route_lines.append(f"ClickUp: {clickup_status}")

    if "jira" in source_types:
        route_lines.append("Jira histórico: evidencia encontrada")
    elif getattr(config, "jira_api_token", ""):
        route_lines.append("Jira histórico: consultado sin coincidencias")
    else:
        route_lines.append("Jira histórico: pendiente de acceso")

    if "documento" in source_types:
        route_lines.append("Base documental local: evidencia encontrada")
    else:
        route_lines.append("Base documental local: disponible como respaldo")

    return "\n".join(f"{index}. {line}" for index, line in enumerate(route_lines, start=1))


def _format_location(location: str) -> str:
    if location.startswith(("http://", "https://")):
        return f"[Abrir fuente]({location})"
    return location


def format_user_response(decision: BotDecision, config=None) -> str:
    evidence_lines = []
    for index, source in enumerate(decision.fuentes, start=1):
        source_label = SOURCE_LABELS.get(source.tipo, source.tipo)
        evidence_lines.append(
            "\n".join(
                [
                    f"{index}. {source.titulo} ({source_label})",
                    f"   {source.fragmento}",
                    f"   Ubicacion: {_format_location(source.ubicacion)}",
                ]
            )
        )

    evidence_block = (
        "\n\n".join(evidence_lines)
        if evidence_lines
        else "No se encontro evidencia suficiente en las fuentes consultadas."
    )
    escalation_line = (
        "Si el problema persiste, escale el caso al equipo de desarrollo."
        if decision.requiere_escalamiento
        else "No se requiere escalamiento inmediato con la evidencia disponible."
    )

    return (
        "Estado\n"
        f"{decision.estado}\n\n"
        "Confianza\n"
        f"{decision.confianza}\n\n"
        "Resumen\n"
        f"{decision.resumen}\n\n"
        "Ruta de investigacion\n"
        f"{_research_route(decision, config)}\n\n"
        "Evidencia\n"
        f"{evidence_block}\n\n"
        "Siguiente accion\n"
        f"{decision.siguiente_accion}\n\n"
        "Escalamiento\n"
        f"{escalation_line}"
    )
