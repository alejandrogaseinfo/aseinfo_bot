"""Muestra la evidencia que Libras obtiene de Azure AI Search.

Es una herramienta de diagnóstico local, de solo lectura. Ejecuta la misma
estrategia de recuperación que usa el bot y no registra preguntas, secretos ni
contenido en telemetría. Su salida queda únicamente en la consola de quien la
ejecuta.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from azure.search.documents import SearchClient

from azure_search import (
    CANDIDATE_POOL_SIZE,
    CONTENT_FIELD,
    SEARCH_SELECT_FIELDS,
    SEARCH_TIMEOUT_SECONDS,
    _credential,
    _excerpt_around_query,
    retrieve_azure_search_evidence,
)
from config import Config, load_project_environment
from models import EvidenceSource, RetrievalTrace


def _source_payload(source: EvidenceSource) -> dict:
    """Expone solo los campos útiles para validar una recuperación."""
    return {
        "titulo": source.titulo,
        "enlace": source.ubicacion,
        "fragmento": source.fragmento,
        "tipo": source.tipo,
        "version_documento": source.document_version,
        "ultima_modificacion": source.last_modified,
        "version_confirmada": source.version_confirmed,
        "motivo_fallback": source.fallback_reason,
        "requisitos_cubiertos": list(source.covered_requirements),
    }


def _raw_candidate_payload(record: dict, question: str, rank: int) -> dict:
    """Present the Azure response without internal credentials or vectors."""
    return {
        "rango_azure": rank,
        "titulo": str(record.get("title") or "Documento sin título"),
        "pagina_o_fragmento": record.get("chunk_number"),
        "puntaje_azure": record.get("@search.score"),
        "puntaje_semantico": record.get("@search.reranker_score"),
        "enlace": str(record.get("source_url") or ""),
        "fragmento": _excerpt_around_query(str(record.get(CONTENT_FIELD) or ""), question),
    }


def retrieve_raw_azure_candidates(question: str, config: Config, limit: int = 10) -> list[dict]:
    """Read the initial Azure query used by Libras for comparison purposes.

    This is intentionally separate from the evidence selection below: Azure
    returns candidates, while Libras must still enforce its provenance and
    direct-evidence policy before responding to a person in Teams.
    """
    search_client = SearchClient(
        endpoint=config.azure_search_endpoint,
        index_name=config.azure_search_index_name,
        credential=_credential(config),
    )
    search_args = {
        "top": min(limit, CANDIDATE_POOL_SIZE),
        "select": SEARCH_SELECT_FIELDS,
        "connection_timeout": SEARCH_TIMEOUT_SECONDS,
        "read_timeout": SEARCH_TIMEOUT_SECONDS,
    }
    if config.azure_search_use_semantic:
        search_args.update(
            {
                "query_type": "semantic",
                "semantic_configuration_name": config.azure_search_semantic_configuration,
                "query_caption": "extractive",
            }
        )
    results = search_client.search(
        search_text=question,
        search_fields=["title", CONTENT_FIELD, "content_tokens"],
        **search_args,
    )
    return [_raw_candidate_payload(dict(result), question, rank) for rank, result in enumerate(results, start=1)]


def build_debug_payload(question: str, config: Config) -> dict:
    """Recupera y serializa la misma ruta de evidencia usada por Libras."""
    if not config.azure_search_configured:
        raise RuntimeError(
            "Azure AI Search no está configurado. Configure endpoint, índice y credencial "
            "(API key o Entra ID) antes de ejecutar el diagnóstico."
        )

    raw_candidates = retrieve_raw_azure_candidates(question, config)
    trace = retrieve_azure_search_evidence(question, config=config, return_trace=True)
    if not isinstance(trace, RetrievalTrace):  # Protección ante futuras estrategias.
        trace = RetrievalTrace(
            sources=trace,
            candidate_count=len(raw_candidates),
            direct_evidence_count=len(trace),
        )

    return {
        "pregunta": question,
        "origen": "azure_ai_search",
        "indice": config.azure_search_index_name,
        "estrategia": config.retrieval_strategy,
        "diagnostico": {
            "candidatos_recibidos": trace.candidate_count,
            "evidencias_aceptadas": trace.direct_evidence_count,
            "requisitos": trace.requirement_count,
            "requisitos_cubiertos": trace.covered_requirement_count,
            "motivos_de_descartes": trace.rejected_reasons,
            "etapas": trace.stage_counts,
        },
        "candidatos_crudos_de_azure": raw_candidates,
        "evidencia_que_recibe_el_bot": [_source_payload(source) for source in trace.sources],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consulta Azure AI Search con la misma recuperación de Libras (solo lectura)."
    )
    parser.add_argument("--question", required=True, help="Pregunta que se desea diagnosticar.")
    args = parser.parse_args()

    load_project_environment()
    try:
        payload = build_debug_payload(args.question, Config(os.environ))
    except Exception as error:
        print(f"Diagnóstico no completado: {error}", file=sys.stderr)
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
