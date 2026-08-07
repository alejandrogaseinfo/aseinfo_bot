"""Apply explicitly approved Libras metadata decisions to staging sidecars."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from azure_search import SUPPORTED_EXTENSIONS, _metadata_for


REVIEWABLE_FIELDS = {
    "product",
    "module",
    "operation",
    "artifact_role",
    "version",
    "country",
    "quality_status",
}
VALID_DECISIONS = {"aprobado", "pendiente", "fuera_de_alcance", "duplicado", "obsoleto"}
CHANGE_MANIFEST_NAME = ".libras-sharepoint-changes.json"


def _documents_by_id(source_dir: Path) -> dict[str, Path]:
    documents: dict[str, Path] = {}
    for path in source_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        metadata = _metadata_for(path)
        document_id = str(metadata.get("document_id") or "")
        if document_id:
            documents[document_id] = path
    return documents


def apply_review_decisions(source_dir: Path, decisions_path: Path) -> int:
    payload = json.loads(decisions_path.read_text(encoding="utf-8"))
    decisions = payload.get("decisions") if isinstance(payload, dict) else None
    if not isinstance(decisions, list):
        raise ValueError("El archivo de revisión requiere un arreglo decisions.")
    documents = _documents_by_id(source_dir)
    applied = 0
    changed_document_ids: set[str] = set()
    for decision in decisions:
        if not isinstance(decision, dict):
            raise ValueError("Cada decisión debe ser un objeto.")
        document_id = str(decision.get("document_id") or "")
        status = str(decision.get("decision") or "").casefold()
        metadata_values = decision.get("metadata", {})
        if not document_id or status not in VALID_DECISIONS or not isinstance(metadata_values, dict):
            raise ValueError("Decisión de revisión inválida.")
        path = documents.get(document_id)
        if path is None:
            raise ValueError(f"No se encontró el documento revisado: {document_id}")
        unsupported = set(metadata_values).difference(REVIEWABLE_FIELDS)
        if unsupported:
            raise ValueError(f"Campos de revisión no permitidos: {', '.join(sorted(unsupported))}")
        sidecar_path = path.with_suffix(path.suffix + ".metadata.json")
        metadata = _metadata_for(path)
        reviewed = metadata.get("libras", {})
        if not isinstance(reviewed, dict):
            reviewed = {}
        reviewed.update(
            {field: str(value).strip() for field, value in metadata_values.items() if str(value).strip()}
        )
        reviewed["quality_status"] = status
        metadata["libras"] = reviewed
        sidecar_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        applied += 1
        changed_document_ids.add(document_id)
    if changed_document_ids:
        manifest_path = source_dir / CHANGE_MANIFEST_NAME
        payload = {}
        if manifest_path.exists():
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        prior = payload.get("changed_document_ids", []) if isinstance(payload, dict) else []
        if not isinstance(prior, list) or not all(isinstance(item, str) for item in prior):
            raise ValueError("El manifiesto de cambios no es válido.")
        manifest_path.write_text(
            json.dumps(
                {"changed_document_ids": sorted(set(prior).union(changed_document_ids))},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    return applied


def main() -> None:
    parser = argparse.ArgumentParser(description="Aplica decisiones humanas de metadatos Libras.")
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--decisions", required=True, help="JSON revisado, con decisions[].")
    args = parser.parse_args()
    applied = apply_review_decisions(Path(args.source_dir).resolve(), Path(args.decisions).resolve())
    print(f"Decisiones de revisión aplicadas: {applied}.")


if __name__ == "__main__":
    main()
