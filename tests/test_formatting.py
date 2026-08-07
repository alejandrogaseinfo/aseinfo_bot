import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from formatting import format_user_response
from models import BotDecision, EvidenceSource


class FormattingTests(unittest.TestCase):
    def test_page_and_document_suffixes_become_a_short_link_label(self):
        response = format_user_response(
            BotDecision(
                estado="resuelto",
                confianza="alta",
                resumen="Respuesta documentada.",
                fuentes=[
                    EvidenceSource(
                        tipo="sharepoint",
                        titulo="Acciones de personal.pdf — Página 18",
                        ubicacion="https://contoso.example/acciones.pdf",
                        fragmento="Evidencia.",
                    )
                ],
            )
        )

        self.assertIn(
            "[Ver documento: Acciones de personal.pdf (pág. 18)]"
            "(https://contoso.example/acciones.pdf#page=18)",
            response,
        )
        self.assertNotIn("Enlace: https://", response)

    def test_legacy_url_format_can_be_enabled_for_reversible_rollback(self):
        response = format_user_response(
            BotDecision(
                estado="resuelto",
                confianza="alta",
                resumen="Respuesta documentada.",
                fuentes=[
                    EvidenceSource(
                        tipo="sharepoint",
                        titulo="Manual.pdf",
                        ubicacion="https://contoso.example/manual.pdf",
                        fragmento="Evidencia.",
                    )
                ],
            ),
            config=SimpleNamespace(use_friendly_links=False),
        )

        self.assertIn("Enlace: https://contoso.example/manual.pdf", response)
        self.assertNotIn("[Ver documento:", response)

    def test_pdf_page_anchor_can_be_disabled(self):
        response = format_user_response(
            BotDecision(
                estado="resuelto",
                confianza="alta",
                resumen="Respuesta documentada.",
                fuentes=[
                    EvidenceSource(
                        tipo="sharepoint",
                        titulo="Manual.pdf — Página 7",
                        ubicacion="https://contoso.example/manual.pdf",
                        fragmento="Evidencia.",
                    )
                ],
            ),
            config=SimpleNamespace(use_pdf_page_links=False),
        )

        self.assertIn("(https://contoso.example/manual.pdf)", response)


if __name__ == "__main__":
    unittest.main()
