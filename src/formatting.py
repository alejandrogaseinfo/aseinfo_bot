from urllib.parse import quote, unquote, urlparse

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


def _sharepoint_folder_link(source_url: str, folder_ctid: str = "") -> str:
    """Build the native SharePoint folder view for a cited file.

    A solution can consist of an instruction file plus scripts or binaries in
    the same folder. The file link remains the evidence; this link lets the
    operator inspect the related artifacts without exposing an internal path.
    """
    parsed = urlparse(source_url)
    if not parsed.scheme.startswith("http") or not parsed.netloc.endswith("sharepoint.com"):
        return ""
    segments = [segment for segment in unquote(parsed.path).split("/") if segment]
    normalized = [segment.casefold() for segment in segments]
    if "documentos compartidos" not in normalized:
        return ""
    library_end = normalized.index("documentos compartidos")
    if len(segments) <= library_end + 1:  # library root is not a file parent
        return ""
    folder_segments = segments[:-1]
    folder_id = "/" + "/".join(folder_segments)
    all_items_path = "/" + "/".join(
        quote(segment, safe="")
        for segment in segments[: library_end + 1] + ["Forms", "AllItems.aspx"]
    )
    query = f"id={quote(folder_id, safe='')}"
    if folder_ctid:
        query = f"FolderCTID={quote(folder_ctid, safe='')}&{query}"
    return f"{parsed.scheme}://{parsed.netloc}{all_items_path}?{query}"


def _related_folder_links(decision: BotDecision, config=None) -> list[str]:
    folder_ctid = str(getattr(config, "sharepoint_folder_ctid", "") or "")
    return list(
        dict.fromkeys(
            folder_link
            for source in decision.fuentes
            if (folder_link := _sharepoint_folder_link(source.ubicacion, folder_ctid))
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
    folder_links = _related_folder_links(decision, config)
    if folder_links:
        folder_label = (
            "Archivos relacionados" if len(folder_links) == 1 else "Carpetas relacionadas"
        )
        response += f"\n{folder_label}: {' | '.join(folder_links)}"
    return response
