import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from handler import process_user_message
from models import BotDecision, EvidenceSource


class HandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = SimpleNamespace(
            openai_model_name="test-model",
            retrieval_timeout_seconds=0.01,
            classification_timeout_seconds=0.01,
        )

    async def test_retrieval_timeout_returns_safe_no_evidence_response(self):
        def slow_retrieval(*_args, **_kwargs):
            time.sleep(0.05)
            return []

        with patch("handler.retrieve_evidence", side_effect=slow_retrieval):
            response = await process_user_message("¿Qué dice el manual?", None, self.config)

        self.assertIn("No se encontro evidencia suficiente", response)

    async def test_classification_timeout_uses_rule_based_decision(self):
        evidence = [
            EvidenceSource(
                tipo="sharepoint",
                titulo="Manual de nómina",
                ubicacion="https://contoso.example/manual.pdf",
                fragmento="El aguinaldo equivale a quince días de salario.",
            )
        ]

        def slow_classification(*_args, **_kwargs):
            time.sleep(0.05)
            return BotDecision("sin_evidencia", "baja", "No usar", [])

        with patch("handler.retrieve_evidence", return_value=evidence), patch(
            "handler.classify_case", side_effect=slow_classification
        ):
            self.config.retrieval_timeout_seconds = 0.2
            response = await process_user_message(
                "¿A cuántos días equivale el aguinaldo?", None, self.config
            )

        self.assertIn("Se encontró documentación", response)
        self.assertIn("Manual de nómina", response)

    async def test_query_telemetry_omits_the_user_message_and_evidence_text(self):
        self.config.retrieval_timeout_seconds = 0.2
        self.config.classification_timeout_seconds = 0.2
        question = "Clave confidencial: no debe aparecer en los registros"
        evidence = [
            EvidenceSource(
                tipo="sharepoint",
                titulo="Manual de nómina",
                ubicacion="https://contoso.example/manual.pdf",
                fragmento="Texto interno que tampoco debe aparecer en los registros.",
            )
        ]
        decision = BotDecision(
            estado="resuelto",
            confianza="alta",
            resumen="La documentación responde la consulta.",
            fuentes=evidence,
        )

        with patch("handler.retrieve_evidence", return_value=evidence), patch(
            "handler.classify_case", return_value=decision
        ), self.assertLogs("chat_salvador", level="INFO") as captured:
            await process_user_message(question, None, self.config)

        telemetry = "\n".join(captured.output)
        self.assertIn("query_completed", telemetry)
        self.assertIn("evidence_count=1", telemetry)
        self.assertNotIn(question, telemetry)
        self.assertNotIn(evidence[0].fragmento, telemetry)


if __name__ == "__main__":
    unittest.main()
