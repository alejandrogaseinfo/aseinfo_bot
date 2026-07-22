import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config import Config
from sharepoint_sync import SharePointApplicationClient, create_sharepoint_client


class SharePointSyncTests(unittest.TestCase):
    def _application_config(self):
        return Config(
            {
                "SHAREPOINT_AUTH_MODE": "application",
                "SHAREPOINT_TENANT_ID": "tenant-id",
                "SHAREPOINT_CLIENT_ID": "client-id",
                "SHAREPOINT_CLIENT_SECRET": "secret-from-key-vault",
                "SHAREPOINT_SITE_ID": "site-id",
                "SHAREPOINT_DRIVE_ID": "drive-id",
                "SHAREPOINT_FOLDER_PATH": "Operaciones/Piloto",
            }
        )

    def test_application_client_uses_app_token_and_explicit_drive(self):
        application = Mock()
        application.acquire_token_for_client.return_value = {"access_token": "token"}
        config = self._application_config()

        with patch(
            "sharepoint_sync.msal.ConfidentialClientApplication", return_value=application
        ) as factory:
            client = SharePointApplicationClient(config)

        self.assertEqual("drive-id", client.drive_id)
        self.assertEqual({"Authorization": "Bearer token"}, client.headers)
        factory.assert_called_once_with(
            client_id="client-id",
            authority="https://login.microsoftonline.com/tenant-id",
            client_credential="secret-from-key-vault",
        )
        application.acquire_token_for_client.assert_called_once_with(
            scopes=["https://graph.microsoft.com/.default"]
        )

    def test_unknown_auth_mode_is_rejected(self):
        config = self._application_config()
        config.sharepoint_auth_mode = "unsupported"

        with self.assertRaisesRegex(RuntimeError, "SHAREPOINT_AUTH_MODE"):
            create_sharepoint_client(config)


if __name__ == "__main__":
    unittest.main()
