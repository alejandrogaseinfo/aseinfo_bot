import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config import Config, load_project_environment
from sharepoint_sync import (
    SharePointApplicationClient,
    SharePointGraphClient,
    SUPPORTED_EXTENSIONS,
    create_sharepoint_client,
    inventory_summary,
    _descriptive_fields,
    _selected_sources,
)


class SharePointSyncTests(unittest.TestCase):
    def test_descriptive_sharepoint_columns_accept_display_name_variants(self):
        fields = _descriptive_fields(
            {
                "listItem": {
                    "fields": {
                        "Detalle": "Corrige vacaciones con saldo negativo.",
                        "Dependencia0": "Requiere respaldo de base de datos.",
                    }
                }
            }
        )

        self.assertEqual(
            {
                "description": "Corrige vacaciones con saldo negativo.",
                "dependency": "Requiere respaldo de base de datos.",
            },
            fields,
        )

    def test_script_fields_are_enriched_from_embedded_list_item_columns(self):
        config = self._application_config()
        client = SharePointGraphClient(config, "token", "drive-id")
        root = client._children_url(config.sharepoint_folder_path)
        with patch.object(
            client,
            "_get",
            return_value={
                "value": [
                    {
                        "id": "script-1",
                        "name": "acc.proc_arreglar_vac_negativos.sql",
                        "file": {},
                        "listItem": {"fields": {"Detalle": "Corrige saldos negativos."}},
                    }
                ]
            },
        ):
            files = client.list_supported_files()

        self.assertEqual("Corrige saldos negativos.", files[0]["_libras_description"])
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

    def test_user_environment_files_override_repository_defaults(self):
        with patch("config.load_dotenv") as load_dotenv_mock:
            load_project_environment()

        user_calls = [
            call
            for call in load_dotenv_mock.call_args_list
            if call.args and str(call.args[0]).endswith(".user")
        ]
        self.assertTrue(user_calls)
        self.assertTrue(all(call.kwargs.get("override") is True for call in user_calls))

    def test_multiple_sharepoint_folder_paths_are_parsed(self):
        config = Config(
            {
                "SHAREPOINT_FOLDER_PATH": "SOLUCIONES",
                "SHAREPOINT_FOLDER_PATHS": "SOLUCIONES, ReadME Hotfixes;Manuales",
            }
        )

        self.assertEqual(
            ("SOLUCIONES", "ReadME Hotfixes", "Manuales"),
            config.sharepoint_folder_paths,
        )

    def test_selected_sources_preserve_explicit_priority_and_validate_bounds(self):
        sources = (("", "readmes"), ("SOLUCIONES", "solutions"), ("", "scripts"))

        self.assertEqual(
            (("", "readmes"), ("", "scripts")),
            _selected_sources(sources, (1, 3, 1)),
        )
        with self.assertRaisesRegex(ValueError, "entre 1 y 3"):
            _selected_sources(sources, (4,))

    def test_multiple_drives_and_paths_remain_aligned_including_library_roots(self):
        config = Config(
            {
                "SHAREPOINT_DRIVE_ID": "drive-1",
                "SHAREPOINT_DRIVE_IDS": "drive-1,drive-2,drive-3",
                "SHAREPOINT_FOLDER_PATH": "SOLUCIONES",
                "SHAREPOINT_FOLDER_PATHS": ",SOLUCIONES,",
            }
        )

        self.assertEqual(
            (("", "drive-1"), ("SOLUCIONES", "drive-2"), ("", "drive-3")),
            config.sharepoint_sources,
        )

    def test_inventory_counts_all_files_without_downloading(self):
        config = self._application_config()
        client = SharePointGraphClient(config, "token", "drive-id")
        responses = {
            client._children_url(config.sharepoint_folder_path): {
                "value": [
                    {"id": "folder-1", "name": "Manual", "folder": {}},
                    {"id": "pdf-1", "name": "guia.PDF", "file": {}},
                ],
                "@odata.nextLink": "https://graph.example/root-next",
            },
            "https://graph.example/root-next": {
                "value": [{"id": "docx-1", "name": "pasos.docx", "file": {}}]
            },
            "https://graph.microsoft.com/v1.0/drives/drive-id/items/folder-1/children": {
                "value": [
                    {"id": "xlsx-1", "name": "tiempos.xlsx", "file": {}},
                    {"id": "other-1", "name": "README", "file": {}},
                ]
            },
        }
        with patch.object(client, "_get", side_effect=lambda url: responses[url]):
            summary = inventory_summary(client, config.sharepoint_folder_path)

        self.assertEqual(1, summary["folder_count"])
        self.assertEqual(4, summary["file_count"])
        self.assertEqual(1, summary["pdf_count"])
        self.assertEqual(
            {".docx": 1, ".pdf": 1, ".xlsx": 1, "[sin extension]": 1},
            summary["files_by_extension"],
        )

    def test_list_supported_files_excludes_binary_formats(self):
        config = self._application_config()
        client = SharePointGraphClient(config, "token", "drive-id")
        root = client._children_url(config.sharepoint_folder_path)
        responses = {
            root: {
                "value": [
                    {"id": "pdf-1", "name": "guia.pdf", "file": {}},
                    {"id": "docx-1", "name": "pasos.docx", "file": {}},
                    {"id": "mp4-1", "name": "video.mp4", "file": {}},
                ]
            }
        }
        with patch.object(client, "_get", side_effect=lambda url: responses[url]):
            files = client.list_supported_files()

        self.assertEqual({"guia.pdf", "pasos.docx"}, {item["name"] for item in files})
        self.assertIn(".docx", SUPPORTED_EXTENSIONS)
        self.assertNotIn(".mp4", SUPPORTED_EXTENSIONS)

    def test_download_does_not_forward_graph_bearer_to_sharepoint_redirect(self):
        config = self._application_config()
        client = SharePointGraphClient(config, "graph-token", "drive-id")
        graph_response = Mock(status_code=302, headers={"location": "https://sharepoint.example/temp"})
        redirected_response = Mock(status_code=200, content=b"document-bytes")

        with patch(
            "sharepoint_sync.requests.get",
            side_effect=[graph_response, redirected_response],
        ) as get:
            from tempfile import TemporaryDirectory

            with TemporaryDirectory() as directory:
                destination = Path(directory) / "manual.pdf"
                client.download({"id": "item-1"}, destination)
                self.assertEqual(b"document-bytes", destination.read_bytes())

        self.assertEqual("https://graph.microsoft.com/v1.0/drives/drive-id/items/item-1/content", get.call_args_list[0].args[0])
        self.assertEqual({"Authorization": "Bearer graph-token"}, get.call_args_list[0].kwargs["headers"])
        self.assertNotIn("headers", get.call_args_list[1].kwargs)

    def test_sync_filename_uses_full_item_id_for_duplicate_names(self):
        from tempfile import TemporaryDirectory

        class FakeSharePointClient:
            drive_id = "drive-1"

            def list_supported_files(self):
                return [
                    {
                        "id": "same-prefix-aaaa",
                        "name": "Instrucciones.txt",
                        "eTag": '"etag-1"',
                        "webUrl": "https://contoso.example/a.txt",
                        "lastModifiedDateTime": "2026-07-22T12:00:00Z",
                    },
                    {
                        "id": "same-prefix-bbbb",
                        "name": "Instrucciones.txt",
                        "eTag": '"etag-2"',
                        "webUrl": "https://contoso.example/b.txt",
                        "lastModifiedDateTime": "2026-07-22T12:00:00Z",
                    },
                ]

            def download(self, item, destination):
                destination.write_text(item["id"], encoding="utf-8")

        with TemporaryDirectory() as directory:
            config = self._application_config()
            with patch("sharepoint_sync.create_sharepoint_client", return_value=FakeSharePointClient()):
                from sharepoint_sync import sync_pdfs

                sync_pdfs(config, Path(directory))
            files = sorted(Path(directory).glob("*.txt"))

        self.assertEqual(2, len(files))
        self.assertTrue(any("same-prefix-aaaa" in path.name for path in files))
        self.assertTrue(any("same-prefix-bbbb" in path.name for path in files))

    def test_multi_library_sync_scopes_document_ids_by_drive(self):
        from tempfile import TemporaryDirectory

        class FakeSharePointClient:
            drive_id = "drive-1"

            def list_supported_files(self, folder_path, drive_id):
                return [
                    {
                        "id": "same-item-id",
                        "name": f"manual-{drive_id}.txt",
                        "eTag": f'"{drive_id}"',
                        "webUrl": f"https://contoso.example/{drive_id}.txt",
                        "lastModifiedDateTime": "2026-07-22T12:00:00Z",
                    }
                ]

            def download(self, item, destination):
                destination.write_text(item["name"], encoding="utf-8")

        config = Config(
            {
                "SHAREPOINT_SITE_ID": "site-id",
                "SHAREPOINT_DRIVE_ID": "drive-1",
                "SHAREPOINT_DRIVE_IDS": "drive-1,drive-2",
                "SHAREPOINT_FOLDER_PATH": "SOLUCIONES",
                "SHAREPOINT_FOLDER_PATHS": "SOLUCIONES,",
            }
        )
        with TemporaryDirectory() as directory:
            with patch(
                "sharepoint_sync.create_sharepoint_client",
                return_value=FakeSharePointClient(),
            ):
                from sharepoint_sync import sync_pdfs

                sync_pdfs(config, Path(directory))

            metadata = sorted(Path(directory).glob("*.txt.metadata.json"))
            self.assertEqual(2, len(metadata))
            document_ids = {
                json.loads(path.read_text(encoding="utf-8"))["document_id"]
                for path in metadata
            }
            self.assertEqual(
                {"drive-1:same-item-id", "drive-2:same-item-id"}, document_ids
            )

    def test_partial_sync_does_not_delete_documents_from_omitted_sources(self):
        from tempfile import TemporaryDirectory

        class FakeSharePointClient:
            drive_id = "drive-1"

            def list_supported_files(self, folder_path, drive_id):
                if drive_id == "drive-1":
                    return []
                return [
                    {
                        "id": "item-2",
                        "name": "manual.txt",
                        "eTag": '"etag-2"',
                        "webUrl": "https://contoso.example/manual.txt",
                        "lastModifiedDateTime": "2026-08-06T12:00:00Z",
                    }
                ]

            def download(self, item, destination):
                destination.write_text("manual", encoding="utf-8")

        config = Config(
            {
                "SHAREPOINT_SITE_ID": "site-id",
                "SHAREPOINT_DRIVE_ID": "drive-1",
                "SHAREPOINT_DRIVE_IDS": "drive-1,drive-2",
                "SHAREPOINT_FOLDER_PATH": "SOLUCIONES",
                "SHAREPOINT_FOLDER_PATHS": "SOLUCIONES,",
            }
        )
        with TemporaryDirectory() as directory:
            output_dir = Path(directory)
            with patch("sharepoint_sync.create_sharepoint_client", return_value=FakeSharePointClient()):
                from sharepoint_sync import sync_pdfs

                sync_pdfs(config, output_dir)
                sync_pdfs(config, output_dir, source_indexes=(1,))

            state = json.loads(
                (output_dir / ".libras-sharepoint-sync-state.json").read_text(encoding="utf-8")
            )
            deletions = json.loads(
                (output_dir / ".libras-sharepoint-deletions.json").read_text(encoding="utf-8")
            )

        self.assertIn("drive-2:item-2", state["documents"])
        self.assertNotIn("drive-2:item-2", deletions["deleted_document_ids"])

    def test_partial_sync_keeps_drive_scoped_identity_for_a_multi_source_scope(self):
        from tempfile import TemporaryDirectory

        class FakeSharePointClient:
            drive_id = "drive-1"

            def list_supported_files(self, folder_path, drive_id):
                return [
                    {
                        "id": "same-item-id",
                        "name": "script.sql",
                        "eTag": '"etag-1"',
                        "webUrl": "https://contoso.example/script.sql",
                        "lastModifiedDateTime": "2026-08-06T12:00:00Z",
                    }
                ]

            def download(self, item, destination):
                destination.write_text("select 1", encoding="utf-8")

        config = Config(
            {
                "SHAREPOINT_SITE_ID": "site-id",
                "SHAREPOINT_DRIVE_ID": "drive-1",
                "SHAREPOINT_DRIVE_IDS": "drive-1,drive-2",
                "SHAREPOINT_FOLDER_PATH": "SOLUCIONES",
                "SHAREPOINT_FOLDER_PATHS": "SOLUCIONES,",
            }
        )
        with TemporaryDirectory() as directory:
            with patch(
                "sharepoint_sync.create_sharepoint_client", return_value=FakeSharePointClient()
            ):
                from sharepoint_sync import sync_pdfs

                sync_pdfs(config, Path(directory), source_indexes=(1,))
            state = json.loads(
                (Path(directory) / ".libras-sharepoint-sync-state.json").read_text(encoding="utf-8")
            )

        self.assertIn("drive-1:same-item-id", state["documents"])
        self.assertNotIn("same-item-id", state["documents"])

    def test_identity_migration_marks_new_key_before_deleting_legacy_key(self):
        from tempfile import TemporaryDirectory

        class FakeSharePointClient:
            drive_id = "drive-1"

            def list_supported_files(self, folder_path, drive_id):
                return [
                    {
                        "id": "item-1",
                        "name": "script.sql",
                        "eTag": '"etag-1"',
                        "webUrl": "https://contoso.example/script.sql",
                        "lastModifiedDateTime": "2026-08-06T12:00:00Z",
                    }
                ]

            def download(self, item, destination):
                destination.write_text("select 1", encoding="utf-8")

        legacy_config = Config(
            {
                "SHAREPOINT_SITE_ID": "site-id",
                "SHAREPOINT_DRIVE_ID": "drive-1",
                "SHAREPOINT_FOLDER_PATH": "SOLUCIONES",
            }
        )
        multi_source_config = Config(
            {
                "SHAREPOINT_SITE_ID": "site-id",
                "SHAREPOINT_DRIVE_ID": "drive-1",
                "SHAREPOINT_DRIVE_IDS": "drive-1,drive-2",
                "SHAREPOINT_FOLDER_PATH": "SOLUCIONES",
                "SHAREPOINT_FOLDER_PATHS": "SOLUCIONES,",
            }
        )
        with TemporaryDirectory() as directory:
            output_dir = Path(directory)
            with patch(
                "sharepoint_sync.create_sharepoint_client", return_value=FakeSharePointClient()
            ):
                from sharepoint_sync import sync_pdfs

                sync_pdfs(legacy_config, output_dir)
                sync_pdfs(multi_source_config, output_dir, source_indexes=(1,))
            changes = json.loads(
                (output_dir / ".libras-sharepoint-changes.json").read_text(encoding="utf-8")
            )
            deletions = json.loads(
                (output_dir / ".libras-sharepoint-deletions.json").read_text(encoding="utf-8")
            )

        self.assertIn("drive-1:item-1", changes["changed_document_ids"])
        self.assertIn("item-1", deletions["deleted_document_ids"])

    def test_unchanged_document_preserves_approved_quality_review(self):
        from tempfile import TemporaryDirectory

        item = {
            "id": "sql-1",
            "name": "vacaciones.sql",
            "eTag": '"etag-1"',
            "webUrl": "https://contoso.example/vacaciones.sql",
            "lastModifiedDateTime": "2026-08-06T12:00:00Z",
        }

        class FakeSharePointClient:
            drive_id = "drive-1"

            def list_supported_files(self, folder_path, drive_id):
                return [item]

            def download(self, current_item, destination):
                destination.write_text("select 1", encoding="utf-8")

        config = Config(
            {
                "SHAREPOINT_SITE_ID": "site-id",
                "SHAREPOINT_DRIVE_ID": "drive-1",
                "SHAREPOINT_FOLDER_PATH": "SOLUCIONES",
            }
        )
        with TemporaryDirectory() as directory:
            output_dir = Path(directory)
            with patch("sharepoint_sync.create_sharepoint_client", return_value=FakeSharePointClient()):
                from sharepoint_sync import sync_pdfs

                sync_pdfs(config, output_dir)
                metadata_path = next(output_dir.glob("*.sql.metadata.json"))
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                metadata["libras"] = {"quality_status": "aprobado", "artifact_role": "script"}
                metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
                sync_pdfs(config, output_dir)

            refreshed = json.loads(metadata_path.read_text(encoding="utf-8"))

        self.assertEqual("aprobado", refreshed["libras"]["quality_status"])
        self.assertEqual("script", refreshed["libras"]["artifact_role"])


if __name__ == "__main__":
    unittest.main()
