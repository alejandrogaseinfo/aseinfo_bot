"""Restore a previously verified Libras Azure AI Search backup.

This command only accepts a backup for the currently selected index and checks
its manifest before uploading.  ``--reset-index`` is explicit because it
deletes the configured index before the restore.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path

from azure.search.documents import SearchClient

from azure_search import _credential, reset_index
from config import Config, load_project_environment


def _load_verified_records(backup_dir: Path) -> tuple[dict, list[dict]]:
    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.exists():
        raise RuntimeError("El respaldo no contiene manifest.json.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload_path = backup_dir / str(manifest.get("payload") or "")
    if not payload_path.exists():
        raise RuntimeError("El respaldo no contiene el archivo de documentos indicado en el manifiesto.")
    digest = hashlib.sha256()
    records: list[dict] = []
    with gzip.open(payload_path, "rb") as payload:
        for line in payload:
            digest.update(line)
            records.append(json.loads(line))
    if len(records) != manifest.get("document_count") or digest.hexdigest() != manifest.get("record_sha256"):
        raise RuntimeError("El respaldo no superó la verificación de conteo o hash; no se restauró nada.")
    return manifest, records


def restore_index_backup(config: Config, backup_dir: Path, reset: bool = False) -> int:
    manifest, records = _load_verified_records(backup_dir)
    if manifest.get("index_name") != config.azure_search_index_name:
        raise RuntimeError("El respaldo pertenece a otro índice; no se restauró nada.")
    if reset:
        reset_index(config)
    search_client = SearchClient(
        endpoint=config.azure_search_endpoint,
        index_name=config.azure_search_index_name,
        credential=_credential(config),
    )
    for start in range(0, len(records), 500):
        results = search_client.upload_documents(documents=records[start : start + 500])
        failed = [result for result in results if not result.succeeded]
        if failed:
            raise RuntimeError(f"La restauración falló en el lote {start // 500 + 1}.")
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Restaura un respaldo verificado de Azure AI Search.")
    parser.add_argument("--backup-dir", required=True)
    parser.add_argument("--reset-index", action="store_true")
    parser.add_argument("--use-current-environment", action="store_true")
    args = parser.parse_args()
    if not args.use_current_environment:
        load_project_environment()
    config = Config(os.environ)
    if not config.azure_search_configured:
        raise RuntimeError("Se requiere una configuración válida de Azure AI Search.")
    restored = restore_index_backup(config, Path(args.backup_dir).resolve(), args.reset_index)
    print(f"Restauración completada: {restored} documentos.")


if __name__ == "__main__":
    main()
