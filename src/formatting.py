from models import BotDecision


def _source_label(decision: BotDecision) -> str:
    source_types = {source.tipo for source in decision.fuentes}
    if source_types.issubset({"azure_ai_search", "sharepoint"}):
        return "Azure AI Search"
    if source_types == {"documento"}:
        return "Base documental local"
    return "Fuentes documentales"


def format_user_response(decision: BotDecision, config=None) -> str:
    if decision.estado == "sin_evidencia" or not decision.fuentes:
        return decision.resumen

    source_titles = list(dict.fromkeys(source.titulo for source in decision.fuentes))
    source_label = "Fuente" if len(source_titles) == 1 else "Fuentes"
    return f"{decision.resumen}\n\n{source_label}: {' | '.join(source_titles)} — {_source_label(decision)}"
