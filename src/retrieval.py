from document_index import retrieve_document_evidence
from logging_utils import get_logger
from models import EvidenceSource


logger = get_logger()


def _tokenize_query(text: str) -> set[str]:
    return {
        token
        for token in text.lower().replace("?", " ").replace(".", " ").split()
        if len(token) > 2
    }


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


def _retrieve_from_vector_store(
    user_message: str,
    client,
    vector_store_id: str,
    limit: int = 3,
) -> list[EvidenceSource]:
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
        if score == 0:
            continue

        ranked_results.append(
            (
                score,
                EvidenceSource(
                    tipo="vector_store",
                    titulo=_humanize_filename(filename),
                    ubicacion=filename,
                    fragmento=_clean_fragment(fragment),
                ),
            )
        )

    ranked_results.sort(key=lambda item: item[0], reverse=True)

    return [source for _, source in ranked_results[:limit]]


def retrieve_evidence(user_message: str, client=None, config=None) -> list[EvidenceSource]:
    """
    Recupera evidencia desde OpenAI Vector Stores cuando hay configuracion
    disponible. Si no existe o falla la consulta, vuelve al indice local.
    """
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
                return evidence
        except Exception:
            logger.exception(
                "Fallo la consulta al vector store de OpenAI. Se usara el indice documental local."
            )

    return retrieve_document_evidence(user_message)
