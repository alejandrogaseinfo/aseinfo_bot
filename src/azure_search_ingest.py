"""CLI to load the controlled document staging area into Azure AI Search."""

import argparse
import os
from pathlib import Path

from azure_search import index_directory
from config import Config, load_project_environment


def main() -> None:
    parser = argparse.ArgumentParser(description="Indexa documentos en Azure AI Search.")
    parser.add_argument("--source-dir", required=True, help="Carpeta de staging autorizada.")
    parser.add_argument("--create-index", action="store_true", help="Crea el índice si aún no existe.")
    args = parser.parse_args()
    load_project_environment()
    uploaded = index_directory(Path(args.source_dir).resolve(), Config(os.environ), args.create_index)
    print(f"Indexados {uploaded} fragmentos en Azure AI Search.")


if __name__ == "__main__":
    main()
