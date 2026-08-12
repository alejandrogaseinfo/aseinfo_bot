import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from azure_search import (
    _chunks_for_document,
    _query_synonym_tokens,
    _v2_score,
    _v2_semantic_coverage_is_anchored,
    retrieve_azure_search_evidence,
)
from classification import classify_case_by_rules
from query_plan import build_query_plan, concept_key, covered_requirements, requirement_is_covered


class QueryPlanTests(unittest.TestCase):
    def test_morphology_uses_a_generic_concept_key(self):
        self.assertEqual("ofusc", concept_key("ofuscan"))
        self.assertEqual("ofusc", concept_key("ofuscación"))
        self.assertEqual("administr", concept_key("gestionar"))
        self.assertEqual("modific", concept_key("modifique"))
        self.assertEqual("negativ", concept_key("negativa"))
        self.assertEqual("negativ", concept_key("negativos"))

    def test_legacy_synonyms_keep_document_administration_paraphrases_equivalent(self):
        first_wording = _query_synonym_tokens({"administran", "documentos"})
        second_wording = _query_synonym_tokens({"administrar", "documentos"})

        self.assertIn("gestion", first_wording)
        self.assertIn("gestionar", first_wording)
        self.assertEqual(first_wording, second_wording)

    def test_platform_context_does_not_become_a_required_evidence_anchor(self):
        plan = build_query_plan(
            "¿Qué parámetros se pueden configurar para prórroga de contratos en Evolution?"
        )

        self.assertNotIn("evolution", plan.requirements[0].concepts)

    def test_outcome_word_does_not_hide_specific_dtc_validation_evidence(self):
        plan = build_query_plan(
            "¿Qué hay que revisar en ambos servidores para confirmar que la comunicación DTC funciona?"
        )

        self.assertEqual(("servidor", "dtc"), plan.requirements[0].concepts)
        self.assertEqual((), plan.requirements[0].actions)

    def test_multi_part_question_preserves_each_requirement(self):
        plan = build_query_plan(
            "¿Cómo se ofuscan datos sensibles en SQL y qué procedimiento de respaldo se aplica?"
        )

        self.assertEqual(("r1", "r2", "r3"), plan.requirement_ids)
        self.assertEqual(
            ("r1", "r2"),
            covered_requirements(
                plan,
                "Ofuscación de datos SQL. El script aplica una transformación a los datos sensibles.",
            ),
        )

    def test_sql_is_chunked_by_declaration(self):
        chunks = list(
            _chunks_for_document(
                Path("procedimientos.sql"),
                "CREATE PROCEDURE dbo.uno AS SELECT 1;\nGO\n"
                "CREATE PROCEDURE dbo.dos AS SELECT 2;",
            )
        )

        self.assertEqual(2, len(chunks))
        self.assertTrue(chunks[0].startswith("CREATE PROCEDURE dbo.uno"))
        self.assertTrue(chunks[1].startswith("CREATE PROCEDURE dbo.dos"))

    def test_requirement_rejects_a_tangential_action_without_its_subject(self):
        requirement = build_query_plan(
            "¿Qué parámetros se pueden modificar para incapacidades?"
        ).requirements[0]

        self.assertFalse(
            requirement_is_covered(
                requirement,
                "Modificar parámetros de una plantilla de importación. "
                + ("Texto de otra sección. " * 80)
                + "Las incapacidades se muestran en un reporte independiente.",
            )
        )

    def test_preinstallation_precaution_scaffolding_does_not_become_an_evidence_anchor(self):
        plan = build_query_plan(
            "¿Qué precauciones se deben tomar antes de instalar una actualización de Evolution?"
        )
        requirement = plan.requirements[0]

        self.assertEqual(("instal", "actualiz"), requirement.concepts)
        self.assertIn(
            "instalacion actualizacion recomendaciones iniciales respaldo preparacion",
            plan.retrieval_queries,
        )

    def test_v2_scoring_prefers_preinstallation_evidence_over_generic_configuration(self):
        plan = build_query_plan(
            "¿Qué precauciones se deben tomar antes de instalar una actualización de Evolution?"
        )
        checklist = {
            "title": "Readme de actualización",
            "content": "Recomendaciones iniciales: preparar un respaldo previo a la instalación.",
        }
        generic = {
            "title": "Actualización de driver",
            "content": "Configurar el driver después de la instalación.",
        }

        self.assertGreater(
            _v2_score(checklist, ("r1",), plan),
            _v2_score(generic, ("r1",), plan),
        )

    def test_v2_scoring_prefers_a_title_with_the_explicit_acronym(self):
        plan = build_query_plan("¿Cómo verificar la comunicación DTC entre dos servidores?")
        named = {"title": "Manual DTC Verificación", "content": "Verificar servidores."}
        generic = {"title": "Guía técnica", "content": "Verificar servidores y comunicación."}

        self.assertGreater(
            _v2_score(named, ("r1",), plan),
            _v2_score(generic, ("r1",), plan),
        )

    def test_script_evidence_can_cover_anchors_across_code_lines(self):
        requirement = build_query_plan(
            "¿Cómo puedo arreglar vacaciones negativas con un script?"
        ).requirements[0]

        self.assertTrue(
            requirement_is_covered(
                requirement,
                "El artefacto de tipo script titulado acc.proc_arreglar_vac_negativos.sql contiene "
                "CREATE PROCEDURE acc.proc_arreglar_vac_negativos(\n"
                "SELECT * FROM acc.vac_vacaciones\n"
                "WHERE vac_saldo < 0",
            )
        )

    def test_semantic_anchor_rejects_topic_heading_and_unrelated_parameter_sentence(self):
        plan = build_query_plan(
            "¿Qué parámetros se pueden configurar para prórroga de contratos en Evolution?"
        )
        record = {
            "artifact_role": "manual",
            "content": (
                "Prórroga de contratos. Administración de licencias. "
                "La pantalla se puede configurar con un parámetro de aplicación."
            ),
        }

        self.assertFalse(_v2_semantic_coverage_is_anchored(record, plan, ("r1",)))

    def test_semantic_anchor_rejects_subject_without_requested_action(self):
        plan = build_query_plan("¿Cómo se clasifican las incapacidades en Evolution?")
        record = {
            "artifact_role": "manual",
            "content": (
                "Incapacidades. Esta opción almacena la información de la acción "
                "en las tablas correspondientes."
            ),
        }

        self.assertFalse(_v2_semantic_coverage_is_anchored(record, plan, ("r1",)))


