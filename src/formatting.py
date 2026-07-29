from models import BotDecision


def _source_label(decision: BotDecision) -> str:
    source_types = {source.tipo for source in decision.fuentes}
    if source_types.issubset({"azure_ai_search", "sharepoint"}):
        return "Azure AI Search"
    if source_types == {"documento"}:
        return "Base documental local"
    return "Fuentes documentales"


def _source_links(decision: BotDecision) -> list[str]:
    """Return the unique, user-verifiable document URLs from the evidence."""
    return list(
        dict.fromkeys(
            source.ubicacion
            for source in decision.fuentes
            if source.ubicacion.startswith(("https://", "http://"))
        )
    )


def format_user_response(decision: BotDecision, config=None) -> str:
    if decision.estado == "sin_evidencia" or not decision.fuentes:
        return decision.resumen

    source_titles = list(dict.fromkeys(source.titulo for source in decision.fuentes))
    source_label = "Fuente" if len(source_titles) == 1 else "Fuentes"
    response = (
        f"{decision.resumen}\n\n"
        f"{source_label}: {' | '.join(source_titles)} — {_source_label(decision)}"
    )
    source_links = _source_links(decision)
    if source_links:
        link_label = "Enlace" if len(source_links) == 1 else "Enlaces"
        response += f"\n{link_label}: {' | '.join(source_links)}"
    return response
