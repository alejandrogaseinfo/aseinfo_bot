"""Build a flat App Service ZIP with Linux Python dependencies vendored."""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from build_deployment_bundle import APPLICATION_FILES

REQUIRED = {"app.py", "handler.py", "ai_first.py", "config.py", "requirements.txt", ".deployment"}
FORBIDDEN_PARTS = {".env", ".git", "tests", "logs", "output", "__pycache__"}
DEPLOYMENT_CONFIG = "[config]\nSCM_DO_BUILD_DURING_DEPLOYMENT = false\nENABLE_ORYX_BUILD = false\n"


def _zip_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def build(source: Path, site_packages: Path, output: Path) -> str:
    if sys.platform != "linux":
        raise RuntimeError("El bundle preconstruido solo se puede crear en Linux")
    if sys.version_info[:2] != (3, 11):
        raise RuntimeError(f"Se requiere Python 3.11, actual={sys.version.split()[0]}")
    if not site_packages.is_dir():
        raise ValueError(f"No existe site-packages Linux: {site_packages}")
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp)
        for name in APPLICATION_FILES:
            shutil.copy2(source / name, staging / name)
        shutil.copy2(source / "requirements.txt", staging / "requirements.txt")
        (staging / ".deployment").write_text(DEPLOYMENT_CONFIG, encoding="utf-8")
        vendor = staging / ".python_packages" / "lib" / "site-packages"
        shutil.copytree(site_packages, vendor)
        members = sorted(p.relative_to(staging).as_posix() for p in staging.rglob("*") if p.is_file())
        if not REQUIRED <= set(members):
            raise ValueError(f"Faltan archivos obligatorios: {sorted(REQUIRED - set(members))}")
        if any(any(part in FORBIDDEN_PARTS or part.endswith(('.env', '.log')) for part in Path(m).parts) for m in members):
            raise ValueError("El bundle contiene archivos prohibidos")
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name in members:
                info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, (staging / name).read_bytes())
    return _zip_digest(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("src"))
    parser.add_argument("--site-packages", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(f"sha256={build(args.source.resolve(), args.site_packages.resolve(), args.output.resolve())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
