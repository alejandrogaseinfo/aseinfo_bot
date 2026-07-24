"""Ingesta documentos incluidos en setups y hotfixes."""

import argparse
import re
import tempfile
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "knowledge-base"
SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt"}


def _safe_name(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return normalized.strip("_") or "documento"


def _documents(root: Path) -> list[Path]:
    return sorted(
        path for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def ingest_setup(product: str, release: str, source: str, output_dir: Path = DEFAULT_OUTPUT_DIR) -> list[Path]:
    """Importa documentos de una carpeta o ZIP de setup/hotfix."""
    source_path = Path(source).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"No existe la entrega: {source_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    source_name = source_path.stem
    created: list[Path] = []

    with tempfile.TemporaryDirectory(prefix="chat_salvador_setup_") as temp_dir:
        extraction_root = Path(temp_dir)
        if source_path.is_file() and source_path.suffix.lower() == ".zip":
            with zipfile.ZipFile(source_path) as archive:
                archive.extractall(extraction_root)
            document_root = extraction_root
        elif source_path.is_dir():
            document_root = source_path
        else:
            raise ValueError("La fuente debe ser una carpeta o un archivo ZIP.")

        for document_path in _documents(document_root):
            relative_path = document_path.relative_to(document_root)
            output_name = (
                f"setup__{_safe_name(product)}__{_safe_name(release)}__"
                f"{_safe_name(document_path.stem)}{document_path.suffix.lower()}"
            )
            destination = output_dir / output_name
            metadata = "\n".join([
                "<!-- libras-metadata",
                f"producto: {product}",
                f"entrega: {release}",
                "fuente: setup_hotfix",
                f"archivo_origen: {source_name}/{relative_path.as_posix()}",
                "-->\n",
            ])
            content = document_path.read_text(encoding="utf-8", errors="replace")
            destination.write_text(metadata + content, encoding="utf-8")
            created.append(destination)
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="Extrae documentos técnicos de un setup o hotfix.")
    parser.add_argument("--product", required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--source", required=True, help="Carpeta o ZIP del setup/hotfix.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    for document in ingest_setup(args.product, args.release, args.source, Path(args.output_dir).resolve()):
        print(f"Documento de setup importado: {document}")


if __name__ == "__main__":
    main()
