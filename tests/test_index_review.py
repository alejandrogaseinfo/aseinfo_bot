import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from apply_index_review import apply_review_decisions


class IndexReviewTests(unittest.TestCase):
    def test_only_an_explicit_human_decision_adds_reviewed_metadata(self):
        with TemporaryDirectory() as directory:
            source_dir = Path(directory)
            sql_file = source_dir / "ofuscacion.sql"
            sql_file.write_text("SELECT 1;", encoding="utf-8")
            sidecar = sql_file.with_suffix(".sql.metadata.json")
            sidecar.write_text(
                json.dumps({"document_id": "sql-1", "name": "ofuscacion.sql"}),
                encoding="utf-8",
            )
            decisions = source_dir / "decisions.json"
            decisions.write_text(
                json.dumps(
                    {
                        "decisions": [
                            {
                                "document_id": "sql-1",
                                "decision": "aprobado",
                                "metadata": {"operation": "ofuscación de datos"},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(1, apply_review_decisions(source_dir, decisions))
            metadata = json.loads(sidecar.read_text(encoding="utf-8"))

            self.assertEqual("ofuscación de datos", metadata["libras"]["operation"])
            self.assertEqual("aprobado", metadata["libras"]["quality_status"])
            self.assertNotIn("operation", {key for key in metadata if key != "libras"})
            change_manifest = json.loads(
                (source_dir / ".libras-sharepoint-changes.json").read_text(encoding="utf-8")
            )
            self.assertEqual(["sql-1"], change_manifest["changed_document_ids"])


if __name__ == "__main__":
    unittest.main()
