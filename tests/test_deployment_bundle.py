import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from build_deployment_bundle import APPLICATION_FILES, REQUIRED_MEMBERS, archive_members, build_bundle


class DeploymentBundleTests(unittest.TestCase):
    def test_bundle_is_flat_and_contains_only_expected_application_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in (*APPLICATION_FILES, "requirements.txt"):
                (root / name).write_text(name, encoding="utf-8")
            output = root / "bundle.zip"
            digest = build_bundle(root, output)
            self.assertEqual(64, len(digest))
            with zipfile.ZipFile(output) as archive:
                names = {entry.filename for entry in archive.infolist() if not entry.is_dir()}
            self.assertEqual(REQUIRED_MEMBERS, names)
            self.assertTrue(all("/" not in name for name in names))

    def test_missing_required_source_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "faltan"):
                archive_members(Path(directory))
