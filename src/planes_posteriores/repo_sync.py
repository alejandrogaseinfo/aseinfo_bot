"""Importa READMEs locales a la base documental del bot.

Esta primera versión no se conecta a GitHub, GitLab ni otro proveedor.
Permite preparar la base mientras se confirma el proveedor y los permisos
de los repositorios.
"""

import argparse
import re
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "knowledge-base"


def _safe_repo_name(name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip())
    return normalized.strip("_") or "Repositorio"


def _readme_path(source: Path) -> Path:
    if source.is_file():
        return source

    candidates = [source / "README.md", source / "readme.md", source / "Readme.md"]
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    raise FileNotFoundError(f"No se encontro README.md en: {source}")


def import_readme(repo_name: str, source: str, output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    source_path = _readme_path(Path(source).expanduser().resolve())
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"{_safe_repo_name(repo_name)}_README.md"
    shutil.copyfile(source_path, destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Importa READMEs locales a docs/knowledge-base."
    )
    parser.add_argument(
        "--repo",
        action="append",
        required=True,
        metavar="NOMBRE=RUTA",
        help="Repositorio y ruta local, por ejemplo ProductoA=C:/codigo/ProductoA",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Carpeta de salida para los READMEs normalizados.",
    )
    args = parser.parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()

    for repository in args.repo:
        if "=" not in repository:
            raise SystemExit(f"Formato invalido para --repo: {repository}. Use NOMBRE=RUTA.")
        name, source = repository.split("=", 1)
        destination = import_readme(name, source, output_dir)
        print(f"README importado: {destination}")


if __name__ == "__main__":
    main()
