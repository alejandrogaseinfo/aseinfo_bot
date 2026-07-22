import unittest

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config import Config


class ConfigTests(unittest.TestCase):
    def test_openai_base_url_is_optional_and_normalized(self):
        config = Config({"OPENAI_BASE_URL": "http://127.0.0.1:11434/v1/"})

        self.assertEqual("http://127.0.0.1:11434/v1", config.openai_base_url)
        self.assertEqual("", config.openai_api_key)

    def test_embedding_configuration_has_safe_defaults(self):
        config = Config({})

        self.assertEqual("text-embedding-3-small", config.openai_embedding_model)
        self.assertEqual(1536, config.openai_embedding_dimensions)


if __name__ == "__main__":
    unittest.main()
