"""Download an approved SharePoint PDF folder with delegated user access.

This script intentionally does not use an application secret. The person who
runs it authenticates with device code and Graph only returns files that person
can already read. It creates local staging files plus safe metadata for the
Azure AI Search ingestion command.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from urllib.parse import quote

import msal
import requests
from config import Config, load_project_environment


GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
GRAPH_SCOPE = ["https://graph.microsoft.com/Files.Read.All"]
SYNC_STATE_NAME = ".libras-sharepoint-sync-state.json"
DELETION_MANIFEST_NAME = ".libras-sharepoint-deletions.json"


def _safe_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "documento.pdf"


class SharePointDelegatedClient:
    def __init__(self, config: Config):
        if not config.sharepoint_configured:
            raise RuntimeError(
                "Faltan SHAREPOINT_TENANT_ID, SHAREPOINT_CLIENT_ID, "
                "para iniciar Microsoft Graph."
            )
        self.config = config
        application = msal.PublicClientApplication(
            client_id=config.sharepoint_client_id,
            authority=f"https://login.microsoftonline.com/{config.sharepoint_tenant_id}",
        )
        flow = application.initiate_device_flow(scopes=GRAPH_SCOPE)
        if "message" not in flow:
            raise RuntimeError("No se pudo iniciar el inicio de sesión de Microsoft Graph.")
        print(flow["message"])
        token_result = application.acquire_token_by_device_flow(flow)
        access_token = token_result.get("access_token")
        if not access_token:
            description = token_result.get("error_description", "sin detalle")
            raise RuntimeError(f"Microsoft Graph no autorizó el acceso: {description}")
        self.headers = {"Authorization": f"Bearer {access_token}"}
        # For a personal OneDrive the caller can omit the drive id; Graph
        # resolves it from the same delegated user that authorized the script.
        self.drive_id = config.sharepoint_drive_id or self._get(f"{GRAPH_ROOT}/me/drive")["id"]

    def _get(self, url: str) -> dict:
        response = requests.get(url, headers=self.headers, timeout=30)
        if response.status_code >= 400:
            raise RuntimeError(f"Microsoft Graph devolvió HTTP {response.status_code}: {response.text[:300]}")
        return response.json()

    def _children_url(self, folder_path: str) -> str:
        base = f"{GRAPH_ROOT}/drives/{self.drive_id}/root"
        if not folder_path:
            return f"{base}/children"
        return f"{base}:/{quote(folder_path)}:/children"

    def list_pdfs(self) -> list[dict]:
        pending = [self._children_url(self.config.sharepoint_folder_path)]
        files: list[dict] = []
        while pending:
            page = self._get(pending.pop())
            for item in page.get("value", []):
                if "folder" in item:
                    pending.append(f"{GRAPH_ROOT}/drives/{self.drive_id}/items/{item['id']}/children")
                elif item.get("name", "").lower().endswith(".pdf") and "file" in item:
                    files.append(item)
            if page.get("@odata.nextLink"):
                pending.append(page["@odata.nextLink"])
        return files

    def download(self, item: dict, destination: Path) -> None:
        content_url = f"{GRAPH_ROOT}/drives/{self.drive_id}/items/{item['id']}/content"
        response = requests.get(content_url, headers=self.headers, timeout=90, allow_redirects=True)
        response.raise_for_status()
        destination.write_bytes(response.content)


def sync_pdfs(config: Config, output_dir: Path) -> int:
    """Synchronize only changed PDFs and emit tombstones for deleted files.

    The durable production identity is pending the administrator requests. This
    local/delegated implementation nevertheless keeps the same document IDs,
    versions and deletion contract that the production job will use.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    client = SharePointDelegatedClient(config)
    files = client.list_pdfs()
    state_path = output_dir / SYNC_STATE_NAME
    previous_state = _load_json(state_path)
    previous_documents = previous_state.get("documents", {})
    if not isinstance(previous_documents, dict):
        previous_documents = {}
    current_documents: dict[str, dict] = {}

    for item in files:
        # Prefix prevents collisions between same-named PDFs in different folders.
        filename = f"{item['id'][:8]}_{_safe_filename(item['name'])}"
        destination = output_dir / filename
        etag = item.get("eTag", "")
        prior = previous_documents.get(item["id"], {})
        prior_filename = prior.get("filename", "")
        if prior_filename and prior_filename != filename:
            old_destination = output_dir / prior_filename
            old_metadata_path = old_destination.with_suffix(old_destination.suffix + ".metadata.json")
            if old_destination.exists():
                old_destination.unlink()
            if old_metadata_path.exists():
                old_metadata_path.unlink()
        if not destination.exists() or prior.get("etag") != etag:
            client.download(item, destination)
        metadata = {
            "source_system": "sharepoint",
            "name": item["name"],
            "web_url": item.get("webUrl", ""),
            "document_id": item["id"],
            "drive_item_id": item["id"],
            "drive_id": client.drive_id,
            "site_id": config.sharepoint_site_id,
            "folder_path": config.sharepoint_folder_path,
            "etag": etag,
            "last_modified": item.get("lastModifiedDateTime", ""),
        }
        destination.with_suffix(destination.suffix + ".metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        current_documents[item["id"]] = {
            "filename": filename,
            "etag": etag,
        }

    pending_deletions = _deletion_ids(output_dir / DELETION_MANIFEST_NAME)
    deleted_document_ids = sorted(
        pending_deletions.union(set(previous_documents).difference(current_documents))
    )
    for document_id in deleted_document_ids:
        # A deletion can remain pending after the document has already been
        # removed from the last successful source snapshot. Retrying it is
        # safe and must not depend on that old entry still being present.
        prior = previous_documents.get(document_id, {})
        filename = prior.get("filename", "")
        if filename:
            destination = output_dir / filename
            metadata_path = destination.with_suffix(destination.suffix + ".metadata.json")
            if destination.exists():
                destination.unlink()
            if metadata_path.exists():
                metadata_path.unlink()

    _write_json(
        output_dir / DELETION_MANIFEST_NAME,
        {"deleted_document_ids": deleted_document_ids},
    )
    _write_json(state_path, {"documents": current_documents})
    return len(files)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"El estado de sincronización no es válido: {path}") from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"El estado de sincronización debe ser un objeto: {path}")
    return payload


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _deletion_ids(path: Path) -> set[str]:
    payload = _load_json(path)
    document_ids = payload.get("deleted_document_ids", [])
    if not isinstance(document_ids, list) or not all(isinstance(item, str) for item in document_ids):
        raise RuntimeError("El manifiesto de eliminaciones debe contener deleted_document_ids.")
    return {item for item in document_ids if item}


def main() -> None:
    parser = argparse.ArgumentParser(description="Descarga PDFs autorizados de SharePoint para staging.")
    parser.add_argument("--output-dir", default="data/sharepoint", help="Carpeta local de staging.")
    args = parser.parse_args()
    load_project_environment()
    count = sync_pdfs(Config(os.environ), Path(args.output_dir).resolve())
    print(f"Descargados {count} PDF(s) de SharePoint.")


if __name__ == "__main__":
    main()
