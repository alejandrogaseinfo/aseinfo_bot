import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from config import Config


def load_environment() -> None:
    load_dotenv()

    project_root = Path(__file__).resolve().parent.parent
    env_name = os.environ.get("TEAMSFX_ENV", "local")
    candidate_files = [
        project_root / "env" / ".env.local.user",
        project_root / "env" / f".env.{env_name}.user",
    ]

    for candidate in candidate_files:
        if candidate.exists():
            load_dotenv(candidate, override=False)


def sync_knowledge_base() -> None:
    load_environment()
    config = Config(os.environ)

    if not config.openai_vector_store_id:
        raise RuntimeError("Falta OPENAI_VECTOR_STORE_ID en el entorno.")

    client = OpenAI(api_key=config.openai_api_key)
    knowledge_base_path = Path(__file__).resolve().parent.parent / "docs" / "knowledge-base"
    markdown_files = sorted(knowledge_base_path.glob("*.md"))

    existing_files = list(
        client.vector_stores.files.list(
            vector_store_id=config.openai_vector_store_id,
            limit=100,
        )
    )
    existing_by_name: dict[str, list] = {}
    for vector_store_file in existing_files:
        existing_by_name.setdefault(getattr(vector_store_file, "filename", ""), []).append(
            vector_store_file
        )

    print(
        f"Sincronizando {len(markdown_files)} archivo(s) hacia el vector store "
        f"{config.openai_vector_store_id}."
    )

    for file_path in markdown_files:
        existing = existing_by_name.get(file_path.name, [])
        if existing:
            for existing_file in existing:
                client.vector_stores.files.delete(
                    vector_store_id=config.openai_vector_store_id,
                    file_id=existing_file.id,
                )
            print(f"Reemplazando archivo existente: {file_path.name}")
        else:
            print(f"Subiendo archivo nuevo: {file_path.name}")

        with file_path.open("rb") as file_handle:
            client.vector_stores.files.upload_and_poll(
                vector_store_id=config.openai_vector_store_id,
                file=file_handle,
                attributes={
                    "source": "knowledge-base",
                    "path": f"docs/knowledge-base/{file_path.name}",
                },
            )

    print("Sincronizacion completada.")


if __name__ == "__main__":
    sync_knowledge_base()
