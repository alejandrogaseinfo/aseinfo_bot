import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from handler import process_user_message
from intent import IntentResult
from models import BotDecision, EvidenceSource


class HandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = SimpleNamespace(
            openai_model_name="test-model",
            openai_intent_model_name="test-intent-model",
            retrieval_timeout_seconds=0.01,
            classification_timeout_seconds=0.01,
            intent_timeout_seconds=0.01,
            use_llm_intent_classifier=False,
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

    async def test_help_command_returns_guidance_without_retrieval(self):
        with patch("handler.retrieve_evidence") as retrieval:
            response = await process_user_message("ayuda", None, self.config)

        self.assertIn("producto o módulo", response)
        self.assertIn("mensaje exacto", response)
        retrieval.assert_not_called()

    async def test_natural_language_help_request_returns_guidance_without_retrieval(self):
        with patch("handler.retrieve_evidence") as retrieval:
            response = await process_user_message("necesito ayuda", None, self.config)

        self.assertIn("producto o módulo", response)
        retrieval.assert_not_called()

    async def test_greeting_with_orientation_request_returns_guidance_without_retrieval(self):
        with patch("handler.retrieve_evidence") as retrieval:
            response = await process_user_message("hola me podes orientar", None, self.config)

        self.assertIn("documentación técnica", response)
        retrieval.assert_not_called()

    async def test_llm_intent_routes_natural_language_help_without_retrieval(self):
        self.config.use_llm_intent_classifier = True
        self.config.model_endpoint_configured = True
        self.config.intent_timeout_seconds = 0.2
        self.config.conversation_timeout_seconds = 0.2
        with patch(
            "handler.classify_intent",
            return_value=IntentResult(name="ayuda", requires_context=False),
        ), patch(
            "handler.generate_conversational_response",
            return_value="Claro, cuéntame qué quieres revisar.",
        ), patch("handler.retrieve_evidence") as retrieval:
            response = await process_user_message("¿Me puedes orientar?", None, self.config)

        self.assertEqual("Claro, cuéntame qué quieres revisar.", response)
        retrieval.assert_not_called()

    async def test_llm_intent_routes_underspecified_error_without_retrieval(self):
        self.config.use_llm_intent_classifier = True
        self.config.model_endpoint_configured = True
        self.config.intent_timeout_seconds = 0.2
        self.config.conversation_timeout_seconds = 0.2
        with patch(
            "handler.classify_intent",
            return_value=IntentResult(name="reporte_error", requires_context=True),
        ), patch(
            "handler.generate_conversational_response",
            return_value="¿Qué producto y mensaje de error aparecen?",
        ), patch("handler.retrieve_evidence") as retrieval:
            response = await process_user_message("Me falla algo al entrar", None, self.config)

        self.assertEqual("¿Qué producto y mensaje de error aparecen?", response)
        retrieval.assert_not_called()

    async def test_llm_ambiguity_does_not_block_a_documentary_question(self):
        self.config.use_llm_intent_classifier = True
        self.config.model_endpoint_configured = True
        self.config.intent_timeout_seconds = 0.2
        self.config.classification_timeout_seconds = 0.2
        evidence = [
            EvidenceSource(
                tipo="azure_ai_search",
                titulo="Políticas de Pago SV — Página 1",
                ubicacion="https://contoso.example/politicas-sv.pdf",
                fragmento="En El Salvador se pagan la planilla mensual, el bono 14 y el aguinaldo.",
            )
        ]
        decision = BotDecision(
            estado="resuelto",
            confianza="alta",
            resumen="La documentación responde directamente la consulta.",
            fuentes=evidence,
        )

        with patch(
            "handler.classify_intent",
            return_value=IntentResult(name="consulta_ambigua", requires_context=True),
        ), patch("handler.retrieve_evidence", return_value=evidence) as retrieval, patch(
            "handler.classify_case", return_value=decision
        ):
            response = await process_user_message(
                "¿Cuáles son las planillas que se pagan en El Salvador?",
                None,
                self.config,
            )

        retrieval.assert_called_once()
        self.assertIn("La documentación responde", response)
        self.assertIn("Políticas de Pago SV", response)

    async def test_generic_error_request_requires_context_without_retrieval(self):
        with patch("handler.retrieve_evidence") as retrieval:
            response = await process_user_message("¿Cómo se corrige el error?", None, self.config)

        self.assertIn("Necesito más contexto", response)
        self.assertIn("producto o módulo", response)
        retrieval.assert_not_called()


if __name__ == "__main__":
    unittest.main()
