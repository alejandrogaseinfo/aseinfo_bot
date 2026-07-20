"""Proveedor e ingesta documental para Azure AI Search.

La búsqueda y la carga usan la misma clave del servicio durante el MVP. En un
entorno compartido se deben separar una clave de consulta y una identidad con
el rol ``Search Index Data Contributor`` para la ingesta.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchFieldDataType,
    SearchIndex,
    SearchableField,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
)
from azure.search.documents.models import QueryType
from pypdf import PdfReader

from document_index import tokenize
from models import EvidenceSource


SUPPORTED_EXTENSIONS = {".md", ".markdown", ".txt", ".pdf"}
CONTENT_FIELD = "content"
SEARCH_TIMEOUT_SECONDS = 10
COUNTRY_ALIASES = {
    "guatemala": {"guatemala"},
    "mexico": {"mexico"},
    "salvador": {"salvador", "sv"},
}


def _credential(config):
    """Prefer a key for the MVP; allow Entra RBAC where it is available."""
    if config.azure_search_api_key:
        return AzureKeyCredential(config.azure_search_api_key)
    if config.azure_search_use_entra_id:
        return DefaultAzureCredential(exclude_interactive_browser_credential=False)
    raise RuntimeError("Falta AZURE_SEARCH_API_KEY o AZURE_SEARCH_USE_ENTRA_ID=true.")


def _clean_text(text: str, limit: int = 500) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit].rsplit(' ', 1)[0]}..."


def _excerpt_around_query(text: str, query: str, limit: int = 1_000) -> str:
    """Return the most relevant part of a chunk instead of its first characters."""
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact

    query_tokens = set(tokenize(query))
    if not query_tokens:
        return _clean_text(compact, limit)

    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", compact)
        if sentence.strip()
    ]
    if not sentences:
        return _clean_text(compact, limit)

    calculation_terms = {"calcula", "formula", "proporcional"}
    calculation_question = bool(query_tokens.intersection(calculation_terms))
    scores = []
    for sentence in sentences:
        score = len(query_tokens.intersection(tokenize(sentence)))
        sentence_tokens = set(tokenize(sentence))
        if calculation_question and sentence_tokens.intersection({"formula", "ejemplo"}):
            score += 5
        scores.append(score)
    best_index = max(range(len(sentences)), key=scores.__getitem__)
    if scores[best_index] == 0:
        return _clean_text(compact, limit)

    # A policy question can require two distant facts on the same page, for
    # example a benefit amount and its tax exemption. Keep the strongest
    # matching sentences rather than stopping after the first local passage.
    selected_indexes: set[int] = set()
    selected_length = 0
    for index in sorted(range(len(sentences)), key=scores.__getitem__, reverse=True):
        if scores[index] == 0:
            break
        sentence = sentences[index]
        separator_length = 1 if selected_indexes else 0
        if selected_indexes and selected_length + separator_length + len(sentence) > limit:
            continue
        selected_indexes.add(index)
        selected_length += separator_length + len(sentence)

    if not selected_indexes:
        selected_indexes.add(best_index)

    selected = " ".join(sentences[index] for index in sorted(selected_indexes))
    return _clean_text(selected, limit)


def _result_fragment(result: dict, user_message: str) -> str:
    captions = result.get("@search.captions") or []
    if captions:
        caption = captions[0]
        text = caption.get("text") if isinstance(caption, dict) else getattr(caption, "text", "")
        if text:
            return _excerpt_around_query(str(text), user_message)
    return _excerpt_around_query(str(result.get(CONTENT_FIELD, "")), user_message)


def _query_phrases(user_message: str) -> set[str]:
    tokens = tokenize(user_message)
    return {
        " ".join(tokens[start : start + phrase_size])
        for phrase_size in (2, 3)
        for start in range(len(tokens) - phrase_size + 1)
    }


def _document_relevance_score(
    record: dict,
    user_message: str,
    phrase_weights: dict[str, float] | None = None,
) -> float:
    """Prefer a page that contains the user's specific phrase over broad matches."""
    query_tokens = tokenize(user_message)
    document_tokens = tokenize(
        f"{record.get('title', '')} {record.get(CONTENT_FIELD, '')}"
    )
    if not query_tokens or not document_tokens:
        return 0.0

    document_token_set = set(document_tokens)
    token_overlap = len(set(query_tokens).intersection(document_token_set))
    document_text = " ".join(document_tokens)
    phrase_matches = {
        phrase for phrase in _query_phrases(user_message) if phrase in document_text
    }
    phrase_score = sum(
        (phrase_weights or {}).get(phrase, 4) for phrase in phrase_matches
    )

    raw_document_text = f"{record.get('title', '')} {record.get(CONTENT_FIELD, '')}".lower()
    country_adjustment = 0
    for country, aliases in COUNTRY_ALIASES.items():
        if country not in query_tokens:
            continue
        if any(alias in raw_document_text for alias in aliases):
            country_adjustment += 40
        else:
            country_adjustment -= 20

    azure_score = float(record.get("@search.reranker_score") or record.get("@search.score") or 0)
    # Coverage across the question's concepts matters more than one isolated
    # exact phrase. This prevents a page that merely lists a decree number
    # from outranking the page that explains its calculation.
    return (token_overlap * 4) + phrase_score + country_adjustment + (azure_score / 1_000)


