"""Validate a Libras deployment tree in an isolated Linux Python runtime."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REQUIRED_ROOT_FILES = frozenset({"app.py", "requirements.txt", ".deployment"})
FORBIDDEN_PARTS = frozenset({".env", "tests", "docs", "data", "output", "tmp"})
PYTHON_IMAGE = "python:3.11.15-slim"
GUNICORN_COMMAND = "gunicorn --check-config --bind 0.0.0.0:8000 --worker-class aiohttp.worker.GunicornWebWorker --timeout 600 app:app"
PLACEHOLDER_ENVIRONMENT = {
    "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID": "00000000-0000-0000-0000-000000000001",
    "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET": "placeholder-not-a-secret",
    "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID": "00000000-0000-0000-0000-000000000002",
    "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__AUTHTYPE": "clientSecret",
}


def validate_tree(root: Path) -> None:
    """Reject a package that cannot be used by the configured ``app:app`` host."""
    names = {path.name for path in root.iterdir()}
    missing = sorted(REQUIRED_ROOT_FILES - names)
    if missing:
        raise ValueError(f"faltan archivos requeridos en la raíz: {', '.join(missing)}")
    if (root / "src").exists():
        raise ValueError("el artefacto no debe envolver la aplicación en src/")
    forbidden = sorted(part for part in FORBIDDEN_PARTS if (root / part).exists())
    if forbidden:
        raise ValueError(f"el artefacto contiene rutas no desplegables: {', '.join(forbidden)}")
    if any(path.name == ".env" for path in root.rglob(".env")):
        raise ValueError("el artefacto contiene un archivo .env")


def extract_bundle(bundle: Path, destination: Path) -> None:
    """Extract a ZIP after rejecting traversal paths and nested-root layouts."""
    with zipfile.ZipFile(bundle) as archive:
        names = [entry.filename for entry in archive.infolist() if not entry.is_dir()]
        if any(Path(name).is_absolute() or ".." in Path(name).parts for name in names):
            raise ValueError("el ZIP contiene una ruta insegura")
        if any(len(Path(name).parts) > 1 for name in names):
            raise ValueError("el ZIP debe contener archivos de aplicación en la raíz")
        archive.extractall(destination)
    validate_tree(destination)


def docker_command(source_dir: Path) -> list[str]:
    """Return the hermetic Linux startup command without passing host secrets."""
    command = " && ".join((
        "python -m pip install --no-cache-dir -r requirements.txt",
        "python -c \"import app, aiohttp, gunicorn; print('entrypoint_import=ok')\"",
        GUNICORN_COMMAND,
    ))
    environment = [item for key, value in PLACEHOLDER_ENVIRONMENT.items() for item in ("--env", f"{key}={value}")]
    return [
        "docker", "run", "--rm", "--network", "none", "--mount",
        f"type=bind,source={source_dir.resolve()},target=/workspace,readonly",
        "--workdir", "/workspace", *environment, PYTHON_IMAGE, "sh", "-ec", command,
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source-dir", type=Path)
    source.add_argument("--bundle", type=Path)
    args = parser.parse_args(argv)
    if args.bundle:
        with tempfile.TemporaryDirectory(prefix="libras-linux-startup-") as temporary:
            root = Path(temporary)
            extract_bundle(args.bundle, root)
            if shutil.which("docker") is None:
                print("Docker no está disponible; no se ejecutó la validación Linux.", file=sys.stderr)
                return 2
            subprocess.run(docker_command(root), check=True)
    else:
        root = args.source_dir.resolve()
        validate_tree(root)
        if shutil.which("docker") is None:
            print("Docker no está disponible; no se ejecutó la validación Linux.", file=sys.stderr)
            return 2
        subprocess.run(docker_command(root), check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
