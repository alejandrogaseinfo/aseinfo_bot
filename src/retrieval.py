from azure_search import retrieve_azure_search_evidence
from clickup_retrieval import retrieve_clickup_evidence
from document_index import retrieve_document_evidence
from jira_retrieval import retrieve_jira_evidence
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
    Recupera evidencia desde ClickUp en modo solo lectura cuando esta
    configurado. Azure AI Search es el índice documental principal y el índice
    local se conserva como respaldo para desarrollo o falta de permisos.
    """
    sources: list[EvidenceSource] = []

    clickup_evidence = retrieve_clickup_evidence(user_message, config=config, limit=2)
    sources.extend(clickup_evidence)

    jira_evidence = retrieve_jira_evidence(user_message, config=config, limit=2)
    sources.extend(jira_evidence)

    if getattr(config, "azure_search_configured", False):
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
                # During the document-retrieval flow, Azure is the source of
                # truth. Operational sources are consulted only when Azure has
                # no documentary evidence.
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
    if sources:
        return _dedupe_evidence(sources + document_evidence, limit=4)

    return _dedupe_evidence(document_evidence, limit=4)
