"""Synchronize readable files from the approved SharePoint folder.

Local development uses delegated device authentication. Production uses the
corporate App Registration with application permissions restricted to the
approved SharePoint site through ``Sites.Selected``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from pathlib import Path
from urllib.parse import quote

import msal
import requests
from config import Config, load_project_environment


GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
GRAPH_DELEGATED_SCOPE = ["https://graph.microsoft.com/Files.Read.All"]
GRAPH_APPLICATION_SCOPE = ["https://graph.microsoft.com/.default"]
SYNC_STATE_NAME = ".libras-sharepoint-sync-state.json"
DELETION_MANIFEST_NAME = ".libras-sharepoint-deletions.json"
CHANGE_MANIFEST_NAME = ".libras-sharepoint-changes.json"


SUPPORTED_EXTENSIONS = {
    ".aspx",
    ".bat",
    ".csv",
    ".docx",
    ".json",
    ".pdf",
    ".ps1",
    ".rdlc",
    ".sql",
    ".txt",
    ".xlsx",
    ".xml",
}
SCRIPT_EXTENSIONS = {".sql", ".ps1", ".bat"}


def _safe_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "documento"


def _descriptive_fields(item: dict) -> dict[str, str]:
    """Extract user-facing SharePoint columns despite internal-name changes."""
    list_item = item.get("listItem") or {}
    fields = list_item.get("fields") or item.get("fields") or {}
    if not isinstance(fields, dict):
        return {}
    result: dict[str, str] = {}
    for raw_name, raw_value in fields.items():
        if raw_value in (None, "") or str(raw_name).startswith("@odata"):
            continue
        name = re.sub(r"[^a-z0-9]", "", str(raw_name).casefold())
        value = str(raw_value).strip()
        if not value:
            continue
        if name.startswith("detalle") or name in {"description", "descripcion"} or "detail" in name:
            result.setdefault("description", value)
        elif name.startswith("dependencia") or name in {"dependency", "dependencia"}:
            result.setdefault("dependency", value)
    return result


class SharePointGraphClient:
    """Common Graph operations for the approved document library."""

    def __init__(self, config: Config, access_token: str, drive_id: str):
        self.config = config
        self.headers = {"Authorization": f"Bearer {access_token}"}
        self.drive_id = drive_id

    def _get(self, url: str) -> dict:
        response = requests.get(url, headers=self.headers, timeout=30)
        if response.status_code >= 400:
            raise RuntimeError(
                f"Microsoft Graph devolvió HTTP {response.status_code}: {response.text[:300]}"
            )
        return response.json()

    def _children_url(self, folder_path: str, drive_id: str | None = None) -> str:
        drive_id = drive_id or self.drive_id
        base = f"{GRAPH_ROOT}/drives/{drive_id}/root"
        if not folder_path:
            return f"{base}/children"
        return f"{base}:/{quote(folder_path)}:/children"

    def _enrich_script_fields(self, item: dict, drive_id: str) -> None:
        """Read custom list columns only for scripts, keeping sync bounded."""
        fields = _descriptive_fields(item)
        if not fields:
            try:
                list_item_url = (
                    f"{GRAPH_ROOT}/drives/{drive_id}/items/{item['id']}/listItem"
                    "?$expand=fields"
                )
                fields = _descriptive_fields({"listItem": self._get(list_item_url)})
            except Exception as error:
                # A missing list-column permission must not remove a readable
                # script from the knowledge base.
                print(
                    f"No se pudieron leer columnas descriptivas de {item.get('name', 'script')}: {error}",
                    flush=True,
                )
        if fields:
            item["_libras_description"] = fields.get("description", "")
            item["_libras_dependency"] = fields.get("dependency", "")

    def list_supported_files(
        self, folder_path: str | None = None, drive_id: str | None = None
    ) -> list[dict]:
        folder_path = self.config.sharepoint_folder_path if folder_path is None else folder_path
        drive_id = drive_id or self.drive_id
        pending = [self._children_url(folder_path, drive_id)]
        visited_urls: set[str] = set()
        files: list[dict] = []
        while pending:
            page_url = pending.pop()
            if page_url in visited_urls:
                continue
            visited_urls.add(page_url)
            if len(visited_urls) % 50 == 0:
                print(
                    f"Carpetas/páginas recorridas: {len(visited_urls)}",
                    flush=True,
                )
            page = self._get(page_url)
            for item in page.get("value", []):
                if "folder" in item and "remoteItem" not in item:
                    pending.append(f"{GRAPH_ROOT}/drives/{drive_id}/items/{item['id']}/children")
                elif "file" in item:
                    extension = Path(str(item.get("name", ""))).suffix.lower()
                    if extension in SUPPORTED_EXTENSIONS:
                        if extension in SCRIPT_EXTENSIONS:
                            self._enrich_script_fields(item, drive_id)
                        item["_libras_folder_path"] = folder_path
                        item["_libras_drive_id"] = drive_id
                        files.append(item)
            if page.get("@odata.nextLink"):
                pending.append(page["@odata.nextLink"])
        return files

    def list_pdfs(self) -> list[dict]:
        """Backward-compatible alias for callers that still expect this name."""
        return [item for item in self.list_supported_files() if item["name"].lower().endswith(".pdf")]

    def inventory(self, folder_path: str | None = None, drive_id: str | None = None) -> dict:
        """Enumerate the approved folder without downloading or writing files."""
        folder_path = self.config.sharepoint_folder_path if folder_path is None else folder_path
        drive_id = drive_id or self.drive_id
        pending = [self._children_url(folder_path, drive_id)]
        visited_urls: set[str] = set()
        files: list[dict] = []
        folder_count = 0
        while pending:
            page_url = pending.pop()
            if page_url in visited_urls:
                continue
            visited_urls.add(page_url)
            page = self._get(page_url)
            for item in page.get("value", []):
                if "folder" in item and "remoteItem" not in item:
                    folder_count += 1
                    pending.append(
                        f"{GRAPH_ROOT}/drives/{drive_id}/items/{item['id']}/children"
                    )
                elif "file" in item:
                    files.append(item)
            if page.get("@odata.nextLink"):
                pending.append(page["@odata.nextLink"])
        return {"folder_count": folder_count, "files": files}

    def download(self, item: dict, destination: Path) -> None:
        drive_id = item.get("_libras_drive_id") or self.drive_id
        content_url = f"{GRAPH_ROOT}/drives/{drive_id}/items/{item['id']}/content"
        response = requests.get(
            content_url, headers=self.headers, timeout=30, allow_redirects=False
        )
        response.raise_for_status()
        download_url = response.headers.get("location")
        if download_url:
            # Graph redirects to a short-lived SharePoint URL. Do not forward
            # the Graph bearer token to that host; the redirect URL carries
            # its own temporary authorization.
            response = requests.get(download_url, timeout=90, allow_redirects=True)
            response.raise_for_status()
        destination.write_bytes(response.content)


class SharePointDelegatedClient(SharePointGraphClient):
    def __init__(self, config: Config):
        if not config.sharepoint_tenant_id or not config.sharepoint_client_id:
            raise RuntimeError(
                "Faltan SHAREPOINT_TENANT_ID y SHAREPOINT_CLIENT_ID para Microsoft Graph."
            )
        application = msal.PublicClientApplication(
            client_id=config.sharepoint_client_id,
            authority=f"https://login.microsoftonline.com/{config.sharepoint_tenant_id}",
        )
        flow = application.initiate_device_flow(scopes=GRAPH_DELEGATED_SCOPE)
        if "message" not in flow:
            raise RuntimeError("No se pudo iniciar el inicio de sesión de Microsoft Graph.")
        print(flow["message"])
        token_result = application.acquire_token_by_device_flow(flow)
        access_token = token_result.get("access_token")
        if not access_token:
            description = token_result.get("error_description", "sin detalle")
            raise RuntimeError(f"Microsoft Graph no autorizó el acceso: {description}")
        # For a personal OneDrive the caller can omit the drive id; Graph
        # resolves it from the same delegated user that authorized the script.
        drive_id = config.sharepoint_drive_id
        if not drive_id:
            # Device flow is strictly a local-development convenience.
            provisional = SharePointGraphClient(config, access_token, "")
            drive_id = provisional._get(f"{GRAPH_ROOT}/me/drive")["id"]
        super().__init__(config, access_token, drive_id)


class SharePointApplicationClient(SharePointGraphClient):
    """Corporate production client using the approved App Registration."""

    def __init__(self, config: Config):
        if not config.sharepoint_application_configured:
            raise RuntimeError(
                "El modo application requiere tenant, client ID, secreto, site ID, drive ID y carpeta aprobada."
            )
        application = msal.ConfidentialClientApplication(
            client_id=config.sharepoint_client_id,
            authority=f"https://login.microsoftonline.com/{config.sharepoint_tenant_id}",
            client_credential=config.sharepoint_client_secret,
        )
        token_result = application.acquire_token_for_client(scopes=GRAPH_APPLICATION_SCOPE)
        access_token = token_result.get("access_token")
        if not access_token:
            description = token_result.get("error_description", "sin detalle")
            raise RuntimeError(f"Microsoft Graph no autorizó la aplicación: {description}")
        super().__init__(config, access_token, config.sharepoint_drive_id)


def create_sharepoint_client(config: Config) -> SharePointGraphClient:
    if config.sharepoint_auth_mode == "delegated":
        return SharePointDelegatedClient(config)
    if config.sharepoint_auth_mode == "application":
        return SharePointApplicationClient(config)
    raise RuntimeError("SHAREPOINT_AUTH_MODE debe ser delegated o application.")


def inventory_summary(
    client: SharePointGraphClient, folder_path: str, drive_id: str | None = None
) -> dict:
    """Return a compact, read-only inventory of the configured source folder."""
    inventory = client.inventory(folder_path, drive_id)
    files = inventory["files"]
    extensions = Counter(
        Path(str(item.get("name", ""))).suffix.lower() or "[sin extension]"
        for item in files
    )
    return {
        "folder_path": folder_path,
        "drive_id": drive_id or client.drive_id,
        "folder_count": inventory["folder_count"],
        "file_count": len(files),
        "files_by_extension": dict(sorted(extensions.items())),
        "pdf_count": extensions[".pdf"],
    }


def _source_key(folder_path: str, drive_id: str) -> tuple[str, str]:
    return (str(folder_path or "").strip("/"), str(drive_id or "").strip())


def _selected_sources(
    configured_sources: tuple[tuple[str, str], ...], source_indexes: tuple[int, ...] | None
) -> tuple[tuple[str, str], ...]:
    """Return requested one-based source indexes, preserving their priority."""
    if not source_indexes:
        return configured_sources
    selected: list[tuple[str, str]] = []
    for source_index in source_indexes:
        if source_index < 1 or source_index > len(configured_sources):
            raise ValueError(
                f"--source-index debe estar entre 1 y {len(configured_sources)}."
            )
        source = configured_sources[source_index - 1]
        if source not in selected:
            selected.append(source)
    return tuple(selected)


def _preserved_unselected_documents(
    previous_documents: dict[str, dict], selected_sources: tuple[tuple[str, str], ...]
) -> dict[str, dict]:
    """Keep omitted sources in state during a partial, priority sync.

    Unknown legacy state is preserved too. This fails closed rather than
    turning a source intentionally postponed to a later batch into a delete.
    """
    selected_keys = {_source_key(folder_path, drive_id) for folder_path, drive_id in selected_sources}
    preserved: dict[str, dict] = {}
    for document_id, state in previous_documents.items():
        if not isinstance(state, dict):
            preserved[document_id] = state
            continue
        drive_id = state.get("drive_id")
        folder_path = state.get("folder_path")
        if not drive_id and folder_path is None:
            preserved[document_id] = state
            continue
        if _source_key(folder_path or "", drive_id or "") not in selected_keys:
            preserved[document_id] = state
    return preserved


def _existing_review_if_current(
    metadata_path: Path, metadata_signature: dict[str, str]
) -> dict[str, str]:
    """Reuse a human review only while the SharePoint version is unchanged."""
    existing = _load_json(metadata_path)
    reviewed = existing.get("libras") if isinstance(existing, dict) else None
    if not isinstance(reviewed, dict):
        return {}
    comparable_keys = ("etag", "web_url", "last_modified", "folder_path", "drive_id")
    if any(
        str(existing.get(key) or "") != str(metadata_signature.get(key) or "")
        for key in comparable_keys
    ):
        return {}
    return {
        str(key): str(value).strip()
        for key, value in reviewed.items()
        if str(value).strip()
    }


def sync_pdfs(
    config: Config,
    output_dir: Path,
    source_indexes: tuple[int, ...] | None = None,
) -> int:
    """Synchronize readable files and emit durable change/deletion manifests.

    The durable production identity is pending the administrator requests. This
    local/delegated implementation nevertheless keeps the same document IDs,
    versions and deletion contract that the production job will use.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    client = create_sharepoint_client(config)
    list_files = (
        client.list_supported_files
        if hasattr(client, "list_supported_files")
        else client.list_pdfs
    )
    configured_sources = tuple(getattr(
        config,
        "sharepoint_sources",
        ((getattr(config, "sharepoint_folder_path", ""), client.drive_id),),
    ))
    sources = _selected_sources(configured_sources, source_indexes)
    state_path = output_dir / SYNC_STATE_NAME
    previous_state = _load_json(state_path)
    previous_documents = previous_state.get("documents", {})
    if not isinstance(previous_documents, dict):
        previous_documents = {}
    current_documents: dict[str, dict] = (
        _preserved_unselected_documents(previous_documents, sources)
        if len(sources) < len(configured_sources)
        else {}
    )
    pending_changes = _change_ids(output_dir / CHANGE_MANIFEST_NAME)
    pending_deletions = _deletion_ids(output_dir / DELETION_MANIFEST_NAME)
    changed_document_ids = set(pending_changes)
    # The durable document key depends on the complete approved scope, not on
    # how many sources happen to be refreshed in this invocation. Otherwise a
    # progressive one-source batch would silently switch from ``drive:item``
    # to ``item`` and create a second identity for the same SharePoint file.
    multiple_sources = len(configured_sources) > 1
    source_labels = {
        _source_key(folder_path, drive_id): label
        for (folder_path, drive_id), label in zip(
            configured_sources, getattr(config, "sharepoint_source_labels", ())
        )
        if label
    }
    file_count = 0

    for folder_path, drive_id in sources:
        source_label = source_labels.get(_source_key(folder_path, drive_id), "fuente autorizada")
        print(
            f"Sincronizando SharePoint: fuente={source_label} ruta={folder_path or '[raiz]'}",
            flush=True,
        )
        if hasattr(client, "list_supported_files"):
            try:
                source_files = list_files(folder_path, drive_id)
            except TypeError:
                source_files = list_files()
        else:
            source_files = list_files()
        print(f"Archivos legibles encontrados: {len(source_files)}", flush=True)

        for raw_item in source_files:
            # Keep the source attached even when a test or legacy client does
            # not add the internal synchronization markers itself.
            item = dict(raw_item)
            item.setdefault("_libras_folder_path", folder_path)
            item.setdefault("_libras_drive_id", drive_id)
            file_count += 1
            source_drive_id = item.get("_libras_drive_id") or client.drive_id
            # Drive item IDs are scoped to a library. Prefixing the item ID with
            # its drive keeps staging, sync state and Azure AI Search keys unique
            # when multiple SharePoint libraries are synchronized.
            document_id = (
                f"{source_drive_id}:{item['id']}" if multiple_sources else item["id"]
            )
            filename = f"{_safe_filename(document_id)}_{_safe_filename(item['name'])}"
            destination = output_dir / filename
            etag = item.get("eTag", "")
            prior = previous_documents.get(document_id, {})
            legacy_prior = {}
            if multiple_sources:
                # The previous single-library staging used the raw item ID.
                # Reuse that file during the one-time migration when its
                # SharePoint version and library match. Matching the stored
                # drive avoids confusing two libraries that happen to use the
                # same Graph item ID.
                legacy_candidate = previous_documents.get(item["id"], {})
                if (
                    isinstance(legacy_candidate, dict)
                    and legacy_candidate.get("drive_id") == source_drive_id
                ):
                    legacy_prior = legacy_candidate
                if not prior and legacy_prior:
                    prior = legacy_prior
            prior_filename = prior.get("filename", "")
            source_folder_path = (
                item["_libras_folder_path"]
                if "_libras_folder_path" in item
                else sources[0][0]
            )
            metadata_signature = {
                "filename": filename,
                "etag": etag,
                "web_url": item.get("webUrl", ""),
                "last_modified": item.get("lastModifiedDateTime", ""),
                "folder_path": source_folder_path,
                "drive_id": source_drive_id,
                "description": item.get("_libras_description", ""),
                "dependency": item.get("_libras_dependency", ""),
            }
            reused_legacy_file = False
            if prior_filename and prior_filename != filename:
                old_destination = output_dir / prior_filename
                old_metadata_path = old_destination.with_suffix(old_destination.suffix + ".metadata.json")
                reusable_legacy = bool(
                    legacy_prior
                    and (old_destination.exists() or destination.exists())
                    and prior.get("etag") == etag
                    and prior.get("web_url") == item.get("webUrl", "")
                    and prior.get("last_modified") == item.get("lastModifiedDateTime", "")
                    and prior.get("folder_path") == source_folder_path
                )
                if reusable_legacy:
                    if old_destination.exists() and not destination.exists():
                        old_destination.replace(destination)
                    new_metadata_path = destination.with_suffix(destination.suffix + ".metadata.json")
                    if old_metadata_path.exists():
                        old_metadata_path.replace(new_metadata_path)
                    reused_legacy_file = True
                else:
                    if old_destination.exists():
                        old_destination.unlink()
                    if old_metadata_path.exists():
                        old_metadata_path.unlink()
            comparison_prior = dict(prior)
            if reused_legacy_file:
                comparison_prior["filename"] = filename
                comparison_prior["drive_id"] = source_drive_id
            identity_migrated = bool(
                multiple_sources
                and legacy_prior
                and document_id not in previous_documents
            )
            # If a prior run already moved state to the drive-scoped key, the
            # raw legacy key is still pending deletion until Azure Search has
            # processed it. Keep marking its replacement as an upsert so a
            # retry can never delete the old chunks without writing the new
            # identity first.
            identity_reindex_pending = bool(
                multiple_sources and item["id"] in pending_deletions
            )
            has_changed = (
                not destination.exists()
                or any(comparison_prior.get(key) != value for key, value in metadata_signature.items())
            )
            if has_changed:
                client.download(item, destination)
            metadata_path = destination.with_suffix(destination.suffix + ".metadata.json")
            metadata = {
                "source_system": "sharepoint",
                "name": item["name"],
                "web_url": item.get("webUrl", ""),
                "document_id": document_id,
                "drive_item_id": item["id"],
                "drive_id": source_drive_id,
                "site_id": config.sharepoint_site_id,
                "folder_path": source_folder_path,
                "etag": etag,
                "last_modified": item.get("lastModifiedDateTime", ""),
                "description": item.get("_libras_description", ""),
                "dependency": item.get("_libras_dependency", ""),
            }
            reviewed = _existing_review_if_current(metadata_path, metadata_signature)
            if reviewed:
                metadata["libras"] = reviewed
            metadata_path.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            current_documents[document_id] = metadata_signature
            if has_changed or identity_migrated or identity_reindex_pending:
                changed_document_ids.add(document_id)
        print(
            f"Fuente completada: fuente={source_label} ruta={folder_path or '[raiz]'}",
            flush=True,
        )

    deleted_document_ids = sorted(
        pending_deletions.union(set(previous_documents).difference(current_documents))
    )
    changed_document_ids.difference_update(deleted_document_ids)
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
    _write_json(
        output_dir / CHANGE_MANIFEST_NAME,
        {"changed_document_ids": sorted(changed_document_ids)},
    )
    _write_json(state_path, {"documents": current_documents})
    return file_count


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