class V2EvidenceTests(unittest.TestCase):
    @staticmethod
    def _config():
        return SimpleNamespace(
            retrieval_strategy="v2",
            azure_search_endpoint="https://search.example",
            azure_search_index_name="libras-docs",
            azure_search_api_key="not-a-real-key",
            azure_search_use_entra_id=False,
            azure_search_use_semantic=False,
            sharepoint_sources=(("", "drive-scripts"),),
        )

    def test_v2_rejects_navigation_and_returns_direct_sql_evidence(self):
        class FakeSearchClient:
            def __init__(self):
                self.calls = []

            def search(self, **kwargs):
                self.calls.append(kwargs)
                return [
                    {
                        "id": "contents",
                        "title": "Manual SQL — Página 2",
                        "source_url": "https://contoso.example/manual.pdf",
                        "source_system": "sharepoint",
                        "folder_path": "",
                        "drive_id": "drive-scripts",
                        "artifact_role": "script",
                        "quality_status": "aprobado",
                        "evidence_kind": "navigation",
                        "content": "Tabla de contenido. Ofuscación de datos, 3, 4, 5, 6, 7, 8.",
                    },
                    {
                        "id": "ofuscacion",
                        "title": "Ofuscación de datos.sql — Documento",
                        "source_url": "https://contoso.example/ofuscacion.sql",
                        "source_system": "sharepoint",
                        "folder_path": "",
                        "drive_id": "drive-scripts",
                        "document_id": "ofuscacion",
                        "document_type": "sql",
                        "artifact_role": "script",
                        "quality_status": "aprobado",
                        "evidence_kind": "primary",
                        "retrieval_text": "Archivo Ofuscación de datos.sql. Tipo de artefacto script.",
                        "retrieval_concepts": "ofusc dato sql script",
                        "content": "El script SQL transforma los datos sensibles mediante la función de ofuscación.",
                    },
                ]

        fake = FakeSearchClient()
        with patch("azure_search.SearchClient", return_value=fake), patch(
            "azure_search._embed_texts", return_value=[[0.0, 0.0]]
        ):
            trace = retrieve_azure_search_evidence(
                "¿Cómo se ofuscan datos sensibles en SQL?",
                self._config(),
                return_trace=True,
            )

        self.assertEqual(["Ofuscación de datos.sql — Documento"], [source.titulo for source in trace.sources])
        self.assertEqual(("r1", "r2"), trace.sources[0].covered_requirements)
        self.assertEqual(1, trace.rejected_reasons["evidence_kind"])
        self.assertTrue(any("retrieval_text" in call["select"] for call in fake.calls))

    def test_v2_uses_reviewed_artifact_role_for_a_script_request(self):
        class FakeSearchClient:
            def search(self, **_kwargs):
                return [
                    {
                        "id": "vac-negatives",
                        "title": "acc.proc_arreglar_vac_negativos.sql — Documento",
                        "source_url": "https://contoso.example/vac.sql",
                        "source_system": "sharepoint",
                        "folder_path": "",
                        "drive_id": "drive-scripts",
                        "artifact_role": "script",
                        "quality_status": "aprobado",
                        "evidence_kind": "primary",
                        "operation": "acc.proc_arreglar_vac_negativos",
                        "content": "Este procedimiento arregla vacaciones negativas.",
                    }
                ]

        with patch("azure_search.SearchClient", return_value=FakeSearchClient()), patch(
            "azure_search._embed_texts", return_value=[[0.0, 0.0]]
        ):
            trace = retrieve_azure_search_evidence(
                "¿Cómo puedo arreglar vacaciones negativas con un script?",
                self._config(),
                return_trace=True,
            )

        self.assertEqual(["acc.proc_arreglar_vac_negativos.sql — Documento"], [source.titulo for source in trace.sources])

    def test_v2_partial_evidence_declares_the_unsupported_subquestion(self):
        class FakeSearchClient:
            def search(self, **_kwargs):
                return [
                    {
                        "id": "ofuscacion",
                        "title": "Ofuscación de datos.sql — Documento",
                        "source_url": "https://contoso.example/ofuscacion.sql",
                        "source_system": "sharepoint",
                        "folder_path": "",
                        "drive_id": "drive-scripts",
                        "artifact_role": "script",
                        "quality_status": "aprobado",
                        "evidence_kind": "primary",
                        "retrieval_text": "Archivo Ofuscación de datos.sql. Tipo de artefacto script.",
                        "retrieval_concepts": "ofusc dato sql script",
                        "content": "El script SQL transforma los datos sensibles mediante la función de ofuscación.",
                    }
                ]

        question = "¿Cómo se ofuscan datos sensibles en SQL y qué procedimiento de respaldo se aplica?"
        with patch("azure_search.SearchClient", return_value=FakeSearchClient()), patch(
            "azure_search._embed_texts", return_value=[[0.0, 0.0]]
        ):
            trace = retrieve_azure_search_evidence(question, self._config(), return_trace=True)

        decision = classify_case_by_rules(question, trace.sources)

        self.assertEqual("resuelto", decision.estado)
        self.assertTrue(decision.requiere_escalamiento)
        self.assertIn("No encontré evidencia directa", decision.resumen)
        self.assertEqual(["Ofuscación de datos.sql — Documento"], [source.titulo for source in decision.fuentes])

    def test_v2_does_not_cite_reference_artifacts(self):
        class FakeSearchClient:
            def search(self, **_kwargs):
                return [
                    {
                        "id": "reference-links",
                        "title": "Links de apoyo — Documento",
                        "source_url": "https://contoso.example/links.docx",
                        "source_system": "sharepoint",
                        "folder_path": "",
                        "drive_id": "drive-scripts",
                        "quality_status": "aprobado",
                        "evidence_kind": "reference",
                        "content": "Descuentos legales de El Salvador.",
                    }
                ]

        with patch("azure_search.SearchClient", return_value=FakeSearchClient()), patch(
            "azure_search._embed_texts", return_value=[[0.0, 0.0]]
        ):
            trace = retrieve_azure_search_evidence(
                "¿Qué descuentos legales existen en El Salvador?",
                self._config(),
                return_trace=True,
            )

        self.assertEqual([], trace.sources)
        self.assertEqual(1, trace.rejected_reasons["evidence_kind"])

    def test_v2_can_use_bounded_semantic_verification_after_deterministic_failure(self):
        class FakeSearchClient:
            def search(self, **_kwargs):
                return [
                    {
                        "id": "contract-extension",
                        "title": "Acciones de personal.pdf — Página 18",
                        "source_url": "https://contoso.example/acciones.pdf",
                        "source_system": "sharepoint",
                        "folder_path": "",
                        "drive_id": "drive-scripts",
                        "artifact_role": "manual",
                        "quality_status": "aprobado",
                        "evidence_kind": "primary",
                        "content": (
                            "Los parámetros de prórroga de contratos permiten definir fechas "
                            "y opciones de vigencia en Evolution."
                        ),
                    }
                ]

        class FakeVerifierClient:
            chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **_kwargs: SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                message=SimpleNamespace(
                                    content='{"verdicts":[{"candidate_id":"c01","requirements":["r1"],"confidence":0.9}]}'
                                )
                            )
                        ]
                    )
                )
            )

        config = self._config()
        config.use_llm_evidence_verifier = True
        config.evidence_verifier_model_name = "test-model"
        config.openai_intent_model_name = "test-model"
        with patch("azure_search.SearchClient", return_value=FakeSearchClient()), patch(
            "azure_search._embed_texts", return_value=[[0.0, 0.0]]
        ):
            trace = retrieve_azure_search_evidence(
                "¿Qué parámetros se pueden configurar para prórroga de contratos en Evolution?",
                config,
                client=FakeVerifierClient(),
                return_trace=True,
            )

        self.assertEqual(["Acciones de personal.pdf — Página 18"], [source.titulo for source in trace.sources])
        self.assertEqual(("r1",), trace.sources[0].covered_requirements)


