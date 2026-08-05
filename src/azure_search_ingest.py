"""CLI to load the controlled document staging area into Azure AI Search."""

import argparse
import os
from pathlib import Path

from azure_search import index_directory, reset_index
from config import Config, load_project_environment


def main() -> None:
    parser = argparse.ArgumentParser(description="Indexa documentos en Azure AI Search.")
    parser.add_argument("--source-dir", required=True, help="Carpeta de staging autorizada.")
    parser.add_argument("--create-index", action="store_true", help="Crea el índice si aún no existe.")
    parser.add_argument(
        "--reset-index",
        action="store_true",
        help="Elimina y recrea únicamente el índice configurado antes de cargarlo.",
    )
    parser.add_argument(
        "--use-current-environment",
        action="store_true",
        help=(
            "Usa únicamente las variables de esta terminal; recomendado para un "
            "índice candidato separado de producción."
        ),
    )
    parser.add_argument(
        "--load-project-secrets",
        action="store_true",
        help=(
            "Carga secretos locales del proyecto y restaura las variables de "
            "Azure Search definidas en esta terminal; no imprime secretos."
        ),
    )
    args = parser.parse_args()
    preserved_search_environment = {
        name: os.environ.get(name)
        for name in (
            "LIBRAS_ENV",
            "AZURE_SEARCH_ENDPOINT",
            "AZURE_SEARCH_INDEX_NAME",
            "AZURE_SEARCH_API_KEY",
            "AZURE_SEARCH_USE_ENTRA_ID",
            "AZURE_SEARCH_USE_SEMANTIC",
            "AZURE_SEARCH_SEMANTIC_CONFIGURATION",
        )
    }
    if not args.use_current_environment:
        load_project_environment()
    elif args.load_project_secrets:
        load_project_environment()
        for name, value in preserved_search_environment.items():
            if value is not None:
                os.environ[name] = value
            elif name == "AZURE_SEARCH_API_KEY":
                # A stale key from a local .env must not override the explicit
                # Entra ID mode selected for the candidate index.
                os.environ.pop(name, None)
    config = Config(os.environ)
    if args.reset_index:
        reset_index(config)
    uploaded = index_directory(
        Path(args.source_dir).resolve(), config, args.create_index or args.reset_index
    )
    print(f"Indexados {uploaded} fragmentos en Azure AI Search.")


if __name__ == "__main__":
    main()
