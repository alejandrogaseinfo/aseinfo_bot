import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from validate_linux_startup import (
    GUNICORN_COMMAND,
    PLACEHOLDER_ENVIRONMENT,
    docker_command,
    validate_tree,
)


class LinuxStartupValidationTests(unittest.TestCase):
    def _deployment_tree(self, root: Path) -> None:
        for name in ("app.py", "requirements.txt", ".deployment"):
            (root / name).write_text("placeholder", encoding="utf-8")

    def test_valid_deployment_tree_has_root_entrypoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._deployment_tree(root)
            validate_tree(root)

    def test_deployment_tree_rejects_src_wrapper_and_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._deployment_tree(root)
            (root / "src").mkdir()
            with self.assertRaisesRegex(ValueError, "src"):
                validate_tree(root)
            (root / "src").rmdir()
            (root / ".env").write_text("not-a-secret", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, ".env"):
                validate_tree(root)

    def test_linux_command_uses_isolated_python_and_gunicorn_entrypoint(self):
        command = docker_command(PROJECT_ROOT / "src")
        self.assertIn("--network", command)
        self.assertIn("none", command)
        self.assertIn("python:3.11.15-slim", command)
        self.assertIn(GUNICORN_COMMAND, command[-1])
        self.assertIn("--env", command)
        self.assertIn(
            "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET="
            + PLACEHOLDER_ENVIRONMENT["CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET"],
            command,
        )
