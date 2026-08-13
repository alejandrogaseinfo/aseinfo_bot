"""Experimental AI-first retrieval pipeline.

This module is deliberately separate from the legacy deterministic path.  It
retrieves a broad, bounded Azure AI Search candidate set, applies only the
security/provenance controls that must precede a model, and lets a judge select
evidence.  The local validator remains authoritative for the judge contract.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

from azure_search import (
    CANDIDATE_POOL_SIZE,
    CONTENT_FIELD,
    CONTENT_VECTOR_FIELD,
    CONTEXT_FIELD,
    SEARCH_SELECT_FIELDS,
    _credential,
    _embed_texts,
    _record_contains_document_injection,
    _record_has_authorized_provenance,
)
from document_index import tokenize
from evidence_verifier import _redact
from models import EvidenceSource
from query_plan import QueryPlan, build_query_plan


MAX_AI_FIRST_CANDIDATES = 12
MAX_AI_FIRST_FRAGMENT_CHARS = 1_200
MAX_AI_FIRST_CONTEXT_CHARS = 400
MIN_JUDGE_CONFIDENCE = 0.80
_VERSION_PATTERN = re.compile(r"(?<![\d.])(\d+(?:\.\d+){2,})(?!\d|\.\d)")


JUDGE_SYSTEM_PROMPT = """
Eres el juez de evidencia de Libras. Selecciona únicamente candidatos
proporcionados por Azure AI Search que puedan servir para responder la pregunta.
No inventes documentos, IDs, requisitos ni hechos. Puedes seleccionar varios
fragmentos y versiones si son pertinentes; no debes resolver la pregunta en tu
respuesta.

Devuelve solamente JSON con este contrato exacto:
{"selections":[{"candidate_id":"c01","requirements":["r1"],"confidence":0.0}]}

