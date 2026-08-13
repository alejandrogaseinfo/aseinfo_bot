from pathlib import Path
import unittest


class PostDeploymentValidationTests(unittest.TestCase):
    def test_ai_first_validation_checks_files_and_imports(self):
        script = (Path(__file__).parents[1] / "scripts" / "validate_post_deployment_ai_first.sh").read_text(encoding="utf-8")
        self.assertIn('test -f "$APP_ROOT/ai_first.py"', script)
        self.assertIn('test -f "$APP_ROOT/handler.py"', script)
        self.assertIn('PYTHONPATH="$APP_ROOT" python -c', script)
        self.assertIn('import ai_first, handler', script)
