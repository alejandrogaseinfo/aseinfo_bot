from azure_search import is_release_guidance_question, retrieve_azure_search_evidence
from classification import has_explicit_version_request
from document_index import retrieve_document_evidence
from logging_utils import get_logger
from models import EvidenceSource, RetrievalTrace


logger = get_logger()


def _dedupe_evidence(sources: list[EvidenceSource], limit: int = 4) -> list[EvidenceSource]:
    unique_sources: list[EvidenceSource] = []
    seen_keys: set[tuple[str, str]] = set()

    for source in sources:
        key = (
            source.tipo,
            source.ubicacion.strip().lower(),
            source.fragmento.strip().lower(),
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_sources.append(source)
        if len(unique_sources) >= limit:
            break

    return unique_sources


def retrieve_evidence(
    user_message: str, client=None, config=None, return_trace: bool = False
) -> list[EvidenceSource] | RetrievalTrace:
    """
    Recupera evidencia desde Azure AI Search; el índice local solo respalda
    entornos que lo permiten explícitamente.
    """
    if getattr(
        config,
        "azure_search_enabled",
        getattr(config, "azure_search_configured", False),
    ):
        try:
            result = retrieve_azure_search_evidence(
                user_message, config=config, client=client, return_trace=return_trace
            )
            evidence = result.sources if isinstance(result, RetrievalTrace) else result
            logger.info(
                "Consulta resuelta con Azure AI Search. index_name=%s evidencias=%s",
                config.azure_search_index_name,
                len(evidence),
            )
            if evidence:
                deduped = _dedupe_evidence(evidence, limit=4)
                if isinstance(result, RetrievalTrace):
                    result.sources = deduped
                    return result
                return deduped
            if isinstance(result, RetrievalTrace) and result.requires_version_context:
                return result
            if (
                isinstance(result, RetrievalTrace)
                and not result.sources
                and is_release_guidance_question(user_message)
                and not has_explicit_version_request(user_message)
            ):
                result.requires_version_context = True
                result.rejected_reasons["release_version_required"] = 1
                return result
            # V2 deliberately abstains when Azure AI Search cannot establish
            # direct evidence. Falling back to the local development corpus
            # turns that safe abstention into an unrelated answer and makes a
            # staging evaluation differ from the deployed index.
            if getattr(config, "retrieval_strategy", "legacy") == "v2":
                return result
        except Exception:
            logger.exception("Falló Azure AI Search.")

    if not getattr(config, "allow_local_document_fallback", True):
        logger.info(
            "No se usará el índice local. environment=%s",
            getattr(config, "environment", "unknown"),
        )
        return RetrievalTrace() if return_trace else []

    document_evidence = retrieve_document_evidence(user_message)
    deduped = _dedupe_evidence(document_evidence, limit=4)
    return RetrievalTrace(sources=deduped, direct_evidence_count=len(deduped)) if return_trace else deduped
