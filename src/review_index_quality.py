"""Generate a non-destructive, evidence-backed review queue for Libras metadata."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from azure_search import _document_records


def build_review_queue(records: list[dict], dominant_chunk_threshold: int = 40) -> dict:
    by_document: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        by_document[str(record["document_id"])].append(record)
    hashes: Counter = Counter(
        str(group[0].get("content_hash") or "") for group in by_document.values()
    )
    queue: list[dict] = []
    for document_id, group in sorted(by_document.items(), key=lambda item: str(item[1][0].get("title", "")).casefold()):
        sample = group[0]
        reasons: list[str] = []
        if str(sample.get("quality_status") or "pendiente") == "pendiente":
            reasons.append("quality_status_pendiente")
        if sample.get("artifact_role") == "script" and not sample.get("operation"):
            reasons.append("script_sin_operacion_revisada")
        if len(group) >= dominant_chunk_threshold:
            reasons.append("documento_dominante")
        content_hash = str(sample.get("content_hash") or "")
        if content_hash and hashes[content_hash] > 1:
            reasons.append("duplicado_exactamente")
        if reasons:
            queue.append(
                {
                    "document_id": document_id,
                    "title": str(sample.get("title") or "").split(" — ", 1)[0],
                    "artifact_role": str(sample.get("artifact_role") or ""),
                    "chunk_count": len(group),
                    "quality_status": str(sample.get("quality_status") or "pendiente"),
                    "reasons": reasons,
                    "proposed_metadata": {
                        key: str(sample.get(key) or "")
                        for key in ("product", "module", "operation", "version", "country")
                    },
                    "proposal_evidence": {
                        "title": str(sample.get("title") or "").split(" — ", 1)[0],
                        "artifact_role_from_extension": str(sample.get("artifact_role") or ""),
                        "routine_identifiers_from_structure": str(sample.get("operation") or ""),
                    },
                    "review_decision": "pendiente",
                }
            )
    return {"schema_version": 1, "review_count": len(queue), "documents": queue}


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera la cola de revisión focalizada de Libras.")
    parser.add_argument("--source-dir", required=True, help="Staging autorizado de SharePoint.")
    parser.add_argument("--output", default="output/cola-revision-calidad-libras.json")
    parser.add_argument("--dominant-chunk-threshold", type=int, default=40)
    args = parser.parse_args()
    records = _document_records(Path(args.source_dir).resolve())
    queue = build_review_queue(records, args.dominant_chunk_threshold)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Cola creada: {queue['review_count']} documentos para revisión focalizada.")


if __name__ == "__main__":
    main()