class LegacyParaphraseRegressionTests(unittest.TestCase):
    @staticmethod
    def _config():
        return SimpleNamespace(
            retrieval_strategy="legacy",
            azure_search_configured=True,
            azure_search_endpoint="https://search.example",
            azure_search_index_name="libras-docs",
            azure_search_api_key="not-a-real-key",
            azure_search_use_entra_id=False,
            azure_search_use_semantic=False,
            sharepoint_sources=(("", "drive-manuales"),),
            sharepoint_source_labels=(),
        )

    def test_legacy_retrieves_the_same_manual_for_both_document_administration_phrasings(self):
        record = {
            "id": "gestion-documentos-p6",
            "document_id": "gestion-documentos",
            "title": "Gestion de documentos.pdf — Página 6",
            "source_url": "https://contoso.example/Gestion%20de%20documentos.pdf",
            "source_system": "sharepoint",
            "folder_path": "",
            "drive_id": "drive-manuales",
            "document_type": "pdf",
            "content_tokens": "gestion documentos administrar",
            "content": (
                "Gestión de documentos. Seleccione el Módulo Gestión de documentos. "
                "Seleccione la opción Administrar documentos Gestionados."
            ),
        }

        class FakeSearchClient:
            def __init__(self):
                self.queries = []

            def search(self, **kwargs):
                query = str(kwargs.get("search_text") or "").casefold()
                self.queries.append(query)
                return [record] if "gestion" in query else []

        fake = FakeSearchClient()
        with patch("azure_search.SearchClient", return_value=fake):
            first_sources = retrieve_azure_search_evidence(
                "¿Cómo se administran los documentos en Evolution?", self._config()
            )
            second_sources = retrieve_azure_search_evidence(
                "¿Cómo se pueden administrar los documentos en Evolution?", self._config()
            )

        self.assertEqual([record["title"]], [source.titulo for source in first_sources])
        self.assertEqual([record["title"]], [source.titulo for source in second_sources])
        self.assertGreaterEqual(sum("gestion" in query for query in fake.queries), 2)


if __name__ == "__main__":
    unittest.main()
