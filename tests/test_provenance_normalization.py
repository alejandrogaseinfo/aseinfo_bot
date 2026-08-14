import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from azure_search import normalize_record_provenance


class ProvenanceNormalizationTests(unittest.TestCase):
    sources = (("SOLUCIONES", "drive-sol"), ("Manuales", "drive-man"))
    labels = ("Documentos/SOLUCIONES", "Manuales")

    def record(self, **kwargs):
        value = {
            "source_system": "sharepoint",
            "source_url": "https://contoso.sharepoint.com/sites/libras/Documentos%20compartidos/SOLUCIONES/manual.pdf",
            "drive_id": "drive-sol",
            "folder_path": "",
        }
        value.update(kwargs)
        return value

    def test_explicit_path_is_preserved(self):
        normalized, diagnostic = normalize_record_provenance(
            self.record(folder_path="SOLUCIONES"), self.sources, self.labels
        )
        self.assertIsNotNone(normalized)
        self.assertEqual("explícita", diagnostic["provenance_status"])

    def test_empty_path_is_derived_from_authorized_url_and_drive(self):
        normalized, diagnostic = normalize_record_provenance(self.record(), self.sources, self.labels)
        self.assertIsNotNone(normalized)
        self.assertEqual("derivada", diagnostic["provenance_status"])
        self.assertEqual("SOLUCIONES", normalized["folder_path"])

    def test_external_or_missing_drive_is_rejected(self):
        for record in (
            self.record(source_url="https://evil.example/SOLUCIONES/manual.pdf"),
            self.record(drive_id=""),
        ):
            normalized, diagnostic = normalize_record_provenance(record, self.sources, self.labels)
            self.assertIsNone(normalized)
            self.assertEqual("rechazada", diagnostic["provenance_status"])

    def test_ambiguous_route_is_rejected(self):
        record = self.record(source_url="https://contoso.sharepoint.com/sites/libras/Documentos/manual.pdf")
        normalized, diagnostic = normalize_record_provenance(record, self.sources, self.labels)
        self.assertIsNone(normalized)
        self.assertIn("route", diagnostic["provenance_reason"])

    def test_incidental_external_record_does_not_pass_with_direct_record(self):
        direct, _ = normalize_record_provenance(self.record(), self.sources, self.labels)
        incidental, _ = normalize_record_provenance(
            self.record(source_url="https://other.sharepoint.com/sites/other/Manuales/incidental.pdf"),
            self.sources,
            self.labels,
        )
        self.assertIsNotNone(direct)
        self.assertIsNone(incidental)


if __name__ == "__main__":
    unittest.main()
