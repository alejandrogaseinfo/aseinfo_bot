import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from preflight import data_access_checks, platform_checks, run_preflight


def _config(**overrides):
    values = {
        "openai_api_key": "test-key",
        "openai_base_url": "",
        "azure_search_configured": True,
        "azure_search_endpoint": "https://libras.search.windows.net",
        "sharepoint_tenant_id": "tenant-id",
        "sharepoint_client_id": "client-id",
        "sharepoint_auth_mode": "application",
        "sharepoint_client_secret": "secret",
        "sharepoint_site_id": "site-id",
        "sharepoint_drive_id": "drive-id",
        "sharepoint_folder_path": "Operaciones/Piloto",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class PreflightTests(unittest.TestCase):
    def test_platform_checks_accept_a_complete_manifest_and_service_configuration(self):
        with TemporaryDirectory() as directory:
            package_dir = Path(directory)
            for icon in ("color.png", "outline.png"):
                (package_dir / icon).write_bytes(b"icon")
            manifest_path = package_dir / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "id": "${{TEAMS_APP_ID}}",
                        "icons": {"color": "color.png", "outline": "outline.png"},
                        "bots": [{"botId": "${{BOT_ID}}", "scopes": ["personal"]}],
                    }
                ),
                encoding="utf-8",
            )

            checks = platform_checks(_config(), manifest_path)

        self.assertTrue(all(check.passed for check in checks))

    def test_data_access_checks_report_only_missing_values(self):
        checks = data_access_checks(_config(sharepoint_drive_id="", sharepoint_folder_path=""))
        missing = {check.name for check in checks if not check.passed}

        self.assertEqual({"sharepoint_drive_id", "sharepoint_folder_path"}, missing)

    def test_platform_rejects_a_placeholder_search_endpoint(self):
        with TemporaryDirectory() as directory:
            package_dir = Path(directory)
            for icon in ("color.png", "outline.png"):
                (package_dir / icon).write_bytes(b"icon")
            manifest_path = package_dir / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "id": "app-id",
                        "icons": {"color": "color.png", "outline": "outline.png"},
                        "bots": [{"botId": "bot-id", "scopes": ["personal"]}],
                    }
                ),
                encoding="utf-8",
            )
            checks = platform_checks(
                _config(azure_search_endpoint="https://<tu-servicio>.search.windows.net"),
                manifest_path,
            )

        search_check = next(check for check in checks if check.name == "azure_ai_search")
        self.assertFalse(search_check.passed)

    def test_all_stage_combines_platform_and_data_access_checks(self):
        with TemporaryDirectory() as directory:
            manifest_path = Path(directory) / "missing.json"
            checks = run_preflight(_config(openai_api_key=""), "all", manifest_path)

        failed = {check.name for check in checks if not check.passed}
        self.assertIn("model_configuration", failed)
        self.assertIn("teams_manifest", failed)


if __name__ == "__main__":
    unittest.main()
