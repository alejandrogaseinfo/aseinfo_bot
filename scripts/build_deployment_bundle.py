"""Create the flat, deterministic ZIP consumed by App Service OneDeploy."""

from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path


APPLICATION_FILES = (
    "agent.py",
    "ai_first.py",
    "app.py",
    "azure_search.py",
    "classification.py",
    "config.py",
    "context_guard.py",
    "conversation.py",
    "conversation_mapping_store.py",
    "conversation_state.py",
    "document_index.py",
    "evidence_verifier.py",
    "formatting.py",
    "grounded_response.py",
    "guided_experience.py",
    "handler.py",
    "intent.py",
    "latency_observability.py",
    "logging_utils.py",
    "models.py",
    "openai_conversations.py",
    "query_plan.py",
    "retrieval.py",
    "runtime_health.py",
)
DEPLOYMENT_CONFIG = """[config]\nSCM_DO_BUILD_DURING_DEPLOYMENT = true\nENABLE_ORYX_BUILD = true\n"""
REQUIRED_MEMBERS = frozenset({".deployment", "requirements.txt", *APPLICATION_FILES})
ZIP_TIMESTAMP = (2026, 8, 13, 0, 0, 0)


def archive_members(source: Path) -> tuple[str, ...]:
    """Return the complete, deliberately flat application payload."""
    missing = [name for name in (*APPLICATION_FILES, "requirements.txt") if not (source / name).is_file()]
    if missing:
        raise ValueError(f"faltan archivos de aplicación: {', '.join(missing)}")
    return (".deployment", "requirements.txt", *APPLICATION_FILES)


def _entry(name: str, content: bytes) -> zipfile.ZipInfo:
    entry = zipfile.ZipInfo(name, date_time=ZIP_TIMESTAMP)
    entry.compress_type = zipfile.ZIP_DEFLATED
    return entry


def build_bundle(source: Path, destination: Path) -> str:
    """Write a clean-root bundle and return its uppercase SHA-256."""
    members = archive_members(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in members:
            content = DEPLOYMENT_CONFIG.encode("utf-8") if name == ".deployment" else (source / name).read_bytes()
            archive.writestr(_entry(name, content), content)
    with zipfile.ZipFile(destination) as archive:
        actual = {entry.filename for entry in archive.infolist() if not entry.is_dir()}
    if actual != REQUIRED_MEMBERS:
        raise ValueError("el ZIP no contiene exactamente el árbol de aplicación esperado")
    return hashlib.sha256(destination.read_bytes()).hexdigest().upper()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("src"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    print(f"bundle={args.output}")
    print(f"sha256={build_bundle(args.source.resolve(), args.output.resolve())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
