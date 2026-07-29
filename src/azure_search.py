"""Proveedor e ingesta documental para Azure AI Search.

La búsqueda y la carga usan la misma clave del servicio durante el MVP. En un
entorno compartido se deben separar una clave de consulta y una identidad con
el rol ``Search Index Data Contributor`` para la ingesta.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchFieldDataType,
    SearchField,
    SearchIndex,
    SearchableField,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery
from openai import OpenAI
from pypdf import PdfReader

from document_index import tokenize
from models import EvidenceSource


# Solo se ingieren formatos con texto recuperable. Los binarios de la carpeta
# (imágenes, vídeos, ejecutables y comprimidos) permanecen fuera del índice.
SUPPORTED_EXTENSIONS = {
    ".aspx",
    ".bat",
    ".csv",
    ".docx",
    ".json",
    ".pdf",
    ".ps1",
    ".rdlc",
    ".sql",
    ".txt",
    ".xlsx",
    ".xml",
}
CONTENT_FIELD = "content"
CONTEXT_FIELD = "document_context"
CONTENT_VECTOR_FIELD = "content_vector"
SEARCH_TIMEOUT_SECONDS = 10
MAX_CANDIDATES = 30
DELETION_MANIFEST_NAME = ".libras-sharepoint-deletions.json"
CHANGE_MANIFEST_NAME = ".libras-sharepoint-changes.json"
SYNC_STATE_NAME = ".libras-sharepoint-sync-state.json"
# Keep query fields compatible with indexes created before the optional
# SharePoint provenance fields were added. The richer metadata is read with
# ``dict.get`` below when the active index provides it.
SEARCH_SELECT_FIELDS = [
    "id",
    "title",
    "source_url",
    "source_system",
    CONTEXT_FIELD,
    CONTENT_FIELD,
    "content_tokens",
    "chunk_number",
]
COUNTRY_TOKENS = {
    "guatemala": {"guatemala", "guatemalteco", "guatemalteca"},
    "el_salvador": {"salvador", "salvadoreno", "salvadoreño", "salvadorena", "salvadoreña"},
}
GENERIC_QUERY_TOKENS = {
    "cambio",
    "como",
    "configur",
    "document",
    "documentacion",
    "existir",
    "hacer",
    "informacion",
    "oficial",
    "paso",
    "procedimiento",
    "realizar",
    "tema",
}


@lru_cache(maxsize=1)
def _entra_credential():
    """Reuse Entra token state instead of prompting for every local query."""
    return DefaultAzureCredential(exclude_interactive_browser_credential=False)


def _credential(config):
    """Prefer a key for the MVP; allow Entra RBAC where it is available."""
    if config.azure_search_api_key:
        return AzureKeyCredential(config.azure_search_api_key)
    if config.azure_search_use_entra_id:
        return _entra_credential()
    raise RuntimeError("Falta AZURE_SEARCH_API_KEY o AZURE_SEARCH_USE_ENTRA_ID=true.")


def _embedding_client(config) -> OpenAI:
    return OpenAI(
        api_key=config.openai_api_key,
        base_url=getattr(
            config,
            "resolved_openai_base_url",
            getattr(config, "openai_base_url", "") or "https://api.openai.com/v1",
        ),
    )


def _embed_texts(texts: list[str], config, client=None) -> list[list[float]]:
    embedding_client = client or _embedding_client(config)
    response = embedding_client.embeddings.create(
        model=config.openai_embedding_model,
        input=texts,
    )
    return [item.embedding for item in response.data]


def _attach_embeddings(records: list[dict], config) -> None:
    """Add one embedding per chunk before it is sent to Azure AI Search."""
    # Keep the request well below the provider's aggregate token limit when
    # indexing code-heavy files with many tokens per character.
    for offset in range(0, len(records), 20):
        batch = records[offset : offset + 20]
        embeddings = _embed_texts(
            [str(record[CONTENT_FIELD]) for record in batch], config
        )
        if len(embeddings) != len(batch):
            raise RuntimeError("No se recibió un embedding para cada fragmento.")
        for record, embedding in zip(batch, embeddings):
            record[CONTENT_VECTOR_FIELD] = embedding


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
    token_weights: dict[str, float] | None = None,
    phrase_weights: dict[str, float] | None = None,
) -> float:
    """Score evidence with generic token coverage, phrase matches and structure."""
    query_tokens = tokenize(user_message)
    document_tokens = tokenize(
        f"{record.get('title', '')} {record.get(CONTENT_FIELD, '')}"
    )
    if not query_tokens or not document_tokens:
        return 0.0

    document_token_set = set(document_tokens)
    token_overlap = set(query_tokens).intersection(document_token_set)
    coverage_score = sum((token_weights or {}).get(token, 1) for token in token_overlap)
    document_text = " ".join(document_tokens)
    phrase_matches = {
        phrase for phrase in _query_phrases(user_message) if phrase in document_text
    }
    phrase_score = sum(
        (phrase_weights or {}).get(phrase, 4) for phrase in phrase_matches
    )

    azure_score = float(record.get("@search.reranker_score") or record.get("@search.score") or 0)
    # Coverage across the question's concepts matters more than one isolated
    # exact phrase. This prevents a page that merely lists a decree number
    # from outranking the page that explains its calculation.
    return (
        (coverage_score * 6)
        + phrase_score
        # Vector similarity finds paraphrases; lexical rank favors pages that
        # explicitly contain the terms requested. Neither source wins alone.
        + max(0, MAX_CANDIDATES - int(record.get("_vector_rank", MAX_CANDIDATES))) * 3.0
        + max(0, MAX_CANDIDATES - int(record.get("_keyword_rank", MAX_CANDIDATES))) * 0.2
        + (azure_score / 1_000)
        - (int(record.get("_missing_anchor_count", 0)) * 8)
    )


def _requested_country(user_message: str) -> str | None:
    query_tokens = set(tokenize(user_message))
    for country, country_tokens in COUNTRY_TOKENS.items():
        if query_tokens.intersection(country_tokens):
            return country
    return None


def _record_has_authorized_provenance(record: dict) -> bool:
    """Accept only HTTPS SharePoint items from the approved document index."""
    return (
        record.get("source_system") == "sharepoint"
        and str(record.get("source_url") or "").startswith("https://")
    )


def _filter_records_for_requested_country(
    records: list[dict], user_message: str
) -> list[dict]:
    """Do not substitute evidence from another country for an explicit request."""
    country = _requested_country(user_message)
    if country is None:
        return records

    country_tokens = COUNTRY_TOKENS[country]
    return [
        record
        for record in records
        if _record_matches_only_requested_country(record, country_tokens)
    ]


def _record_matches_only_requested_country(record: dict, country_tokens: set[str]) -> bool:
    record_tokens = set(
        tokenize(
            f"{record.get('title', '')} {record.get(CONTEXT_FIELD, '')} "
            f"{record.get(CONTENT_FIELD, '')}"
        )
    )
    if not country_tokens.intersection(record_tokens):
        return False

    other_country_tokens = set().union(
        *(tokens for tokens in COUNTRY_TOKENS.values() if tokens != country_tokens)
    )
    # Contact footers often list several countries.  They do not establish
    # that the technical procedure applies to any one of those countries.
    return not other_country_tokens.intersection(record_tokens)


def _has_minimum_content_coverage(record: dict, user_message: str) -> bool:
    """Reject a tangential hit that shares only one broad term with the query."""
    country_tokens = set().union(*COUNTRY_TOKENS.values())
    required_tokens = set(tokenize(user_message)).difference(
        GENERIC_QUERY_TOKENS, country_tokens
    )
    if not required_tokens:
        return True

    record_tokens = set(
        tokenize(f"{record.get('title', '')} {record.get(CONTENT_FIELD, '')}")
    )
    required_matches = required_tokens.intersection(record_tokens)
    if _requested_country(user_message) is not None:
        # Country filtering above already requires an exclusive country match;
        # one domain term can be sufficient for a short country-specific query.
        minimum_matches = 1
    elif len(required_tokens) >= 4:
        minimum_matches = 3
    else:
        minimum_matches = 2 if len(required_tokens) >= 3 else 1
    return len(required_matches) >= minimum_matches


def _rerank_records(records: list[dict], user_message: str) -> list[tuple[float, dict]]:
    """Rerank Azure candidates with query coverage and corpus-relative weights."""
    query_tokens = set(tokenize(user_message))
    token_document_frequency = {token: 0 for token in query_tokens}
    phrases = _query_phrases(user_message)
    phrase_document_frequency = {phrase: 0 for phrase in phrases}
    for record in records:
        document_text = " ".join(
            tokenize(f"{record.get('title', '')} {record.get(CONTENT_FIELD, '')}")
        )
        document_token_set = set(document_text.split())
        for token in query_tokens:
            if token in document_token_set:
                token_document_frequency[token] += 1
        for phrase in phrases:
            if phrase in document_text:
                phrase_document_frequency[phrase] += 1

    candidate_count = max(len(records), 1)
    token_weights = {
        token: 1 + math.log((candidate_count + 1) / (frequency + 1))
        for token, frequency in token_document_frequency.items()
    }
    phrase_weights = {
        phrase: 2 + (4 * math.log((candidate_count + 1) / (frequency + 1)))
        for phrase, frequency in phrase_document_frequency.items()
        if frequency
    }
    # Query terms that appear in only part of the candidate set are useful
    # disambiguators (country, product, module, acronym). Penalize a result
    # that omits them, without keeping a vocabulary of special cases.
    anchor_tokens = {
        token
        for token, frequency in token_document_frequency.items()
        if 0 < frequency <= candidate_count * 0.45 and len(token) > 3
    }
    for record in records:
        record_tokens = set(
            tokenize(
                f"{record.get('title', '')} {record.get(CONTEXT_FIELD, '')} "
                f"{record.get(CONTENT_FIELD, '')}"
            )
        )
        record["_missing_anchor_count"] = len(anchor_tokens.difference(record_tokens))
    ranked_records = [
        (_document_relevance_score(record, user_message, token_weights, phrase_weights), record)
        for record in records
    ]
    ranked_records.sort(key=lambda item: item[0], reverse=True)
    return ranked_records


def retrieve_azure_search_evidence(
    user_message: str, config, client=None, limit: int = 3
) -> list[EvidenceSource]:
    """Retrieve vector candidates and normalize them to bot evidence."""
    if not getattr(config, "azure_search_configured", False):
        return []

    search_client = SearchClient(
        endpoint=config.azure_search_endpoint,
        index_name=config.azure_search_index_name,
        credential=_credential(config),
    )
    search_args = {
        "top": MAX_CANDIDATES,
        "select": SEARCH_SELECT_FIELDS,
        "connection_timeout": SEARCH_TIMEOUT_SECONDS,
        "read_timeout": SEARCH_TIMEOUT_SECONDS,
    }

    # The vector query is generic: it compares the meaning of a question with
    # every indexed chunk. The keyword pass complements it for exact policy
    # names, acronyms and figures. No document-specific query rewrites exist.
    try:
        query_embedding = _embed_texts([user_message], config, client=client)[0]
        vector_query = VectorizedQuery(
            vector=query_embedding,
            k_nearest_neighbors=MAX_CANDIDATES,
            fields=CONTENT_VECTOR_FIELD,
        )
        records_by_id: dict[str, dict] = {}
        for rank, result in enumerate(
            search_client.search(
                search_text=None,
                vector_queries=[vector_query],
                **search_args,
            ),
            start=1,
        ):
            record = dict(result)
            record["_vector_rank"] = rank
            records_by_id[str(record.get("id", ""))] = record

        for rank, result in enumerate(
            search_client.search(
                search_text=user_message,
                search_fields=["title", CONTENT_FIELD, "content_tokens"],
                **search_args,
            ),
            start=1,
        ):
            record = dict(result)
            record_id = str(record.get("id", ""))
            existing = records_by_id.get(record_id)
            if existing is None:
                existing = record
                records_by_id[record_id] = existing
            existing["_keyword_rank"] = rank
        candidate_records = list(records_by_id.values())
    except Exception:
        # Keep a usable, lower-quality fallback if embeddings or a legacy index
        # are temporarily unavailable. It deliberately has no topic-specific
        # behavior, and the caller still rejects weak evidence below.
        candidate_records = [
            dict(result)
            for result in search_client.search(
                search_text=user_message,
                search_fields=["title", CONTENT_FIELD, "content_tokens"],
                **search_args,
            )
        ]

    authorized_records = [
        record for record in candidate_records if _record_has_authorized_provenance(record)
    ]
    country_scoped_records = _filter_records_for_requested_country(authorized_records, user_message)
    candidate_records = [
        record
        for record in country_scoped_records
        if _has_minimum_content_coverage(record, user_message)
    ]
    ranked_records = _rerank_records(candidate_records, user_message)
    if not ranked_records:
        return []

    # Avoid sending tangential pages to generation when one page has a much
    # stronger match. Multiple pages are retained when they are similarly
    # relevant, which still supports answers that span a section boundary.
    best_score = ranked_records[0][0]
    if best_score < 8:
        return []
    relevant_records = [
        item for item in ranked_records if item[0] >= best_score * 0.80
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
                source_system=source_system,
                document_id=str(record.get("document_id") or ""),
                document_version=str(record.get("document_version") or ""),
                last_modified=str(record.get("last_modified") or ""),
                document_type=str(record.get("document_type") or ""),
                folder_path=str(record.get("folder_path") or ""),
            )
        )
    return sources


def _document_pages(document_path: Path) -> list[tuple[int | None, str]]:
    """Extract text by page so a search result keeps its original context."""
    if document_path.stat().st_size == 0:
        return []
    extension = document_path.suffix.lower()
    if extension == ".pdf":
        reader = PdfReader(str(document_path))
        return [
            (page_number, page.extract_text() or "")
            for page_number, page in enumerate(reader.pages, start=1)
        ]
    if extension == ".docx":
        from docx import Document

        document = Document(str(document_path))
        parts = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
        for table in document.tables:
            for row in table.rows:
                parts.append(" | ".join(cell.text for cell in row.cells))
        return [(None, "\n".join(parts))]
    if extension == ".xlsx":
        from openpyxl import load_workbook

        workbook = load_workbook(str(document_path), read_only=True, data_only=True)
        parts: list[str] = []
        for worksheet in workbook.worksheets:
            parts.append(f"Hoja: {worksheet.title}")
            for row in worksheet.iter_rows(values_only=True):
                values = [str(value) for value in row if value is not None]
                if values:
                    parts.append(" | ".join(values))
        workbook.close()
        return [(None, "\n".join(parts))]
    return [(None, document_path.read_text(encoding="utf-8", errors="replace"))]


def _chunks(
    text: str,
    size: int = 450,
    overlap: int = 75,
    max_characters: int = 6_000,
) -> Iterable[str]:
    """Split text by words and characters for safe embedding requests."""
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start
        character_count = 0
        while end < len(words) and end < start + size:
            word_length = len(words[end])
            separator_length = 1 if end > start else 0
            if end > start and character_count + separator_length + word_length > max_characters:
                break
            if end == start and word_length > max_characters:
                for offset in range(0, word_length, max_characters):
                    chunks.append(words[end][offset : offset + max_characters])
                end += 1
                break
            character_count += separator_length + word_length
            end += 1
        split_long_word = False
        if end == start:
            end += 1
        elif len(words[start]) > max_characters:
            split_long_word = True
        if not split_long_word:
            chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(start + 1, end - overlap)
    return chunks


def _metadata_for(document_path: Path) -> dict:
    metadata_path = document_path.with_suffix(document_path.suffix + ".metadata.json")
    if not metadata_path.exists():
        return {}
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _document_records(
    source_dir: Path, document_ids: set[str] | None = None
) -> list[dict]:
    records: list[dict] = []
    documents = [
        path
        for path in sorted(source_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    # Once the OneDrive sync has written metadata, index only those managed
    # copies. This prevents duplicate results from PDFs manually staged before
    # delegated access was approved.
    has_managed_documents = any(
        path.with_suffix(path.suffix + ".metadata.json").exists() for path in documents
    )
    sync_state_path = source_dir / SYNC_STATE_NAME
    synchronized_document_ids: set[str] | None = None
    if sync_state_path.exists():
        try:
            sync_state = json.loads(sync_state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise RuntimeError(
                f"El estado de sincronización no es JSON válido: {sync_state_path}"
            ) from error
        if not isinstance(sync_state, dict):
            raise RuntimeError(
                f"El estado de sincronización debe ser un objeto JSON: {sync_state_path}"
            )
        synchronized_documents = sync_state.get("documents", {})
        if isinstance(synchronized_documents, dict):
            synchronized_document_ids = set(synchronized_documents)
    for document_path in documents:
        if has_managed_documents and not document_path.with_suffix(
            document_path.suffix + ".metadata.json"
        ).exists():
            continue
        pages = _document_pages(document_path)
        full_text = "\n".join(text for _, text in pages)
        if not full_text.strip():
            continue
        metadata = _metadata_for(document_path)
        source_url = metadata.get("web_url") or str(document_path.resolve())
        title = metadata.get("name") or document_path.stem
        source_system = metadata.get("source_system", "local")
        document_id = str(metadata.get("document_id") or source_url)
        if (
            synchronized_document_ids is not None
            and source_system == "sharepoint"
            and document_id not in synchronized_document_ids
        ):
            continue
        if document_ids is not None and document_id not in document_ids:
            continue
        document_version = str(metadata.get("etag") or metadata.get("document_version") or "")
        last_modified = str(metadata.get("last_modified") or "")
        folder_path = str(metadata.get("folder_path") or "")
        # Later pages frequently omit the country/product named on the cover.
        # Store a compact document-level context with every chunk so retrieval
        # can keep that context without merging documents or pages.
        document_context = _clean_text(full_text, limit=900)
        content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
        document_key = hashlib.sha256(document_id.encode("utf-8")).hexdigest()
        sequence = 0
        for page_number, page_text in pages:
            for chunk in _chunks(page_text):
                page_label = f"Página {page_number}" if page_number else "Documento"
                records.append(
                    {
                        "id": f"{document_key}-{sequence}",
                        "title": f"{title} — {page_label}",
                        "content": f"{page_label}\n{chunk}",
                        CONTEXT_FIELD: document_context,
                        "source_url": source_url,
                        "source_system": source_system,
                        "document_id": document_id,
                        "document_version": document_version,
                        "last_modified": last_modified,
                        "content_hash": content_hash,
                        "document_type": document_path.suffix.lower().lstrip("."),
                        "folder_path": folder_path,
                        "indexed_at": datetime.now(timezone.utc).isoformat(),
                        "chunk_number": sequence,
                        "content_tokens": " ".join(tokenize(chunk)),
                    }
                )
                sequence += 1
    return records


def _existing_record_ids(client: SearchClient, document_ids: set[str]) -> set[str]:
    """Find prior chunks so updates and deletions remove stale fragments."""
    existing_ids: set[str] = set()
    for document_id in document_ids:
        escaped_id = document_id.replace("'", "''")
        results = client.search(
            search_text="*",
            filter=f"document_id eq '{escaped_id}'",
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
        SearchableField(name=CONTEXT_FIELD, type=SearchFieldDataType.String, searchable=True),
        SearchField(
            name=CONTENT_VECTOR_FIELD,
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=config.openai_embedding_dimensions,
            vector_search_profile_name="content-vector-profile",
        ),
        SimpleField(name="source_url", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="source_system", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="document_version", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="last_modified", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="content_hash", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="document_type", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="folder_path", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="indexed_at", type=SearchFieldDataType.String, filterable=True),
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
            vector_search=VectorSearch(
                algorithms=[HnswAlgorithmConfiguration(name="content-vector-hnsw")],
                profiles=[
                    VectorSearchProfile(
                        name="content-vector-profile",
                        algorithm_configuration_name="content-vector-hnsw",
                    )
                ],
            ),
        )
    )


def reset_index(config) -> None:
    """Delete and recreate only the explicitly configured pilot index."""
    index_client = SearchIndexClient(
        endpoint=config.azure_search_endpoint,
        credential=_credential(config),
    )
    try:
        index_client.delete_index(config.azure_search_index_name)
    except ResourceNotFoundError:
        pass
    ensure_index(config)


def _deletion_document_ids(source_dir: Path) -> set[str]:
    """Read idempotent SharePoint deletion notices written by the sync step."""
    manifest_path = source_dir / DELETION_MANIFEST_NAME
    if not manifest_path.exists():
        return set()
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"El manifiesto de eliminaciones no es válido: {manifest_path}") from error
    deletions = payload.get("deleted_document_ids", [])
    if not isinstance(deletions, list) or not all(isinstance(item, str) for item in deletions):
        raise RuntimeError("El manifiesto de eliminaciones debe contener deleted_document_ids.")
    return {item for item in deletions if item}


def _changed_document_ids(source_dir: Path) -> set[str] | None:
    """Read pending SharePoint upserts, or ``None`` for legacy full ingests."""
    manifest_path = source_dir / CHANGE_MANIFEST_NAME
    if not manifest_path.exists():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"El manifiesto de cambios no es válido: {manifest_path}") from error
    changes = payload.get("changed_document_ids", [])
    if not isinstance(changes, list) or not all(isinstance(item, str) for item in changes):
        raise RuntimeError("El manifiesto de cambios debe contener changed_document_ids.")
    return {item for item in changes if item}


def _delete_record_ids(client: SearchClient, record_ids: set[str]) -> None:
    for offset in range(0, len(record_ids), 500):
        batch = list(record_ids)[offset : offset + 500]
        results = client.delete_documents(documents=[{"id": record_id} for record_id in batch])
        failures = [result.key for result in results if not result.succeeded]
        if failures:
            raise RuntimeError(f"Azure AI Search no eliminó {len(failures)} fragmentos.")


def _clear_deletion_manifest(source_dir: Path) -> None:
    manifest_path = source_dir / DELETION_MANIFEST_NAME
    if manifest_path.exists():
        manifest_path.write_text(
            json.dumps({"deleted_document_ids": []}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _clear_change_manifest(source_dir: Path) -> None:
    manifest_path = source_dir / CHANGE_MANIFEST_NAME
    if manifest_path.exists():
        manifest_path.write_text(
            json.dumps({"changed_document_ids": []}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def index_directory(source_dir: Path, config, create_index: bool = False) -> int:
    """Upload all legacy files or only pending SharePoint changes to Azure AI Search."""
    if not getattr(config, "azure_search_configured", False):
        raise RuntimeError("Falta configurar AZURE_SEARCH_ENDPOINT y AZURE_SEARCH_API_KEY.")
    if create_index:
        ensure_index(config)
    client = SearchClient(
        endpoint=config.azure_search_endpoint,
        index_name=config.azure_search_index_name,
        credential=_credential(config),
    )
    deleted_document_ids = _deletion_document_ids(source_dir)
    if deleted_document_ids:
        _delete_record_ids(client, _existing_record_ids(client, deleted_document_ids))
        _clear_deletion_manifest(source_dir)

    change_manifest_document_ids = _changed_document_ids(source_dir)
    pending_changes = None if create_index else change_manifest_document_ids
    records = _document_records(source_dir, document_ids=pending_changes)
    target_document_ids = (
        pending_changes
        if pending_changes is not None
        else {str(record["document_id"]) for record in records}
    )
    previous_ids = _existing_record_ids(client, target_document_ids)

    if records:
        _attach_embeddings(records, config)
        for offset in range(0, len(records), 500):
            results = client.merge_or_upload_documents(documents=records[offset : offset + 500])
            failures = [result.key for result in results if not result.succeeded]
            if failures:
                raise RuntimeError(f"Azure AI Search rechazó {len(failures)} fragmentos.")

    stale_ids = previous_ids.difference(str(record["id"]) for record in records)
    _delete_record_ids(client, stale_ids)
    if change_manifest_document_ids is not None:
        _clear_change_manifest(source_dir)
    return len(records)
