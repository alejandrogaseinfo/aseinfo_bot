import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from azure_search import (
    CHANGE_MANIFEST_NAME,
    _credential,
    _changed_document_ids,
    _clear_change_manifest,
    _clear_deletion_manifest,
    _deletion_document_ids,
    _document_records,
    _document_pages,
    _chunks,
    _document_relevance_score,
    _has_minimum_content_coverage,
    _filter_records_for_requested_country,
    _record_has_authorized_provenance,
    _entra_credential,
    _excerpt_around_query,
    _rerank_records,
    retrieve_azure_search_evidence,
    index_directory,
)
from classification import classify_case_by_rules
from document_index import tokenize
from formatting import format_user_response
from models import EvidenceSource
from models import BotDecision
from sharepoint_sync import (
    CHANGE_MANIFEST_NAME as SYNC_CHANGE_MANIFEST_NAME,
    DELETION_MANIFEST_NAME,
    _change_ids,
    sync_pdfs,
)


class DocumentQuestionTests(unittest.TestCase):
    def test_retrieval_uses_fields_supported_by_legacy_search_indexes(self):
        class FakeSearchClient:
            def __init__(self):
                self.calls = []

            def search(self, **kwargs):
                self.calls.append(kwargs)
                return [
                    {
                        "id": "sv-page-1",
                        "title": "Políticas de Pago SV.pdf — Página 1",
                        "source_url": "https://contoso.example/politicas-sv.pdf",
                        "source_system": "sharepoint",
                        "document_context": "El Salvador. Planilla Mensual, Planilla Quincenal y Planilla Aguinaldo.",
                        "content": "El Salvador. Dentro del proyecto se contemplan la Planilla Mensual, la Planilla Quincenal y la Planilla Aguinaldo.",
                        "content_tokens": "salvador planilla mensual quincenal aguinaldo",
                    }
                ]

        fake_search = FakeSearchClient()
        config = SimpleNamespace(
            azure_search_configured=True,
            azure_search_endpoint="https://search.example",
            azure_search_index_name="chat-salvador-docs",
            azure_search_api_key="not-a-real-key",
            azure_search_use_entra_id=False,
            openai_api_key="test-key",
            openai_base_url="",
            resolved_openai_base_url="https://api.openai.com/v1",
            openai_embedding_model="text-embedding-3-small",
        )

        with patch("azure_search.SearchClient", return_value=fake_search), patch(
            "azure_search._embed_texts", return_value=[[0.0, 0.0]]
        ):
            sources = retrieve_azure_search_evidence(
                "¿Cuáles son las planillas que se pagan en El Salvador?",
                config,
            )

        self.assertEqual("Políticas de Pago SV.pdf — Página 1", sources[0].titulo)
        for call in fake_search.calls:
            self.assertNotIn("document_id", call["select"])
            self.assertNotIn("document_version", call["select"])
            self.assertIn("folder_path", call["select"])

    def test_explicit_filename_prioritizes_the_exact_indexed_document(self):
        requested_name = "sp_anular_solicitud_vac.sql"

        class FakeSearchClient:
            def search(self, **kwargs):
                if kwargs.get("search_text") == requested_name:
                    return [
                        {
                            "id": "scripts-anular-vac",
                            "title": f"{requested_name} — Documento",
                            "source_url": "https://contoso.example/scripts/sp_anular_solicitud_vac.sql",
                            "source_system": "sharepoint",
                            "folder_path": "",
                            "drive_id": "drive-scripts",
                            "content": "EXEC sp_anular_solicitud_vac @id_solicitud = 123;",
                            "content_tokens": "exec sp anular solicitud vac id solicitud",
                        }
                    ]
                return [
                    {
                        "id": "related-config",
                        "title": "ConfiguracionAnulacionSolicitudVac.sql — Documento",
                        "source_url": "https://contoso.example/scripts/ConfiguracionAnulacionSolicitudVac.sql",
                        "source_system": "sharepoint",
                        "folder_path": "",
                        "drive_id": "drive-scripts",
                        "content": "Configuración relacionada con solicitudes de vacaciones.",
                        "content_tokens": "configuracion anulacion solicitud vacaciones",
                    }
                ]

        config = SimpleNamespace(
            azure_search_configured=True,
            azure_search_endpoint="https://search.example",
            azure_search_index_name="libras-docs",
            azure_search_api_key="not-a-real-key",
            azure_search_use_entra_id=False,
            sharepoint_sources=(("", "drive-scripts"),),
        )

        with patch("azure_search.SearchClient", return_value=FakeSearchClient()), patch(
            "azure_search._embed_texts", return_value=[[0.0, 0.0]]
        ):
            sources = retrieve_azure_search_evidence(
                "Busca exactamente el archivo sp_anular_solicitud_vac.sql. "
                "¿Qué parámetros utiliza y qué operación realiza?",
                config,
            )

        self.assertEqual([f"{requested_name} — Documento"], [source.titulo for source in sources])

    def test_unknown_explicit_filename_does_not_fall_back_to_related_documents(self):
        class FakeSearchClient:
            def search(self, **kwargs):
                return [
                    {
                        "id": "related-readme",
                        "title": "Readme 1.19.1.13.pdf — Página 7",
                        "source_url": "https://contoso.example/readme.pdf",
                        "source_system": "sharepoint",
                        "folder_path": "",
                        "drive_id": "drive-readme",
                        "content": "Validación previa a la instalación de una actualización.",
                        "content_tokens": "validacion previa instalacion actualizacion",
                    }
                ]

        config = SimpleNamespace(
            azure_search_configured=True,
            azure_search_endpoint="https://search.example",
            azure_search_index_name="libras-docs",
            azure_search_api_key="not-a-real-key",
            azure_search_use_entra_id=False,
            sharepoint_sources=(("", "drive-readme"),),
        )

        with patch("azure_search.SearchClient", return_value=FakeSearchClient()), patch(
            "azure_search._embed_texts", return_value=[[0.0, 0.0]]
        ):
            sources = retrieve_azure_search_evidence(
                "Busca exactamente el archivo procedimiento_inexistente.sql.", config
            )

        self.assertEqual([], sources)

    def test_entra_credential_is_reused_for_multiple_search_operations(self):
        config = SimpleNamespace(
            azure_search_api_key="",
            azure_search_use_entra_id=True,
        )
        _entra_credential.cache_clear()
        try:
            with patch("azure_search.DefaultAzureCredential") as credential_class:
                first = _credential(config)
                second = _credential(config)

            self.assertIs(first, second)
            credential_class.assert_called_once_with(
                exclude_interactive_browser_credential=False
            )
        finally:
            _entra_credential.cache_clear()

    def test_evidence_source_preserves_optional_document_metadata(self):
        source = EvidenceSource(
            tipo="sharepoint",
            titulo="Manual",
            ubicacion="https://contoso.example/manual.pdf",
            fragmento="Texto de prueba.",
            document_id="drive-item-123",
            document_version='"etag-2"',
            last_modified="2026-07-22T12:00:00Z",
            document_type="pdf",
            folder_path="Operaciones/Manuales",
        )

        self.assertEqual("drive-item-123", source.document_id)
        self.assertEqual("pdf", source.document_type)
        self.assertEqual("Operaciones/Manuales", source.folder_path)

    def test_deletion_manifest_is_read_and_cleared_after_indexing(self):
        with TemporaryDirectory() as directory:
            source_dir = Path(directory)
            manifest = source_dir / DELETION_MANIFEST_NAME
            manifest.write_text(
                '{"deleted_document_ids": ["one", "two", "one"]}', encoding="utf-8"
            )

            self.assertEqual({"one", "two"}, _deletion_document_ids(source_dir))
            _clear_deletion_manifest(source_dir)
            self.assertEqual(set(), _deletion_document_ids(source_dir))

    def test_change_manifest_is_read_and_cleared_after_indexing(self):
        with TemporaryDirectory() as directory:
            source_dir = Path(directory)
            manifest = source_dir / CHANGE_MANIFEST_NAME
            manifest.write_text(
                '{"changed_document_ids": ["one", "two", "one"]}', encoding="utf-8"
            )

            self.assertEqual({"one", "two"}, _changed_document_ids(source_dir))
            _clear_change_manifest(source_dir)
            self.assertEqual(set(), _changed_document_ids(source_dir))

    def test_pdf_records_include_stable_sharepoint_metadata(self):
        with TemporaryDirectory() as directory:
            source_dir = Path(directory)
            pdf_path = source_dir / "manual.pdf"
            pdf_path.write_bytes(b"placeholder")
            pdf_path.with_suffix(".pdf.metadata.json").write_text(
                """{
                  "source_system": "sharepoint",
                  "document_id": "drive-item-123",
                  "etag": "etag-2",
                  "last_modified": "2026-07-22T12:00:00Z",
                  "web_url": "https://contoso.example/manual.pdf",
                  "folder_path": "Operaciones/Manuales",
                  "drive_id": "drive-1"
                }""",
                encoding="utf-8",
            )
            with patch(
                "azure_search._document_pages",
                return_value=[(1, "Procedimiento para instalar el hotfix de nómina.")],
            ):
                records = _document_records(source_dir)

        self.assertEqual(1, len(records))
        record = records[0]
        self.assertEqual("drive-item-123", record["document_id"])
        self.assertEqual("etag-2", record["document_version"])
        self.assertEqual("pdf", record["document_type"])
        self.assertEqual("Operaciones/Manuales", record["folder_path"])
        self.assertEqual("drive-1", record["drive_id"])
        self.assertTrue(record["content_hash"])
        self.assertTrue(record["indexed_at"])

    def test_pdf_records_ignore_sharepoint_files_outside_sync_state(self):
        with TemporaryDirectory() as directory:
            source_dir = Path(directory)
            (source_dir / ".libras-sharepoint-sync-state.json").write_text(
                '{"documents": {"allowed-id": {"filename": "allowed.pdf"}}}',
                encoding="utf-8",
            )
            for filename, document_id in (("allowed.pdf", "allowed-id"), ("stale.pdf", "stale-id")):
                pdf_path = source_dir / filename
                pdf_path.write_bytes(b"placeholder")
                pdf_path.with_suffix(".pdf.metadata.json").write_text(
                    json.dumps(
                        {
                            "source_system": "sharepoint",
                            "document_id": document_id,
                            "web_url": f"https://contoso.example/{filename}",
                        }
                    ),
                    encoding="utf-8",
                )
            with patch(
                "azure_search._document_pages",
                return_value=[(1, "Contenido controlado.")],
            ):
                records = _document_records(source_dir)

        self.assertEqual({"allowed-id"}, {record["document_id"] for record in records})

    def test_readable_office_files_are_extracted(self):
        from docx import Document
        from openpyxl import Workbook

        with TemporaryDirectory() as directory:
            source_dir = Path(directory)
            docx_path = source_dir / "manual.docx"
            document = Document()
            document.add_paragraph("Paso documentado para instalar el módulo.")
            document.save(docx_path)

            xlsx_path = source_dir / "parametros.xlsx"
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.title = "Configuración"
            worksheet.append(["Parametro", "Valor"])
            worksheet.append(["Timeout", "30"])
            workbook.save(xlsx_path)

            docx_pages = _document_pages(docx_path)
            xlsx_pages = _document_pages(xlsx_path)

        self.assertIn("Paso documentado", docx_pages[0][1])
        self.assertIn("Configuración", xlsx_pages[0][1])
        self.assertIn("Timeout | 30", xlsx_pages[0][1])

    def test_chunks_bound_long_lines_for_embedding_limits(self):
        chunks = list(_chunks("x" * 13_000, size=450, max_characters=6_000))

        self.assertEqual([6_000, 6_000, 1_000], [len(chunk) for chunk in chunks])

    def test_empty_documents_are_skipped(self):
        with TemporaryDirectory() as directory:
            empty_pdf = Path(directory) / "empty.pdf"
            empty_pdf.touch()

            self.assertEqual([], _document_pages(empty_pdf))

    def test_sync_reuses_unchanged_pdf_and_preserves_pending_deletion(self):
        class FakeSharePointClient:
            drive_id = "drive-1"

            def __init__(self):
                self.files = [
                    {
                        "id": "document-1",
                        "name": "manual.pdf",
                        "eTag": '"etag-1"',
                        "webUrl": "https://contoso.example/manual.pdf",
                        "lastModifiedDateTime": "2026-07-22T12:00:00Z",
                    }
                ]
                self.download_calls = 0

            def list_pdfs(self):
                return self.files

            def download(self, _item, destination):
                self.download_calls += 1
                destination.write_bytes(b"placeholder PDF")

        fake_client = FakeSharePointClient()
        config = SimpleNamespace(
            sharepoint_site_id="site-1",
            sharepoint_folder_path="Operaciones",
        )

        with TemporaryDirectory() as directory, patch(
            "sharepoint_sync.create_sharepoint_client", return_value=fake_client
        ):
            source_dir = Path(directory)
            sync_pdfs(config, source_dir)
            sync_pdfs(config, source_dir)
            self.assertEqual(1, fake_client.download_calls)
            self.assertEqual({"document-1"}, _change_ids(source_dir / SYNC_CHANGE_MANIFEST_NAME))

            fake_client.files[0]["name"] = "manual-renombrado.pdf"
            sync_pdfs(config, source_dir)
            self.assertEqual(2, fake_client.download_calls)
            self.assertFalse((source_dir / "document-1_manual.pdf").exists())
            self.assertTrue((source_dir / "document-1_manual-renombrado.pdf").exists())

            fake_client.files = []
            sync_pdfs(config, source_dir)
            self.assertEqual({"document-1"}, _deletion_document_ids(source_dir))
            self.assertEqual(set(), _change_ids(source_dir / SYNC_CHANGE_MANIFEST_NAME))
            self.assertFalse((source_dir / "document-1_manual-renombrado.pdf").exists())

            # If Azure ingestion has not yet acknowledged the deletion, a
            # subsequent sync must retain the tombstone instead of losing it.
            sync_pdfs(config, source_dir)
            self.assertEqual({"document-1"}, _deletion_document_ids(source_dir))

    def test_index_directory_only_embeds_pending_sharepoint_changes(self):
        class FakeSearchClient:
            def __init__(self):
                self.uploaded_records = []

            def search(self, **_kwargs):
                return []

            def merge_or_upload_documents(self, documents):
                self.uploaded_records.extend(documents)
                return [
                    SimpleNamespace(succeeded=True, key=document["id"])
                    for document in documents
                ]

            def delete_documents(self, documents):
                return [
                    SimpleNamespace(succeeded=True, key=document["id"])
                    for document in documents
                ]

        config = SimpleNamespace(
            azure_search_configured=True,
            azure_search_endpoint="https://search.example",
            azure_search_index_name="libras-docs",
            azure_search_api_key="not-a-real-key",
        )
        fake_search = FakeSearchClient()
        with TemporaryDirectory() as directory:
            source_dir = Path(directory)
            for document_id in ("document-1", "document-2"):
                pdf_path = source_dir / f"{document_id}.pdf"
                pdf_path.write_bytes(b"placeholder")
                pdf_path.with_suffix(".pdf.metadata.json").write_text(
                    (
                        '{"source_system": "sharepoint", '
                        f'"document_id": "{document_id}", "etag": "etag-1"}}'
                    ),
                    encoding="utf-8",
                )
            (source_dir / CHANGE_MANIFEST_NAME).write_text(
                '{"changed_document_ids": ["document-1"]}', encoding="utf-8"
            )

            with (
                patch("azure_search.SearchClient", return_value=fake_search),
                patch(
                    "azure_search._document_pages",
                    return_value=[(1, "Contenido aprobado del manual.")],
                ),
                patch("azure_search._attach_embeddings") as attach_embeddings,
            ):
                uploaded = index_directory(source_dir, config)

            self.assertEqual(1, uploaded)
            embedded_records = attach_embeddings.call_args.args[0]
            self.assertEqual(["document-1"], [record["document_id"] for record in embedded_records])
            self.assertEqual(
                ["document-1"],
                [record["document_id"] for record in fake_search.uploaded_records],
            )
            self.assertEqual(set(), _changed_document_ids(source_dir))

    def test_create_index_reindexes_every_pdf_and_acknowledges_pending_changes(self):
        class FakeSearchClient:
            def search(self, **_kwargs):
                return []

            def merge_or_upload_documents(self, documents):
                return [
                    SimpleNamespace(succeeded=True, key=document["id"])
                    for document in documents
                ]

            def delete_documents(self, documents):
                return [
                    SimpleNamespace(succeeded=True, key=document["id"])
                    for document in documents
                ]

        config = SimpleNamespace(
            azure_search_configured=True,
            azure_search_endpoint="https://search.example",
            azure_search_index_name="libras-docs",
            azure_search_api_key="not-a-real-key",
        )
        with TemporaryDirectory() as directory:
            source_dir = Path(directory)
            for document_id in ("document-1", "document-2"):
                pdf_path = source_dir / f"{document_id}.pdf"
                pdf_path.write_bytes(b"placeholder")
                pdf_path.with_suffix(".pdf.metadata.json").write_text(
                    f'{{"document_id": "{document_id}"}}', encoding="utf-8"
                )
            (source_dir / CHANGE_MANIFEST_NAME).write_text(
                '{"changed_document_ids": ["document-1"]}', encoding="utf-8"
            )

            with (
                patch("azure_search.SearchClient", return_value=FakeSearchClient()),
                patch("azure_search.ensure_index"),
                patch(
                    "azure_search._document_pages",
                    return_value=[(1, "Contenido aprobado del manual.")],
                ),
                patch("azure_search._attach_embeddings") as attach_embeddings,
            ):
                uploaded = index_directory(source_dir, config, create_index=True)

            self.assertEqual(2, uploaded)
            self.assertEqual(
                {"document-1", "document-2"},
                {record["document_id"] for record in attach_embeddings.call_args.args[0]},
            )
            self.assertEqual(set(), _changed_document_ids(source_dir))

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

    def test_country_specific_request_does_not_mix_evidence(self):
        guatemala_record = {
            "title": "Guatemala — Página 1",
            "document_context": "Procedimiento autorizado para Guatemala.",
            "content": "Guatemala. Ajuste de sesión.",
        }
        salvador_record = {
            "title": "El Salvador — Página 1",
            "document_context": "Procedimiento autorizado para El Salvador.",
            "content": "El Salvador. Ajuste de sesión.",
        }

        filtered = _filter_records_for_requested_country(
            [salvador_record, guatemala_record],
            "¿Cómo se realiza el ajuste de sesión en Guatemala?",
        )

        self.assertEqual([guatemala_record], filtered)

    def test_country_specific_request_without_matching_evidence_returns_no_records(self):
        generic_record = {
            "title": "Manual general",
            "document_context": "Procedimiento técnico sin país.",
            "content": "Ajuste de sesión.",
        }

        filtered = _filter_records_for_requested_country(
            [generic_record], "¿Cómo se realiza el ajuste de sesión en El Salvador?"
        )

        self.assertEqual([], filtered)

    def test_country_request_rejects_a_multi_country_contact_footer(self):
        shared_footer_record = {
            "title": "Cambios generales de Evolution",
            "document_context": "GUATEMALA oficina central. EL SALVADOR oficina regional.",
            "content": "Cambios de interfaz de Evolution.",
        }

        filtered = _filter_records_for_requested_country(
            [shared_footer_record],
            "¿Qué cambios existen para El Salvador en Evolution?",
        )

        self.assertEqual([], filtered)

    def test_tangential_single_term_hit_is_not_sufficient_evidence(self):
        vacation_policy = {
            "title": "Políticas de pago",
            "content": "Las vacaciones pendientes se procesan al retiro del empleado.",
        }

        self.assertFalse(
            _has_minimum_content_coverage(
                vacation_policy,
                "¿Cuál es el procedimiento oficial de Recursos Humanos para aprobar vacaciones?",
            )
        )
        self.assertTrue(
            _has_minimum_content_coverage(
                vacation_policy,
                "¿Cómo se procesan las vacaciones pendientes?",
            )
        )

    def test_vacation_guide_without_approval_action_is_not_evidence_of_approval_procedure(self):
        technical_guide = {
            "title": "Guía de temas técnicos Evolution",
            "content": (
                "Creación y modificación de vacaciones. Para crear un periodo de "
                "vacaciones, asigne el año inicial y valide el empleo."
            ),
        }
        approval_procedure = {
            "title": "Procedimiento de aprobación de vacaciones",
            "content": (
                "El jefe aprueba la solicitud de vacaciones y Recursos Humanos "
                "confirma la aprobación antes de registrar el movimiento."
            ),
        }
        question = "¿Cuál es el procedimiento oficial para aprobar vacaciones?"

        self.assertFalse(_has_minimum_content_coverage(technical_guide, question))
        self.assertTrue(_has_minimum_content_coverage(approval_procedure, question))

    def test_related_vacation_evidence_without_approval_action_is_not_classified_as_resolved(self):
        evidence = [
            EvidenceSource(
                tipo="sharepoint",
                titulo="Guía de temas técnicos Evolution",
                ubicacion="https://contoso.example/guia.docx",
                fragmento="Creación y modificación de vacaciones para el empleo.",
            )
        ]

        decision = classify_case_by_rules(
            "¿Cuál es el procedimiento oficial para aprobar vacaciones?", evidence
        )

        self.assertEqual("sin_evidencia", decision.estado)
        self.assertEqual([], decision.fuentes)

    def test_out_of_scope_question_requires_three_specific_terms(self):
        human_resources_capacity = {
            "title": "Requerimientos de Evolution",
            "content": "Usuarios concurrentes del departamento de Recursos Humanos.",
        }

        self.assertFalse(
            _has_minimum_content_coverage(
                human_resources_capacity,
                "¿Cuál es el procedimiento oficial de Recursos Humanos para aprobar vacaciones?",
            )
        )

    def test_only_https_sharepoint_records_are_authorized_evidence(self):
        self.assertTrue(
            _record_has_authorized_provenance(
                {"source_system": "sharepoint", "source_url": "https://contoso.example/manual.pdf"}
            )
        )
        self.assertFalse(
            _record_has_authorized_provenance(
                {"source_system": "web", "source_url": "https://unapproved.example/manual.pdf"}
            )
        )
        self.assertFalse(
            _record_has_authorized_provenance(
                {"source_system": "sharepoint", "source_url": "http://contoso.example/manual.pdf"}
            )
        )
        approved_folder = ("SOLUCIONES",)
        self.assertTrue(
            _record_has_authorized_provenance(
                {
                    "source_system": "sharepoint",
                    "source_url": "https://contoso.example/manual.pdf",
                    "folder_path": "SOLUCIONES",
                },
                approved_folder,
            )
        )
        self.assertFalse(
            _record_has_authorized_provenance(
                {
                    "source_system": "sharepoint",
                    "source_url": "https://contoso.example/manual.pdf",
                    "folder_path": "ReadME Hotfixes",
                },
                approved_folder,
            )
        )

    def test_multi_library_provenance_accepts_only_approved_drive_and_path(self):
        approved_sources = (("", "drive-readme"), ("SOLUCIONES", "drive-documents"))
        base_record = {
            "source_system": "sharepoint",
            "source_url": "https://contoso.example/manual.pdf",
        }

        self.assertTrue(
            _record_has_authorized_provenance(
                {**base_record, "drive_id": "drive-readme", "folder_path": ""},
                approved_sources,
            )
        )
        self.assertTrue(
            _record_has_authorized_provenance(
                {
                    **base_record,
                    "drive_id": "drive-documents",
                    "folder_path": "SOLUCIONES",
                },
                approved_sources,
            )
        )
        self.assertFalse(
            _record_has_authorized_provenance(
                {**base_record, "drive_id": "drive-other", "folder_path": ""},
                approved_sources,
            )
        )

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

    def test_response_includes_verifiable_source_link(self):
        response = format_user_response(
            BotDecision(
                estado="resuelto",
                confianza="alta",
                resumen="El procedimiento está documentado.",
                fuentes=[
                    EvidenceSource(
                        tipo="sharepoint",
                        titulo="Procedimiento de actualización",
                        ubicacion="https://contoso.example/procedimiento.pdf",
                        fragmento="Pasos aprobados.",
                    )
                ],
            )
        )

        self.assertIn("Enlace: https://contoso.example/procedimiento.pdf", response)

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