def _rerank_records(records: list[dict], user_message: str) -> list[tuple[float, dict]]:
    """Rerank Azure candidates and boost phrases rare within the candidate set."""
    phrases = _query_phrases(user_message)
    phrase_document_frequency = {phrase: 0 for phrase in phrases}
    for record in records:
        document_text = " ".join(
            tokenize(f"{record.get('title', '')} {record.get(CONTENT_FIELD, '')}")
        )
        for phrase in phrases:
            if phrase in document_text:
                phrase_document_frequency[phrase] += 1

    phrase_weights = {
        phrase: 4 + (8 / frequency)
        for phrase, frequency in phrase_document_frequency.items()
        if frequency
    }
    ranked_records = [
        (_document_relevance_score(record, user_message, phrase_weights), record)
        for record in records
    ]
    ranked_records.sort(key=lambda item: item[0], reverse=True)
    return ranked_records


def retrieve_azure_search_evidence(
    user_message: str, config, limit: int = 3
) -> list[EvidenceSource]:
    """Run a keyword or semantic query and normalize it to bot evidence."""
    if not getattr(config, "azure_search_configured", False):
        return []

    client = SearchClient(
        endpoint=config.azure_search_endpoint,
        index_name=config.azure_search_index_name,
        credential=_credential(config),
    )
    search_args = {
        "search_text": user_message,
        # Azure provides the candidate set. A local, deterministic rerank then
        # promotes pages containing exact phrases from the user's question.
        "top": max(limit * 4, 12),
        "select": ["title", "source_url", "source_system", CONTENT_FIELD],
        "search_fields": ["title", CONTENT_FIELD, "content_tokens"],
        "connection_timeout": SEARCH_TIMEOUT_SECONDS,
        "read_timeout": SEARCH_TIMEOUT_SECONDS,
    }
    if config.azure_search_use_semantic:
        search_args.update(
            query_type=QueryType.SEMANTIC,
            semantic_configuration_name=config.azure_search_semantic_configuration,
            query_caption="extractive",
        )

    candidate_records = [dict(result) for result in client.search(**search_args)]
    ranked_records = _rerank_records(candidate_records, user_message)
    if not ranked_records:
        return []

    # Avoid sending tangential pages to generation when one page has a much
    # stronger match. Multiple pages are retained when they are similarly
    # relevant, which still supports answers that span a section boundary.
    best_score = ranked_records[0][0]
    if best_score < 12:
        return []
    relevant_records = [
        item for item in ranked_records if item[0] >= best_score * 0.95
    ][:limit]
    sources: list[EvidenceSource] = []
    for _, record in relevant_records:
        fragment = _result_fragment(record, user_message)
        if not fragment:
            continue
        source_system = record.get("source_system", "azure_ai_search")
        sources.append(
            EvidenceSource(
                tipo="sharepoint" if source_system == "sharepoint" else "azure_ai_search",
                titulo=record.get("title") or "Documento sin título",
                ubicacion=record.get("source_url") or "Azure AI Search",
                fragmento=fragment,
            )
        )
    return sources


def _document_pages(document_path: Path) -> list[tuple[int | None, str]]:
    """Extract text by page so a search result keeps its original context."""
    if document_path.suffix.lower() == ".pdf":
        reader = PdfReader(str(document_path))
        return [
            (page_number, page.extract_text() or "")
            for page_number, page in enumerate(reader.pages, start=1)
        ]
    return [(None, document_path.read_text(encoding="utf-8", errors="replace"))]


