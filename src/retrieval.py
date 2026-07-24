from azure_search import retrieve_azure_search_evidence
from document_index import retrieve_document_evidence
from logging_utils import get_logger
from models import EvidenceSource


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


def retrieve_evidence(user_message: str, client=None, config=None) -> list[EvidenceSource]:
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
            evidence = retrieve_azure_search_evidence(
                user_message, config=config, client=client
            )
            logger.info(
                "Consulta resuelta con Azure AI Search. index_name=%s evidencias=%s",
                config.azure_search_index_name,
                len(evidence),
            )
            if evidence:
                return _dedupe_evidence(evidence, limit=4)
        except Exception:
            logger.exception("Falló Azure AI Search.")

    if not getattr(config, "allow_local_document_fallback", True):
        logger.info(
            "No se usará el índice local. environment=%s",
            getattr(config, "environment", "unknown"),
        )
        return []

    document_evidence = retrieve_document_evidence(user_message)
    return _dedupe_evidence(document_evidence, limit=4)
