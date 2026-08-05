import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from index_inventory import build_inventory


class IndexInventoryTests(unittest.TestCase):
    def test_groups_chunks_and_identifies_missing_metadata_and_duplicates(self):
        inventory = build_inventory(
            [
                {
                    "document_id": "manual-1",
                    "title": "Manual Evolution.pdf — Página 1",
                    "source_system": "sharepoint",
                    "folder_path": "SOLUCIONES",
                    "drive_id": "drive-docs",
                    "document_type": "pdf",
                    "last_modified": "2026-08-01T00:00:00Z",
                    "content_hash": "hash-a",
                    "chunk_number": 0,
                },
                {
                    "document_id": "manual-1",
                    "title": "Manual Evolution.pdf — Página 2",
                    "source_system": "sharepoint",
                    "folder_path": "SOLUCIONES",
                    "drive_id": "drive-docs",
                    "document_type": "pdf",
                    "last_modified": "2026-08-01T00:00:00Z",
                    "content_hash": "hash-a",
                    "chunk_number": 1,
                },
                {
                    "document_id": "manual-copy",
                    "title": "Manual Evolution copia.pdf — Página 1",
                    "source_system": "sharepoint",
                    "folder_path": "SOLUCIONES",
                    "drive_id": "drive-docs",
                    "document_type": "pdf",
                    "last_modified": "2026-08-02T00:00:00Z",
                    "content_hash": "hash-a",
                    "chunk_number": 0,
                },
                {
                    "document_id": "missing-metadata",
                    "title": "Sin metadatos.txt — Documento",
                    "source_system": "sharepoint",
                    "folder_path": "",
                    "drive_id": "",
                    "document_type": "txt",
                    "last_modified": "",
                    "content_hash": "",
                    "chunk_number": 0,
                },
            ]
        )

        self.assertEqual(3, inventory["summary"]["document_count"])
        self.assertEqual(4, inventory["summary"]["chunk_count"])
        self.assertEqual(1, inventory["summary"]["duplicate_content_hash_count"])
        self.assertEqual(
            ["manual-1", "manual-copy"],
            inventory["duplicate_content_hashes"]["hash-a"],
        )
        missing_document = next(
            document
            for document in inventory["documents"]
            if document["document_id"] == "missing-metadata"
        )
        self.assertEqual(["folder_path", "drive_id", "content_hash"], missing_document["missing_metadata"])


if __name__ == "__main__":
    unittest.main()
