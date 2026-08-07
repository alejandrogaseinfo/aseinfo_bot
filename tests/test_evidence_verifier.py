import json
import sys
import unittest
from types import SimpleNamespace


sys.path.insert(0, "src")

from evidence_verifier import verify_semantic_evidence
from query_plan import build_query_plan


class EvidenceVerifierTests(unittest.TestCase):
    def test_keeps_only_known_candidate_and_requirement_ids(self):
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **_kwargs: SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                message=SimpleNamespace(
                                    content=json.dumps(
                                        {
                                            "verdicts": [
                                                {"candidate_id": "good", "requirements": ["r1", "bad"]},
                                                {"candidate_id": "unknown", "requirements": ["r1"]},
                                            ]
                                        }
                                    )
                                )
                            )
                        ]
                    )
                )
            )
        )
        plan = build_query_plan("¿Cómo se administran documentos en Evolution?")

        verdicts = verify_semantic_evidence(
            plan,
            [{"candidate_id": "good", "title": "Manual", "fragments": []}],
            client,
            "test-model",
        )

        self.assertEqual({"good": ("r1",)}, verdicts)
