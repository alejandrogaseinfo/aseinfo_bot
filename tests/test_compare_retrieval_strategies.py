import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from compare_retrieval_strategies import build_strategy_configs


class CompareRetrievalStrategiesTests(unittest.TestCase):
    def test_variants_keep_legacy_and_disable_azure_semantic_search(self):
        base = SimpleNamespace(
            retrieval_strategy="v2",
            azure_search_use_semantic=True,
        )

        variants = build_strategy_configs(base)

        self.assertEqual({
            "actual_legacy",
            "candidatos_ampliados",
            "ampliados_reranking_determinista",
        }, set(variants))
        self.assertEqual((60, 20), (
            variants["actual_legacy"].retrieval_merged_pool_limit,
            variants["actual_legacy"].retrieval_rerank_pool_limit,
        ))
        self.assertEqual((100, 40), (
            variants["candidatos_ampliados"].retrieval_merged_pool_limit,
            variants["candidatos_ampliados"].retrieval_rerank_pool_limit,
        ))
        self.assertTrue(all(variant.retrieval_strategy == "legacy" for variant in variants.values()))
        self.assertTrue(all(not variant.azure_search_use_semantic for variant in variants.values()))


if __name__ == "__main__":
    unittest.main()
