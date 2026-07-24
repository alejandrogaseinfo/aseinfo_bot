"""Preflight checks for Libras deployment and SharePoint data access."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from config import Config, load_project_environment


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_ROOT / "appPackage" / "manifest.json"


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def _model_configured(config) -> bool:
    return bool(config.openai_api_key or config.openai_base_url)


def _search_endpoint_is_production_like(config) -> bool:
    endpoint = getattr(config, "azure_search_endpoint", "")
    if not endpoint:
        # Test doubles can expose only azure_search_configured. Real Config
        # always carries the endpoint and receives the stricter validation.
        return True
    parsed = urlparse(endpoint)
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and parsed.hostname.endswith(".search.windows.net")
        and "<" not in endpoint
        and ">" not in endpoint
    )


def validate_manifest(manifest_path: Path = MANIFEST_PATH) -> list[CheckResult]:
    if not manifest_path.exists():
        return [CheckResult("teams_manifest", False, "No se encontró appPackage/manifest.json.")]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [CheckResult("teams_manifest", False, "El manifest de Teams no es JSON válido.")]

    bots = manifest.get("bots")
    bot_id = bots[0].get("botId") if isinstance(bots, list) and bots else ""
    scopes = bots[0].get("scopes", []) if isinstance(bots, list) and bots else []
    icons = manifest.get("icons", {})
    return [
        CheckResult(
            "teams_manifest_id",
            bool(manifest.get("id")),
            "El manifest declara un ID de aplicación o un placeholder de Toolkit.",
        ),
        CheckResult(
            "teams_bot_id",
            bool(bot_id),
            "El bot declara un ID o un placeholder de Toolkit.",
        ),
        CheckResult(
            "teams_personal_scope",
            "personal" in scopes,
            "El bot está disponible en el ámbito personal de Teams.",
        ),
        CheckResult(
            "teams_icons",
            all((manifest_path.parent / icons.get(name, "")).is_file() for name in ("color", "outline")),
            "Los dos íconos declarados están presentes en appPackage.",
        ),
    ]


def platform_checks(config, manifest_path: Path = MANIFEST_PATH) -> list[CheckResult]:
    checks = [
        CheckResult(
            "model_configuration",
            _model_configured(config),
            "Hay una clave de modelo o una URL compatible configurada.",
        ),
        CheckResult(
            "azure_ai_search",
            bool(config.azure_search_configured) and _search_endpoint_is_production_like(config),
            "Azure AI Search tiene endpoint válido, índice y autenticación configurados.",
        ),
    ]
    return checks + validate_manifest(manifest_path)


def data_access_checks(config) -> list[CheckResult]:
    required_fields = {
        "sharepoint_tenant_id": "Tenant ID de Microsoft Entra.",
        "sharepoint_client_id": "Client ID de la App Registration corporativa.",
        "sharepoint_site_id": "ID del sitio de SharePoint aprobado.",
        "sharepoint_drive_id": "ID de la biblioteca o drive aprobado.",
        "sharepoint_folder_path": "Carpeta aprobada dentro de la biblioteca.",
    }
    checks = [
        CheckResult(name, bool(getattr(config, name, "")), detail)
        for name, detail in required_fields.items()
    ]
    auth_mode = getattr(config, "sharepoint_auth_mode", "delegated")
    checks.append(
        CheckResult(
            "sharepoint_auth_mode",
            auth_mode == "application",
            "La sincronización productiva usa application con la App Registration corporativa.",
        )
    )
    checks.append(
        CheckResult(
            "sharepoint_application_secret",
            bool(getattr(config, "sharepoint_client_secret", "")),
            "El secreto o referencia de Key Vault de la App Registration está disponible.",
        )
    )
    return checks


def run_preflight(config, stage: str, manifest_path: Path = MANIFEST_PATH) -> list[CheckResult]:
    checks: list[CheckResult] = []
    if stage in {"platform", "all"}:
        checks.extend(platform_checks(config, manifest_path))
    if stage in {"data-access", "all"}:
        checks.extend(data_access_checks(config))
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Valida prerequisitos configurables de Libras sin revelar secretos."
    )
    parser.add_argument(
        "--stage",
        choices=("platform", "data-access", "all"),
        default="all",
        help="platform corresponde a Solicitud A; data-access prepara Solicitud B.",
    )
    args = parser.parse_args()
    load_project_environment()
    checks = run_preflight(Config(os.environ), args.stage)
    for check in checks:
        status = "OK" if check.passed else "PENDIENTE"
        print(f"[{status}] {check.name}: {check.detail}")
    if not all(check.passed for check in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
