"""Export a verifiable backup of the configured Azure AI Search index.

The command is intentionally read-only against Azure AI Search.  The backup
contains every retrievable field, including vectors when the service exposes
them, and a manifest with a deterministic hash for rollback verification.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient

from azure_search import _credential
from config import Config, load_project_environment


def _canonical_line(record: dict) -> bytes:
    return (json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def export_index_backup(config: Config, output_dir: Path) -> dict:
    """Export current index documents and return a non-secret manifest."""
    output_dir.mkdir(parents=True, exist_ok=True)
    index_client = SearchIndexClient(
        endpoint=config.azure_search_endpoint, credential=_credential(config)
    )
    index = index_client.get_index(config.azure_search_index_name)
    field_names = [
        field.name
        for field in index.fields
        if field.name and getattr(field, "retrievable", None) is not False
    ]
    if "id" not in field_names:
        field_names.insert(0, "id")

    payload_path = output_dir / "index-documents.jsonl.gz"
    digest = hashlib.sha256()
    count = 0
    search_client = SearchClient(
        endpoint=config.azure_search_endpoint,
        index_name=config.azure_search_index_name,
        credential=_credential(config),
    )
    # Azure AI Search limits a single search response to 1,000 records.  A
    # backup must page through the complete index and prove its count before
    # it can be used as a rollback artifact.
    expected_count = search_client.get_document_count()
    page_size = 1_000
    seen_ids: set[str] = set()
    with gzip.open(payload_path, "wb") as output:
        for offset in range(0, expected_count, page_size):
            results = search_client.search(
                search_text="*",
                select=field_names,
                top=page_size,
                skip=offset,
            )
            page_count = 0
            for item in results:
                record = dict(item)
                record_id = str(record.get("id") or "")
                if not record_id or record_id in seen_ids:
                    raise RuntimeError(
                        "La paginación del respaldo produjo un identificador vacío o repetido; "
                        "no se generó un respaldo utilizable."
                    )
                seen_ids.add(record_id)
                line = _canonical_line(record)
                output.write(line)
                digest.update(line)
                count += 1
                page_count += 1
            if page_count == 0:
                raise RuntimeError(
                    "La paginación del respaldo terminó antes del conteo informado por Azure AI Search."
                )

    if count != expected_count:
        raise RuntimeError(
            f"El respaldo contiene {count} registros, pero el índice informó {expected_count}; "
            "no se generó un respaldo utilizable."
        )

    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "index_name": config.azure_search_index_name,
        "document_count": count,
        "expected_document_count": expected_count,
        "record_sha256": digest.hexdigest(),
        "fields": field_names,
        "payload": payload_path.name,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Respalda un índice de Azure AI Search sin modificarlo.")
    parser.add_argument("--output-dir", required=True, help="Directorio local nuevo o vacío para el respaldo.")
    parser.add_argument("--use-current-environment", action="store_true")
    args = parser.parse_args()
    if not args.use_current_environment:
        load_project_environment()
    config = Config(os.environ)
    if not config.azure_search_configured:
        raise RuntimeError("Se requiere una configuración válida de Azure AI Search.")
    manifest = export_index_backup(config, Path(args.output_dir).resolve())
    print(
        f"Respaldo verificado creado: índice={manifest['index_name']} "
        f"documentos={manifest['document_count']} hash={manifest['record_sha256']}."
    )


if __name__ == "__main__":
    main()