def _chunks(text: str, size: int = 450, overlap: int = 75) -> Iterable[str]:
    """Split a single page into focused, overlapping retrieval chunks."""
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap
    return chunks


def _metadata_for(document_path: Path) -> dict:
    metadata_path = document_path.with_suffix(document_path.suffix + ".metadata.json")
    if not metadata_path.exists():
        return {}
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _document_records(source_dir: Path) -> list[dict]:
    records: list[dict] = []
    for document_path in sorted(source_dir.rglob("*")):
        if not document_path.is_file() or document_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        pages = _document_pages(document_path)
        full_text = "\n".join(text for _, text in pages)
        if not full_text.strip():
            continue
        metadata = _metadata_for(document_path)
        source_url = metadata.get("web_url") or str(document_path.resolve())
        title = metadata.get("name") or document_path.stem
        source_system = metadata.get("source_system", "local")
        document_hash = hashlib.sha256(
            f"{source_url}|{full_text}".encode("utf-8")
        ).hexdigest()
        sequence = 0
        for page_number, page_text in pages:
            for chunk in _chunks(page_text):
                page_label = f"Página {page_number}" if page_number else "Documento"
                records.append(
                    {
                        "id": f"{document_hash}-{sequence}",
                        "title": f"{title} — {page_label}",
                        "content": f"{page_label}\n{chunk}",
                        "source_url": source_url,
                        "source_system": source_system,
                        "chunk_number": sequence,
                        "content_tokens": " ".join(tokenize(chunk)),
                    }
                )
                sequence += 1
    return records


def _existing_record_ids(client: SearchClient, source_urls: set[str]) -> set[str]:
    """Find prior chunks so a re-ingest removes stale larger chunks."""
    existing_ids: set[str] = set()
    for source_url in source_urls:
        escaped_url = source_url.replace("'", "''")
        results = client.search(
            search_text="*",
            filter=f"source_url eq '{escaped_url}'",
            select=["id"],
            top=1_000,
        )
        existing_ids.update(str(result["id"]) for result in results)
    return existing_ids


def ensure_index(config) -> None:
    """Create the minimal text/semantic index when it does not exist."""
    index_client = SearchIndexClient(
        endpoint=config.azure_search_endpoint,
        credential=_credential(config),
    )
    try:
        index_client.get_index(config.azure_search_index_name)
        return
    except ResourceNotFoundError:
        pass

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchableField(name="title", type=SearchFieldDataType.String, searchable=True),
        SearchableField(name=CONTENT_FIELD, type=SearchFieldDataType.String, searchable=True),
        SimpleField(name="source_url", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="source_system", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="chunk_number", type=SearchFieldDataType.Int32, filterable=True),
        SearchableField(name="content_tokens", type=SearchFieldDataType.String, searchable=True),
    ]
    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name=config.azure_search_semantic_configuration,
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="title"),
                    content_fields=[SemanticField(field_name=CONTENT_FIELD)],
                ),
            )
        ]
    )
    index_client.create_index(
        SearchIndex(
            name=config.azure_search_index_name,
            fields=fields,
            semantic_search=semantic_search,
        )
    )


def index_directory(source_dir: Path, config, create_index: bool = False) -> int:
    """Upload Markdown, text and PDFs from a controlled staging directory."""
    if not getattr(config, "azure_search_configured", False):
        raise RuntimeError("Falta configurar AZURE_SEARCH_ENDPOINT y AZURE_SEARCH_API_KEY.")
    if create_index:
        ensure_index(config)
    records = _document_records(source_dir)
    if not records:
        return 0
    client = SearchClient(
        endpoint=config.azure_search_endpoint,
        index_name=config.azure_search_index_name,
        credential=_credential(config),
    )
    previous_ids = _existing_record_ids(
        client, {str(record["source_url"]) for record in records}
    )
    for offset in range(0, len(records), 500):
        results = client.merge_or_upload_documents(documents=records[offset : offset + 500])
        failures = [result.key for result in results if not result.succeeded]
        if failures:
            raise RuntimeError(f"Azure AI Search rechazó {len(failures)} fragmentos.")

    stale_ids = previous_ids.difference(str(record["id"]) for record in records)
    for offset in range(0, len(stale_ids), 500):
        client.delete_documents(
            documents=[{"id": record_id} for record_id in list(stale_ids)[offset : offset + 500]]
        )
    return len(records)
