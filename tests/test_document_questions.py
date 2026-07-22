import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from azure_search import _document_relevance_score, _excerpt_around_query, _rerank_records
from classification import classify_case_by_rules
from document_index import tokenize
from formatting import format_user_response
from models import EvidenceSource
from models import BotDecision


class DocumentQuestionTests(unittest.TestCase):
    def test_excerpt_prefers_matching_sentence_over_chunk_start(self):
        content = (
            "Página 3 Información general de la planilla y parámetros administrativos. "
            "Los descuentos se gestionan conforme a la configuración vigente. "
            "Bono Decreto: Bono 37-2001, es de Q 250.00. Para empleados de nuevo "
            "ingreso es proporcional al tiempo laborado en el período."
        )

        excerpt = _excerpt_around_query(
            content,
            "¿Cuál es el valor del Bono Decreto 37-2001 para un empleado de nuevo ingreso?",
        )

        self.assertIn("Q 250.00", excerpt)
        self.assertIn("nuevo ingreso", excerpt)

    def test_excerpt_keeps_separate_facts_from_the_same_page(self):
        content = (
            "El aguinaldo equivale a quince días de salario después de un año continuo. "
            "Esta prestación se paga en diciembre. "
            "El aguinaldo está exento de renta hasta 30 UMA."
        )

        excerpt = _excerpt_around_query(
            content,
            "¿A cuántos días de salario equivale el aguinaldo y hasta cuánto está exento de renta?",
        )

        self.assertIn("quince días", excerpt)
        self.assertIn("30 UMA", excerpt)

    def test_calculation_question_keeps_the_formula(self):
        content = (
            "El aguinaldo se calcula proporcionalmente al tiempo trabajado. "
            "La empresa realiza el pago en diciembre. "
            "Ejemplo: días de aguinaldo = 15 * días trabajados / días del año. "
            "La fórmula de pago es salario diario * días de aguinaldo."
        )

        excerpt = _excerpt_around_query(
            content,
            "¿Cómo se calcula proporcionalmente el aguinaldo?",
        )

        self.assertIn("fórmula de pago", excerpt)

    def test_direct_document_question_is_resolved(self):
        evidence = [
            EvidenceSource(
                tipo="sharepoint",
                titulo="Políticas de Pago MEXICO — Página 14",
                ubicacion="https://contoso.example/politicas-mexico.pdf",
                fragmento=(
                    "El aguinaldo equivale a quince días de salario después de un año "
                    "de trabajo continuo y está exento de renta hasta 30 UMA."
                ),
            )
        ]

        decision = classify_case_by_rules(
            "En México, ¿a cuántos días de salario equivale el aguinaldo después de un año continuo y hasta cuánto está exento de renta?",
            evidence,
        )

        self.assertEqual("resuelto", decision.estado)
        self.assertFalse(decision.requiere_escalamiento)

    def test_important_numeric_terms_are_searchable(self):
        self.assertIn("37", tokenize("Bono Decreto 37-2001"))

    def test_plural_terms_normalize_without_altering_acronyms(self):
        tokens = tokenize("Empleados ISSS")
        self.assertIn("empleado", tokens)
        self.assertIn("isss", tokens)

    def test_inflected_terms_normalize_for_retrieval(self):
        self.assertIn("proporcional", tokenize("proporcionalmente proporcionales"))

    def test_camel_case_application_fields_are_searchable_by_concept(self):
        tokens = tokenize("BaseCalculoISSS")

        self.assertTrue({"base", "calculo", "isss"}.issubset(tokens))

    def test_specific_planilla_phrase_outranks_liquidation_page(self):
        question = "En la planilla quincenal, ¿cómo se aplican el ISSS, AFP e impuesto sobre la renta?"
        quincenal_page = {
            "title": "Políticas de Pago SV — Página 2",
            "content": (
                "Planilla Quincenal. Los descuentos de ley ISSS, AFP e Impuesto sobre "
                "la Renta serán aplicados en cada quincena con ajuste mensual."
            ),
        }
        liquidation_page = {
            "title": "Políticas de Pago SV — Página 14",
            "content": "En liquidación se aplican AFP, ISSS e Impuesto sobre la Renta.",
        }

        self.assertGreater(
            _document_relevance_score(quincenal_page, question),
            _document_relevance_score(liquidation_page, question),
        )

        ranked = _rerank_records([liquidation_page, quincenal_page], question)
        self.assertEqual(quincenal_page, ranked[0][1])

    def test_generic_coverage_prioritizes_calculation_page(self):
        question = "¿Cómo se aplica el ISR quincenal y qué descuentos se restan de su base?"
        tax_page = {
            "title": "Políticas de Pago SV — Página 6",
            "content": "ISR BaseCalculoRenta. Tabla de Renta Quincenal. Descuentos AFP e ISSS.",
        }
        monthly_page = {
            "title": "Políticas de Pago SV — Página 8",
            "content": "Planilla mensual: ISR, AFP e ISSS. Se usa el mismo agrupador de la planilla quincenal.",
        }

        ranked = _rerank_records([monthly_page, tax_page], question)
        self.assertEqual(tax_page, ranked[0][1])

    def test_vector_rank_breaks_a_lexical_tie(self):
        question = "¿Cómo se calcula el aguinaldo proporcional?"
        first_vector_result = {
            "title": "México — Página 9",
            "content": "El aguinaldo proporcional se calcula según los días laborados.",
            "_vector_rank": 1,
        }
        later_vector_result = {
            "title": "Guatemala — Página 7",
            "content": "El aguinaldo proporcional se calcula según los días laborados.",
            "_vector_rank": 20,
        }

        ranked = _rerank_records([later_vector_result, first_vector_result], question)

        self.assertEqual(first_vector_result, ranked[0][1])

    def test_unmatched_question_remains_without_evidence(self):
        evidence = [
            EvidenceSource(
                tipo="sharepoint",
                titulo="Políticas de Pago MEXICO — Página 14",
                ubicacion="https://contoso.example/politicas-mexico.pdf",
                fragmento="El aguinaldo está exento de renta hasta 30 UMA.",
            )
        ]

        decision = classify_case_by_rules(
            "¿Cuál es la fecha de vencimiento del certificado SSL?",
            evidence,
        )

        self.assertEqual("sin_evidencia", decision.estado)

    def test_teams_response_shows_only_answer_and_brief_source(self):
        response = format_user_response(
            BotDecision(
                estado="resuelto",
                confianza="alta",
                resumen="El aguinaldo equivale a quince días de salario.",
                fuentes=[
                    EvidenceSource(
                        tipo="azure_ai_search",
                        titulo="Políticas de Pago MEXICO — Página 14",
                        ubicacion="C:/datos/politicas.pdf",
                        fragmento="Texto de evidencia interno.",
                    )
                ],
                siguiente_accion="No aplica.",
            )
        )

        self.assertIn("El aguinaldo equivale", response)
        self.assertIn("Políticas de Pago MEXICO — Página 14", response)
        self.assertIn("Azure AI Search", response)
        self.assertNotIn("Estado", response)
        self.assertNotIn("Confianza", response)
        self.assertNotIn("Ruta de investigacion", response)

    def test_no_evidence_response_does_not_show_tangential_source(self):
        response = format_user_response(
            BotDecision(
                estado="sin_evidencia",
                confianza="baja",
                resumen="No se encontró evidencia suficiente.",
                fuentes=[
                    EvidenceSource(
                        tipo="documento",
                        titulo="Documento no relacionado",
                        ubicacion="docs/changelog.md",
                        fragmento="Texto no relacionado.",
                    )
                ],
            )
        )

        self.assertEqual("No se encontró evidencia suficiente.", response)

    def test_local_fallback_is_not_labeled_as_azure(self):
        response = format_user_response(
            BotDecision(
                estado="resuelto",
                confianza="media",
                resumen="Respuesta desde el respaldo local.",
                fuentes=[
                    EvidenceSource(
                        tipo="documento",
                        titulo="Documento local",
                        ubicacion="docs/prueba.md",
                        fragmento="Texto de respaldo.",
                    )
                ],
            )
        )

        self.assertIn("Base documental local", response)
        self.assertNotIn("Azure AI Search", response)


if __name__ == "__main__":
    unittest.main()
