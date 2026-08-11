from urllib.parse import quote, unquote, urlparse, urlsplit, urlunsplit

from models import BotDecision


def _source_label(decision: BotDecision) -> str:
    source_types = {source.tipo for source in decision.fuentes}
    if source_types.issubset({"azure_ai_search", "sharepoint"}):
        return "Azure AI Search"
    if source_types == {"documento"}:
        return "Base documental local"
    return "Fuentes documentales"


def _source_links(decision: BotDecision, config=None) -> list[tuple[str, str]]:
    """Return unique document links with a short, evidence-derived label."""
    links: list[tuple[str, str]] = []
    seen_urls: set[str] = set()
    for source in decision.fuentes:
        url = _page_aware_url(
            source.ubicacion,
            source.titulo,
            enabled=getattr(config, "use_pdf_page_links", True),
        )
        if not url.startswith(("https://", "http://")) or url in seen_urls:
            continue
        seen_urls.add(url)
        links.append((_document_link_label(source.titulo), url))
    return links


def _page_aware_url(url: str, title: str, *, enabled: bool = True) -> str:
    """Add the standard PDF page fragment when evidence cites a page."""
    if not enabled or not url.lower().split("?", 1)[0].endswith(".pdf"):
        return url
    marker = " — Página "
    if marker not in (title or ""):
        return url
    _base, page_number = title.rsplit(marker, 1)
    page_number = page_number.strip()
    if not page_number.isdigit():
        return url
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, f"page={page_number}"))


def _document_link_label(title: str) -> str:
    """Build a readable link label without exposing internal paths."""
    title = (title or "documentación").strip()
    page = ""
    page_marker = " — Página "
    if page_marker in title:
        title, page_number = title.rsplit(page_marker, 1)
        page = f" (pág. {page_number.strip()})"
    for suffix in (" — Documento", " - Documento"):
        if title.endswith(suffix):
            title = title[: -len(suffix)].rstrip()
            break
    title = title or "documentación"
    if len(title) > 72:
        title = f"{title[:69].rstrip()}..."
    return f"Ver documento: {title}{page}"


def _markdown_link(label: str, url: str) -> str:
    """Render a link while preserving the exact evidence URL as its target."""
    safe_label = (label or "Abrir enlace").replace("[", "(").replace("]", ")")
    return f"[{safe_label}]({url})"


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
    if any(source.version_confirmed is False for source in decision.fuentes):
        response += (
            "\nNota: La fuente encontrada documenta la estructura técnica, "
            "pero no confirma explícitamente su correspondencia con la versión solicitada."
        )
    source_links = _source_links(decision, config)
    if source_links:
        link_label = "Enlace" if len(source_links) == 1 else "Enlaces"
        if getattr(config, "use_friendly_links", True):
            rendered_links = " | ".join(
                _markdown_link(label, url) for label, url in source_links
            )
        else:
            rendered_links = " | ".join(url for _label, url in source_links)
        response += f"\n{link_label}: {rendered_links}"
    folder_links = _related_folder_links(decision, config)
    if folder_links:
        folder_label = (
            "Archivos relacionados" if len(folder_links) == 1 else "Carpetas relacionadas"
        )
        if getattr(config, "use_friendly_links", True):
            folder_links = [
                _markdown_link("Abrir carpeta relacionada", url)
                for url in folder_links
            ]
        response += f"\n{folder_label}: {' | '.join(folder_links)}"
    return response
