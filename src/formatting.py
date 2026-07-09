from models import BotDecision


def format_user_response(decision: BotDecision) -> str:
    evidence_lines = []
    for index, source in enumerate(decision.fuentes, start=1):
        evidence_lines.append(
            "\n".join(
                [
                    f"{index}. {source.titulo} ({source.tipo})",
                    f"   {source.fragmento}",
                    f"   Archivo: {source.ubicacion}",
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
        "Evidencia\n"
        f"{evidence_block}\n\n"
        "Siguiente accion\n"
        f"{decision.siguiente_accion}\n\n"
        "Escalamiento\n"
        f"{escalation_line}"
    )
