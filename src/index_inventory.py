"""Create a non-content inventory of the configured Azure AI Search index.

The report is a read-only quality baseline. It deliberately excludes document
content, extracted fragments, credentials and SharePoint URLs, while retaining
the identifiers and metadata needed to audit provenance, duplicate documents
and chunk distribution before an index rebuild.
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from azure.search.documents import SearchClient

from azure_search import _credential
from config import Config, load_project_environment


INVENTORY_FIELDS = [
    "document_id",
    "title",
    "source_system",
    "folder_path",
    "drive_id",
    "document_type",
    "last_modified",
    "content_hash",
    "chunk_number",
]


def _document_title(title: str) -> str:
    """Remove the generated page suffix so one document has one title."""
    return str(title or "Documento sin título").split(" — Página ", 1)[0].split(
        " — Documento", 1
    )[0]


def _counter_summary(counter: Counter) -> dict[str, int]:
    return {
        str(key) if key not in {None, ""} else "[sin valor]": value
        for key, value in sorted(counter.items(), key=lambda item: str(item[0]).casefold())
    }


def build_inventory(records: Iterable[dict]) -> dict:
    """Aggregate index records into one non-sensitive row per document."""
    documents: dict[str, dict] = {}
    chunks_by_source: Counter = Counter()
    chunks_by_type: Counter = Counter()
    chunks_by_folder: Counter = Counter()

    for raw_record in records:
        record = dict(raw_record)
        document_id = str(record.get("document_id") or "").strip()
        if not document_id:
            # A chunk without a stable document identity cannot be safely
            # reconciled during reindexing. Keep it visible rather than hiding
            # it in a generic count.
            document_id = f"[sin document_id]::{record.get('title', '')}"

        source_system = str(record.get("source_system") or "")
        document_type = str(record.get("document_type") or "")
        folder_path = str(record.get("folder_path") or "")
        chunks_by_source[source_system] += 1
        chunks_by_type[document_type] += 1
        chunks_by_folder[folder_path] += 1

        document = documents.setdefault(
            document_id,
            {
                "document_id": document_id,
                "title": _document_title(record.get("title", "")),
                "source_system": source_system,
                "folder_path": folder_path,
                "drive_id": str(record.get("drive_id") or ""),
                "document_type": document_type,
                "last_modified": str(record.get("last_modified") or ""),
                "content_hash": str(record.get("content_hash") or ""),
                "chunk_count": 0,
                "missing_metadata": [],
            },
        )
        document["chunk_count"] += 1

    duplicate_hashes: dict[str, list[str]] = defaultdict(list)
    missing_metadata: Counter = Counter()
    for document in documents.values():
        document["missing_metadata"] = [
            field
            for field in ("source_system", "folder_path", "drive_id", "document_type", "content_hash")
            if not document[field]
        ]
        missing_metadata.update(document["missing_metadata"])
        if document["content_hash"]:
            duplicate_hashes[document["content_hash"]].append(document["document_id"])

    duplicate_documents = {
        content_hash: sorted(document_ids)
        for content_hash, document_ids in sorted(duplicate_hashes.items())
        if len(document_ids) > 1
    }
    document_rows = sorted(
        documents.values(), key=lambda document: (document["title"].casefold(), document["document_id"])
    )
    return {
        "schema_version": 1,
        "summary": {
            "document_count": len(document_rows),
            "chunk_count": sum(document["chunk_count"] for document in document_rows),
            "documents_with_missing_metadata": sum(
                1 for document in document_rows if document["missing_metadata"]
            ),
            "duplicate_content_hash_count": len(duplicate_documents),
            "chunks_by_source_system": _counter_summary(chunks_by_source),
            "chunks_by_document_type": _counter_summary(chunks_by_type),
            "chunks_by_folder_path": _counter_summary(chunks_by_folder),
            "missing_metadata_by_field": _counter_summary(missing_metadata),
        },
        "documents": document_rows,
        "duplicate_content_hashes": duplicate_documents,
    }


def retrieve_index_records(config) -> Iterable[dict]:
    """Read only metadata from every searchable item in the configured index."""
    if not config.azure_search_configured:
        raise RuntimeError("Azure AI Search no está configurado para generar el inventario.")
    client = SearchClient(
        endpoint=config.azure_search_endpoint,
        index_name=config.azure_search_index_name,
        credential=_credential(config),
    )
    return client.search(search_text="*", select=INVENTORY_FIELDS)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera un inventario no sensible y de solo lectura del índice de Libras."
    )
    parser.add_argument(
        "--output",
        default="output/inventario-indice-libras.json",
        help="Archivo JSON de salida; no se modifica Azure AI Search.",
    )
    parser.add_argument(
        "--use-current-environment",
        action="store_true",
        help=(
            "Usa únicamente las variables ya definidas en esta terminal; evita "
            "cargar archivos .env locales de desarrollo."
        ),
    )
    args = parser.parse_args()

    if not args.use_current_environment:
        load_project_environment()
    config = Config(os.environ)
    try:
        inventory = build_inventory(retrieve_index_records(config))
    except Exception:
        # Configuration and identity problems are operational diagnostics, not
        # reasons to print an endpoint, token path or provider internals in a
        # report that may be shared with the quality-review group.
        print(
            "No fue posible leer el índice. Verifique que esta sesión use la "
            "configuración autorizada del índice y una identidad con permiso de lectura."
        )
        raise SystemExit(1) from None
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = inventory["summary"]
    print(
        "Inventario creado: "
        f"{summary['document_count']} documentos, {summary['chunk_count']} fragmentos, "
        f"{summary['duplicate_content_hash_count']} hashes duplicados."
    )
    print(f"Salida: {output_path}")


if __name__ == "__main__":
    main()