def _change_ids(path: Path) -> set[str]:
    payload = _load_json(path)
    document_ids = payload.get("changed_document_ids", [])
    if not isinstance(document_ids, list) or not all(isinstance(item, str) for item in document_ids):
        raise RuntimeError("El manifiesto de cambios debe contener changed_document_ids.")
    return {item for item in document_ids if item}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descarga archivos legibles autorizados de SharePoint para staging."
    )
    parser.add_argument("--output-dir", default="data/sharepoint", help="Carpeta local de staging.")
    parser.add_argument(
        "--source-index",
        action="append",
        type=int,
        dest="source_indexes",
        help=(
            "Índice de fuente configurada (base 1). Puede repetirse para una "
            "sincronización progresiva; las fuentes omitidas no se eliminan."
        ),
    )
    parser.add_argument(
        "--inventory",
        action="store_true",
        help="Enumera recursivamente la carpeta configurada sin descargar ni modificar archivos.",
    )
    parser.add_argument(
        "--use-current-environment",
        action="store_true",
        help=(
            "No carga archivos .env del proyecto. Úsalo solo cuando la configuración "
            "ya fue inyectada por el entorno de ejecución."
        ),
    )
    args = parser.parse_args()
    if not args.use_current_environment:
        load_project_environment()
    config = Config(os.environ)
    if args.inventory:
        client = create_sharepoint_client(config)
        sources = getattr(
            config,
            "sharepoint_sources",
            ((config.sharepoint_folder_path, client.drive_id),),
        )
        selected = _selected_sources(tuple(sources), tuple(args.source_indexes or ()))
        summaries = []
        for source_index, (folder_path, drive_id) in enumerate(sources, start=1):
            if (folder_path, drive_id) not in selected:
                continue
            summary = inventory_summary(client, folder_path, drive_id)
            summary["source_index"] = source_index
            summaries.append(summary)
        print(json.dumps(summaries, ensure_ascii=False))
        return
    count = sync_pdfs(
        config,
        Path(args.output_dir).resolve(),
        tuple(args.source_indexes or ()),
    )
    print(f"Descargados {count} archivo(s) legible(s) de SharePoint.")


if __name__ == "__main__":
    main()
