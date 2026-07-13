from clickup_retrieval import retrieve_clickup_evidence
from document_index import tokenize
from document_index import retrieve_document_evidence
from jira_retrieval import retrieve_jira_evidence
from logging_utils import get_logger
from models import EvidenceSource


logger = get_logger()


def _tokenize_query(text: str) -> set[str]:
    return set(tokenize(text))


def _humanize_filename(filename: str) -> str:
    stem = filename.rsplit(".", 1)[0]
    return stem.replace("_", " ").strip().title()


def _clean_fragment(text: str, limit: int = 320) -> str:
    lines = [line.strip("# ").strip() for line in text.splitlines() if line.strip()]
    compact = " ".join(lines)
    compact = " ".join(compact.split())
    if len(compact) <= limit:
        return compact
    truncated = compact[:limit].rsplit(" ", 1)[0].strip()
    return f"{truncated}..."


def _extract_result_text(content_items) -> str:
    fragments: list[str] = []
    for item in content_items or []:
        text = getattr(item, "text", None)
        if text:
            fragments.append(str(text).strip())
    return " ".join(fragment for fragment in fragments if fragment).strip()


def _score_result(user_message: str, filename: str, fragment: str) -> int:
    query_tokens = _tokenize_query(user_message)
    haystack = _tokenize_query(f"{filename} {fragment}")
    return len(query_tokens.intersection(haystack))


def _min_overlap_required(query_tokens: set[str]) -> int:
    if len(query_tokens) >= 4:
        return 2
    if len(query_tokens) >= 2:
        return 1
    return 0


def _dedupe_evidence(sources: list[EvidenceSource], limit: int = 4) -> list[EvidenceSource]:
    unique_sources: list[EvidenceSource] = []
    seen_keys: set[tuple[str, str]] = set()

    for source in sources:
        key = (source.tipo, source.ubicacion.strip().lower())
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_sources.append(source)
        if len(unique_sources) >= limit:
            break

    return unique_sources


def _retrieve_from_vector_store(
    user_message: str,
    client,
    vector_store_id: str,
    limit: int = 3,
) -> list[EvidenceSource]:
    query_tokens = _tokenize_query(user_message)
    min_overlap = _min_overlap_required(query_tokens)

    results = client.vector_stores.search(
        vector_store_id=vector_store_id,
        query=user_message,
        max_num_results=6,
        rewrite_query=True,
    )

    ranked_results: list[tuple[int, EvidenceSource]] = []
    for result in results.data:
        filename = getattr(result, "filename", None) or getattr(result, "file_id", "Documento")
        fragment = _extract_result_text(getattr(result, "content", []))
        if not fragment:
            continue

        score = _score_result(user_message, filename, fragment)
        if score < min_overlap:
            continue

        ranked_results.append(
            (
                score,
                EvidenceSource(
                    tipo="setup" if filename.startswith("setup__") else "vector_store",
                    titulo=_humanize_filename(filename),
                    ubicacion=filename,
                    fragmento=_clean_fragment(fragment),
                ),
            )
        )

    ranked_results.sort(key=lambda item: item[0], reverse=True)
    best_score = ranked_results[0][0] if ranked_results else 0

    filtered_sources = [
        source
        for score, source in ranked_results
        if score >= min_overlap and score >= best_score - 1
    ]

    return _dedupe_evidence(filtered_sources, limit=limit)


def retrieve_evidence(user_message: str, client=None, config=None) -> list[EvidenceSource]:
    """
    Recupera evidencia desde ClickUp en modo solo lectura cuando esta
    configurado. Luego intenta OpenAI Vector Stores y finalmente vuelve al
    indice local.
    """
    sources: list[EvidenceSource] = []

    clickup_evidence = retrieve_clickup_evidence(user_message, config=config, limit=2)
    sources.extend(clickup_evidence)

    jira_evidence = retrieve_jira_evidence(user_message, config=config, limit=2)
    sources.extend(jira_evidence)

    vector_store_id = getattr(config, "openai_vector_store_id", "")
    if client and vector_store_id:
        try:
            evidence = _retrieve_from_vector_store(user_message, client, vector_store_id)
            logger.info(
                "Consulta resuelta con vector store. vector_store_id=%s evidencias=%s",
                vector_store_id,
                len(evidence),
            )
            if evidence:
                return _dedupe_evidence(sources + evidence, limit=4)
        except Exception:
            logger.exception(
                "Fallo la consulta al vector store de OpenAI. Se usara el indice documental local."
            )

    document_evidence = retrieve_document_evidence(user_message)
    if sources:
        return _dedupe_evidence(sources + document_evidence, limit=4)

    return _dedupe_evidence(document_evidence, limit=4)