Usa exclusivamente los candidate_id y requirement_id recibidos. Si la
evidencia no basta, devuelve {"selections":[]}. La confianza debe estar entre
0 y 1; no selecciones candidatos con confianza menor que 0.80. La versión
explícita solicitada por el usuario debe coincidir con la identidad del
documento, no solo aparecer mencionada dentro del fragmento.
""".strip()


@dataclass(frozen=True)
class AIFirstCandidate:
    candidate_id: str
    source: EvidenceSource
    record: dict
    payload: dict[str, str]


@dataclass
class AIFirstRetrieval:
    candidates: list[AIFirstCandidate] = field(default_factory=list)
    raw_candidate_count: int = 0
    rejected_reasons: dict[str, int] = field(default_factory=dict)


@dataclass
class AIFirstJudgeResult:
    plan: QueryPlan
    selected: list[AIFirstCandidate] = field(default_factory=list)
    selected_requirements: dict[str, tuple[str, ...]] = field(default_factory=dict)
    abstained: bool = False
    validator_rejections: dict[str, int] = field(default_factory=dict)


def _bounded_text(value: object, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return str(_redact(text))[:limit]


def _record_version_matches(record: dict, requested_version: str) -> bool:
    """Validate explicit version against identity metadata, never body prose."""
    metadata = " ".join(
        str(record.get(field) or "")
        for field in (
            "title",
            "version",
            "document_version",
            "product_version",
            "release_version",
            "metadata_version",
        )
    )
    return requested_version.casefold() in {
        match.group(1).casefold() for match in _VERSION_PATTERN.finditer(metadata)
    }


def _source_from_record(record: dict) -> EvidenceSource:
    return EvidenceSource(
        tipo="sharepoint" if record.get("source_system") == "sharepoint" else "azure_ai_search",
        titulo=_bounded_text(record.get("title") or "Documento sin título", 300),
        ubicacion=str(record.get("source_url") or "Azure AI Search"),
        fragmento=_bounded_text(record.get(CONTENT_FIELD) or record.get(CONTEXT_FIELD), MAX_AI_FIRST_FRAGMENT_CHARS),
        source_system=str(record.get("source_system") or ""),
        document_id=str(record.get("document_id") or ""),
        document_version=str(record.get("document_version") or ""),
        last_modified=str(record.get("last_modified") or ""),
        document_type=str(record.get("document_type") or ""),
        folder_path=str(record.get("folder_path") or ""),
        version_confirmed=None,
    )


def retrieve_ai_first_candidates(
    user_message: str, config, client=None, limit: int = MAX_AI_FIRST_CANDIDATES
) -> AIFirstRetrieval:
    """Retrieve broad Azure candidates with only pre-judge safety controls."""
    if not getattr(config, "azure_search_enabled", False):
        return AIFirstRetrieval(rejected_reasons={"azure_unavailable": 1})

    search_client = SearchClient(
        endpoint=config.azure_search_endpoint,
        index_name=config.azure_search_index_name,
        credential=_credential(config),
    )
    search_args = {
        "top": min(CANDIDATE_POOL_SIZE, 40),
        "select": SEARCH_SELECT_FIELDS,
        "connection_timeout": 10,
        "read_timeout": 10,
        "search_mode": "any",
    }
    records_by_id: dict[str, dict] = {}
    rank_by_id: dict[str, int] = {}
    queries = [user_message]
    # Keep the second pass generic. The experimental route must not inherit
    # case-specific aliases or literal-coverage gates from legacy ranking.
    focused = " ".join(dict.fromkeys(tokenize(user_message)))
    if focused and focused.casefold() != user_message.casefold():
        queries.append(focused)
    for query_rank, query in enumerate(queries):
        try:
            results = search_client.search(
                search_text=query,
                search_fields=["title", CONTENT_FIELD, "content_tokens"],
                **search_args,
            )
            for rank, result in enumerate(results, start=1):
                record = dict(result)
                record_id = str(record.get("id") or "")
                if not record_id:
                    continue
                records_by_id.setdefault(record_id, record).update(record)
                rank_by_id[record_id] = min(rank_by_id.get(record_id, 10_000), rank + (query_rank * 100))
        except Exception:
            continue

    # Vector retrieval is a recall aid only. Its results are not judged or
    # discarded by semantic coverage here.
    try:
        embedding = _embed_texts([user_message], config, client=client)[0]
        vector_query = VectorizedQuery(
            vector=embedding,
            k_nearest_neighbors=min(CANDIDATE_POOL_SIZE, 40),
            fields=CONTENT_VECTOR_FIELD,
        )
        for rank, result in enumerate(
            search_client.search(search_text=None, vector_queries=[vector_query], **search_args),
            start=1,
        ):
            record = dict(result)
            record_id = str(record.get("id") or "")
            if not record_id:
                continue
            records_by_id.setdefault(record_id, record).update(record)
            rank_by_id[record_id] = min(rank_by_id.get(record_id, 10_000), rank + 200)
    except Exception:
        pass

    rejected: dict[str, int] = {}
    allowed_sources = getattr(config, "sharepoint_sources", None)
    if allowed_sources is None:
        allowed_sources = tuple(getattr(config, "sharepoint_folder_paths", ()) or ())
    allowed_labels = tuple(getattr(config, "sharepoint_source_labels", ()) or ())
    candidates: list[AIFirstCandidate] = []
    ordered_records = sorted(records_by_id.values(), key=lambda item: rank_by_id.get(str(item.get("id") or ""), 10_000))
    for record in ordered_records:
        if not _record_has_authorized_provenance(record, allowed_sources, allowed_labels):
            rejected["provenance"] = rejected.get("provenance", 0) + 1
            continue
        if _record_contains_document_injection(record):
            rejected["document_injection"] = rejected.get("document_injection", 0) + 1
            continue
        source = _source_from_record(record)
        if not source.fragmento:
            rejected["empty_fragment"] = rejected.get("empty_fragment", 0) + 1
            continue
        candidate_id = f"c{len(candidates) + 1:02d}"
        payload = {
            "candidate_id": candidate_id,
            "title": _bounded_text(record.get("title"), 300),
            "fragment": source.fragmento,
            "metadata": _bounded_text(record.get(CONTEXT_FIELD), MAX_AI_FIRST_CONTEXT_CHARS),
        }
        candidates.append(
            AIFirstCandidate(
                candidate_id=candidate_id,
                source=source,
                record=record,
                payload=payload,
            )
        )
        if len(candidates) >= max(1, min(limit, MAX_AI_FIRST_CANDIDATES)):
            break
    return AIFirstRetrieval(
        candidates=candidates,
        raw_candidate_count=len(records_by_id),
        rejected_reasons=rejected,
    )


def judge_ai_first_candidates(
    user_message: str,
    retrieval: AIFirstRetrieval,
    client,
    model: str,
) -> AIFirstJudgeResult:
    """Ask the judge to select candidates, then validate its closed contract."""
    plan = build_query_plan(user_message)
    result = AIFirstJudgeResult(plan=plan)
    if not retrieval.candidates or client is None:
        result.abstained = True
        result.validator_rejections["sin_candidatos"] = 1
        return result
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "question": user_message,
                            "requirements": [
                                {"requirement_id": req.identifier, "text": req.text}
                                for req in plan.requirements
                            ],
                            "candidates": [candidate.payload for candidate in retrieval.candidates],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        )
        payload = json.loads(response.choices[0].message.content or "{}")
    except Exception:
        result.abstained = True
        result.validator_rejections["json_invalido"] = 1
        return result
    if not isinstance(payload, dict) or set(payload) != {"selections"} or not isinstance(payload["selections"], list):
        result.abstained = True
        result.validator_rejections["json_invalido"] = 1
        return result

    allowed_candidates = {candidate.candidate_id: candidate for candidate in retrieval.candidates}
    allowed_requirements = set(plan.requirement_ids)
    seen_ids: set[str] = set()
    requested_version = plan.version
    for selection in payload["selections"]:
        if not isinstance(selection, dict) or set(selection) != {"candidate_id", "requirements", "confidence"}:
            result.abstained = True
            result.validator_rejections["contrato_invalido"] = 1
            result.selected.clear()
            return result
        candidate_id = str(selection.get("candidate_id") or "")
        requirements = selection.get("requirements")
        confidence = selection.get("confidence")
        if candidate_id in seen_ids or candidate_id not in allowed_candidates:
            result.abstained = True
            result.validator_rejections["id_desconocido"] = 1
            result.selected.clear()
            return result
        if (
            not isinstance(requirements, list)
            or not requirements
            or any(str(item) not in allowed_requirements for item in requirements)
        ):
            result.abstained = True
            result.validator_rejections["requisitos_no_permitidos"] = 1
            result.selected.clear()
            return result
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or confidence < MIN_JUDGE_CONFIDENCE or confidence > 1:
            result.abstained = True
            result.validator_rejections["confianza_insuficiente"] = 1
            result.selected.clear()
            return result
        candidate = allowed_candidates[candidate_id]
        if requested_version and not _record_version_matches(candidate.record, requested_version):
            result.validator_rejections["version_incompatible"] = result.validator_rejections.get("version_incompatible", 0) + 1
            seen_ids.add(candidate_id)
            continue
        normalized_requirements = tuple(dict.fromkeys(str(item) for item in requirements))
        result.selected.append(candidate)
        result.selected_requirements[candidate_id] = normalized_requirements
        seen_ids.add(candidate_id)

    if not result.selected:
        result.abstained = True
    return result


def mark_confirmed_versions(result: AIFirstJudgeResult) -> list[EvidenceSource]:
    """Return locally validated sources with explicit-version metadata marked."""
    sources: list[EvidenceSource] = []
    for candidate in result.selected:
        source = candidate.source
        if result.plan.version:
            source.version_confirmed = True
        source.covered_requirements = result.selected_requirements.get(candidate.candidate_id, ())
        sources.append(source)
    return sources
