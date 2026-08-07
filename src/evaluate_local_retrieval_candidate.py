"""Evaluate the reproducible local v2 RAG candidate before promotion.

It uses the same staging, document-record builder and embedding dimensions as
production.  Retrieval runs locally so Azure AI Search Free does not need a
second full index.  The report contains only case IDs, document titles and
hashed query diagnostics; it never writes questions or fragments to telemetry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from azure_search import (
    CANDIDATE_POOL_SIZE,
    EXCLUDED_QUALITY_STATUSES,
    MAX_CANDIDATES_PER_DOCUMENT,
    _attach_embeddings,
    _filter_records_for_requested_country,
    _result_fragment,
    _v2_direct_text,
    _v2_semantic_candidate_payload,
    _v2_semantic_coverage_is_anchored,
    _v2_semantic_verifier_records,
    _v2_semantic_evidence,
    _v2_validated_evidence,
    _document_records,
)
from config import Config, load_project_environment
from evidence_verifier import verify_semantic_evidence
from evaluate_retrieval_quality import evaluate_cases, load_cases
from models import EvidenceSource, RetrievalTrace
from query_plan import build_query_plan, concept_keys, covered_requirements


def _overlap_score(record: dict, concepts: set[str]) -> float:
    title = record.get("_local_title_concepts") or set(concept_keys(str(record.get("title") or "")))
    searchable = record.get("_local_search_concepts") or set(
        concept_keys(
            " ".join(
                str(record.get(field) or "")
                for field in ("retrieval_text", "retrieval_concepts", "content_tokens")
            )
        )
    )
    return len(concepts.intersection(searchable)) * 8 + len(concepts.intersection(title)) * 12


def _cosine_score(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _local_v2_score(record: dict, coverage: tuple[str, ...], plan) -> float:
    plan_concepts = {
        concept for requirement in plan.requirements for concept in requirement.concepts
    }
    return (
        len(coverage) * 100
        + _overlap_score(record, plan_concepts)
        + max(0, CANDIDATE_POOL_SIZE - int(record.get("_vector_rank", CANDIDATE_POOL_SIZE))) * 0.5
        + max(0, CANDIDATE_POOL_SIZE - int(record.get("_lexical_rank", CANDIDATE_POOL_SIZE))) * 0.2
    )


class LocalCandidateRetriever:
    def __init__(
        self,
        records: list[dict],
        config: Config,
        use_embeddings: bool,
        cache_dir: Path | None = None,
        max_embedding_batches: int | None = None,
        use_semantic_verifier: bool = False,
        verifier_client=None,
    ) -> None:
        self.records = records
        self.config = config
        self.use_embeddings = use_embeddings
        self.embeddings_ready = True
        self.embedded_count = 0
        self.use_semantic_verifier = use_semantic_verifier
        self.verifier_client = verifier_client
        for record in self.records:
            record["_local_title_concepts"] = set(concept_keys(str(record.get("title") or "")))
            record["_local_search_concepts"] = set(
                concept_keys(
                    " ".join(
                        str(record.get(field) or "")
                        for field in ("retrieval_text", "retrieval_concepts", "content_tokens")
                    )
                )
            )
        if use_embeddings:
            self.embeddings_ready = self._attach_embeddings_with_resume(
                cache_dir, max_embedding_batches
            )

    def _attach_embeddings_with_resume(
        self, cache_dir: Path | None, max_batches: int | None
    ) -> bool:
        """Persist completed local batches so a time-limited run can resume."""
        if cache_dir is None:
            _attach_embeddings(self.records, self.config)
            self.embedded_count = len(self.records)
            return True
        from azure_search import _embed_texts

        cache_dir.mkdir(parents=True, exist_ok=True)
        vectors_path = cache_dir / "embeddings.json"
        embeddings_manifest_path = cache_dir / "embeddings-manifest.json"
        try:
            cached_vectors = json.loads(vectors_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            cached_vectors = {}
        try:
            embeddings_manifest = json.loads(embeddings_manifest_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            embeddings_manifest = {}
        expected_embedding_config = {
            "model": self.config.openai_embedding_model,
            "dimensions": self.config.openai_embedding_dimensions,
        }
        if embeddings_manifest != expected_embedding_config:
            cached_vectors = {}
            vectors_path.write_text("{}", encoding="utf-8")
            embeddings_manifest_path.write_text(
                json.dumps(expected_embedding_config), encoding="utf-8"
            )
        if not isinstance(cached_vectors, dict):
            cached_vectors = {}
        missing = [record for record in self.records if str(record["id"]) not in cached_vectors]
        for batch_number, offset in enumerate(range(0, len(missing), 20), start=1):
            if max_batches is not None and batch_number > max_batches:
                break
            batch = missing[offset : offset + 20]
            embeddings = _embed_texts(
                [
                    "\n".join(
                        str(record.get(field) or "")
                        for field in ("title", "retrieval_text", "document_context", "content")
                    )
                    for record in batch
                ],
                self.config,
            )
            if len(embeddings) != len(batch):
                raise RuntimeError("No se recibió un embedding para cada fragmento local.")
            for record, embedding in zip(batch, embeddings):
                cached_vectors[str(record["id"])] = embedding
            vectors_path.write_text(json.dumps(cached_vectors), encoding="utf-8")
        self.embedded_count = len(cached_vectors)
        if self.embedded_count < len(self.records):
            return False
        for record in self.records:
            record["content_vector"] = cached_vectors[str(record["id"])]
        return True

    def __call__(self, user_message: str) -> RetrievalTrace:
        plan = build_query_plan(user_message)
        query_concepts = set(concept_keys(" ".join(plan.retrieval_queries)))
        lexical_ranked = sorted(
            (
                (_overlap_score(record, query_concepts), record)
                for record in self.records
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        candidates_by_id: dict[str, dict] = {}
        for rank, (score, record) in enumerate(lexical_ranked, start=1):
            if score <= 0 or rank > CANDIDATE_POOL_SIZE:
                break
            copy = dict(record)
            copy["_lexical_rank"] = rank
            candidates_by_id[str(copy["id"])] = copy

        if self.use_embeddings:
            from azure_search import _embed_texts

            question_embedding = _embed_texts([plan.raw_message], self.config)[0]
            vector_ranked = sorted(
                (
                    (_cosine_score(question_embedding, record["content_vector"]), record)
                    for record in self.records
                ),
                key=lambda item: item[0],
                reverse=True,
            )
            for rank, (_, record) in enumerate(vector_ranked[:CANDIDATE_POOL_SIZE], start=1):
                existing = candidates_by_id.setdefault(str(record["id"]), dict(record))
                existing["_vector_rank"] = rank

        candidates = _filter_records_for_requested_country(
            list(candidates_by_id.values()), user_message
        )
        direct_records: list[tuple[float, dict, tuple[str, ...], str]] = []
        semantic_candidates: list[dict] = []
        rejected: dict[str, int] = {}
        for record in candidates:
            quality_status = str(record.get("quality_status") or "pendiente").casefold()
            if quality_status in EXCLUDED_QUALITY_STATUSES:
                rejected["quality_status"] = rejected.get("quality_status", 0) + 1
                continue
            if str(record.get("evidence_kind") or "primary").casefold() in {"navigation", "reference"}:
                rejected["evidence_kind"] = rejected.get("evidence_kind", 0) + 1
                continue
            coverage = covered_requirements(plan, _v2_direct_text(record))
            if not coverage:
                semantic_candidates.append(record)
                continue
            direct_records.append((_local_v2_score(record, coverage, plan), record, coverage, "deterministic"))

        if self.use_semantic_verifier and semantic_candidates:
            verifier_records = _v2_semantic_verifier_records(semantic_candidates, plan)
            try:
                verdicts = verify_semantic_evidence(
                    plan,
                    [_v2_semantic_candidate_payload(record, plan) for record in verifier_records],
                    self.verifier_client,
                    self.config.evidence_verifier_model_name,
                )
                for record in verifier_records:
                    coverage = verdicts.get(str(record.get("id") or ""), ())
                    if coverage and _v2_semantic_coverage_is_anchored(record, plan, coverage):
                        direct_records.append(
                            (_local_v2_score(record, coverage, plan), record, coverage, "semantic")
                        )
            except Exception:
                rejected["semantic_verifier_failed"] = rejected.get("semantic_verifier_failed", 0) + 1
        rejected["insufficient_direct_evidence"] = (
            rejected.get("insufficient_direct_evidence", 0) + len(semantic_candidates)
        )

        direct_records.sort(key=lambda item: item[0], reverse=True)
        sources: list[EvidenceSource] = []
        covered: set[str] = set()
        sources_per_document: dict[str, int] = {}
        for _, record, coverage, verification_mode in direct_records:
            document_key = str(record.get("document_id") or record.get("id") or "")
            if sources_per_document.get(document_key, 0) >= MAX_CANDIDATES_PER_DOCUMENT:
                rejected["document_diversity"] = rejected.get("document_diversity", 0) + 1
                continue
            fragment, validated_coverage = (
                _v2_semantic_evidence(record, plan, coverage)
                if verification_mode == "semantic"
                else _v2_validated_evidence(record, plan)
            )
            if not fragment or not validated_coverage:
                rejected["fragment_without_direct_coverage"] = rejected.get("fragment_without_direct_coverage", 0) + 1
                continue
            if set(validated_coverage).issubset(covered):
                rejected["redundant_direct_evidence"] = rejected.get("redundant_direct_evidence", 0) + 1
                continue
            sources.append(
                EvidenceSource(
                    tipo="sharepoint" if record.get("source_system") == "sharepoint" else "documento",
                    titulo=str(record.get("title") or "Documento sin título"),
                    ubicacion=str(record.get("source_url") or "staging local"),
                    fragmento=fragment,
                    source_system=str(record.get("source_system") or ""),
                    document_id=str(record.get("document_id") or ""),
                    document_version=str(record.get("document_version") or ""),
                    last_modified=str(record.get("last_modified") or ""),
                    document_type=str(record.get("document_type") or ""),
                    folder_path=str(record.get("folder_path") or ""),
                    artifact_role=str(record.get("artifact_role") or ""),
                    quality_status=str(record.get("quality_status") or ""),
                    evidence_kind=str(record.get("evidence_kind") or ""),
                    covered_requirements=validated_coverage,
                )
            )
            covered.update(validated_coverage)
            sources_per_document[document_key] = sources_per_document.get(document_key, 0) + 1
            if set(plan.requirement_ids).issubset(covered) or len(sources) == 3:
                break
        return RetrievalTrace(
            sources=sources,
            query_hash=plan.query_hash,
            candidate_count=len(candidates),
            direct_evidence_count=len(sources),
            requirement_count=len(plan.requirements),
            covered_requirement_count=len(covered),
            rejected_reasons=rejected,
        )


def _staging_signature(source_dir: Path) -> str:
    digest = hashlib.sha256()
    supported_suffixes = {
        ".metadata.json", ".sql", ".pdf", ".docx", ".xlsx", ".csv", ".txt",
        ".json", ".xml", ".aspx", ".ps1", ".bat", ".rdlc",
    }
    for path in sorted(source_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in supported_suffixes:
            continue
        relative = path.relative_to(source_dir).as_posix()
        stat = path.stat()
        digest.update(f"{relative}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode("utf-8"))
    return digest.hexdigest()


def _load_or_build_records(source_dir: Path, cache_dir: Path | None) -> list[dict]:
    if cache_dir is None:
        return _document_records(source_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = cache_dir / "records-manifest.json"
    records_path = cache_dir / "records.json"
    signature = _staging_signature(source_dir)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("staging_signature") == signature and records_path.exists():
            return json.loads(records_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    records = _document_records(source_dir)
    records_path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    manifest_path.write_text(
        json.dumps({"staging_signature": signature, "record_count": len(records)}), encoding="utf-8"
    )
    # A new source signature invalidates any vectors from an older corpus.
    (cache_dir / "embeddings.json").write_text("{}", encoding="utf-8")
    return records


def promotion_gates(report: dict) -> dict:
    summary = report["summary"]
    evidence_results = [result for result in report["results"] if result["expected"] == "evidence"]
    correct_direct_sources = sum(
        result["passed"] and (result["direct_evidence_count"] or 0) > 0
        for result in evidence_results
    )
    direct_source_rate = (
        correct_direct_sources / len(evidence_results) if evidence_results else 0.0
    )
    unsupported_sources = sum(
        result["evidence_count"] > 0 and (result["direct_evidence_count"] or 0) == 0
        for result in report["results"]
    )
    values = {
        "candidate_document_top3": summary["candidate_document_recall"] or 0.0,
        "direct_correct_source": direct_source_rate,
        "correct_abstention": summary["correct_abstention_rate"] or 0.0,
        "unsupported_sources": unsupported_sources,
    }
    return {
        "values": values,
        "passed": (
            values["candidate_document_top3"] >= 0.90
            and values["direct_correct_source"] >= 0.95
            and values["correct_abstention"] >= 0.95
            and values["unsupported_sources"] == 0
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evalúa el candidato local v2 de Libras.")
    parser.add_argument("--source-dir", required=True, help="Staging completo y autorizado de SharePoint.")
    parser.add_argument("--cases", required=True)
    parser.add_argument("--output", default="output/evaluacion-candidato-local-libras.json")
    parser.add_argument("--without-embeddings", action="store_true")
    parser.add_argument("--use-llm-evidence-verifier", action="store_true")
    parser.add_argument(
        "--embedding-dimensions",
        type=int,
        help="Dimensión confirmada del índice productivo; obligatoria al medir con embeddings.",
    )
    parser.add_argument(
        "--cache-dir",
        help="Caché local reanudable de fragmentos y embeddings; no se envía ni se usa en producción.",
    )
    parser.add_argument(
        "--embedding-batches",
        type=int,
        help="Máximo de lotes de 20 fragmentos por ejecución; permite reanudar sin recomputar.",
    )
    parser.add_argument("--assert-promotion-gates", action="store_true")
    parser.add_argument("--use-current-environment", action="store_true")
    args = parser.parse_args()
    if not args.use_current_environment:
        load_project_environment()
    config = Config(os.environ)
    if not args.without_embeddings:
        if not args.embedding_dimensions or args.embedding_dimensions <= 0:
            raise RuntimeError(
                "La evaluación vectorial requiere --embedding-dimensions con la dimensión confirmada de producción."
            )
        config.openai_embedding_dimensions = args.embedding_dimensions
    config.use_llm_evidence_verifier = args.use_llm_evidence_verifier
    source_dir = Path(args.source_dir).resolve()
    cache_dir = Path(args.cache_dir).resolve() if args.cache_dir else None
    records = _load_or_build_records(source_dir, cache_dir)
    verifier_client = None
    if args.use_llm_evidence_verifier:
        from azure_search import _embedding_client

        verifier_client = _embedding_client(config)
    retriever = LocalCandidateRetriever(
        records,
        config,
        use_embeddings=not args.without_embeddings,
        cache_dir=cache_dir,
        max_embedding_batches=args.embedding_batches,
        use_semantic_verifier=args.use_llm_evidence_verifier,
        verifier_client=verifier_client,
    )
    if not args.without_embeddings and not retriever.embeddings_ready:
        progress = {
            "status": "embedding_pending",
            "candidate": {
                "record_count": len(records),
                "embedded_count": retriever.embedded_count,
                "embedding_dimensions": config.openai_embedding_dimensions,
            },
        }
        output = Path(args.output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            f"Embeddings locales en progreso: {retriever.embedded_count}/{len(records)} fragmentos. "
            "Ejecute de nuevo el mismo comando para reanudar."
        )
        return
    report = evaluate_cases(load_cases(Path(args.cases).resolve()), retriever)
    report["candidate"] = {
        "record_count": len(records),
        "embedding_dimensions": config.openai_embedding_dimensions if not args.without_embeddings else None,
        "embedding_enabled": not args.without_embeddings,
    }
    report["promotion_gates"] = promotion_gates(report)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Candidato local evaluado: {report['summary']['passed_count']}/{report['summary']['case_count']} "
        f"casos; puertas={'aprobadas' if report['promotion_gates']['passed'] else 'bloqueadas'}."
    )
    if args.assert_promotion_gates and not report["promotion_gates"]["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
